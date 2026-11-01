#!/bin/bash
set -e

echo "=== 1. Tenancy and VCN Setup ==="
TENANCY_ID="$OCI_TENANCY"
VCN_ID="ocid1.vcn.oc1.eu-turin-1.amaaaaaaaikiy6ayedadmrw47cfdtw224p7p3baseakadpcppv3xm4skpba"
echo "Tenancy: $TENANCY_ID"
echo "VCN: $VCN_ID"

# Get default Route Table and Security List IDs from VCN
RT_ID=$(oci network vcn get --vcn-id "$VCN_ID" --query "data.\"default-route-table-id\"" --raw-output)
SL_ID=$(oci network vcn get --vcn-id "$VCN_ID" --query "data.\"default-security-list-id\"" --raw-output)
echo "Default RT: $RT_ID"
echo "Default SL: $SL_ID"

# 2. Create Internet Gateway if not present
echo "=== 2. Creating Internet Gateway ==="
IGW_ID=$(oci network internet-gateway list --compartment-id "$TENANCY_ID" --vcn-id "$VCN_ID" --query "data[0].id" --raw-output 2>/dev/null || true)
if [ -z "$IGW_ID" ] || [ "$IGW_ID" == "None" ]; then
  IGW_ID=$(oci network internet-gateway create --compartment-id "$TENANCY_ID" --vcn-id "$VCN_ID" --is-enabled true --display-name "speechify-igw" --query "data.id" --raw-output)
fi
echo "Internet Gateway ID: $IGW_ID"

# 3. Update Route Table with 0.0.0.0/0 -> IGW
echo "=== 3. Configuring Route Table ==="
oci network route-table update --rt-id "$RT_ID" --route-rules '[{"cidrBlock":"0.0.0.0/0","networkEntityId":"'"$IGW_ID"'"}]' --force

# 4. Update Security List to open 22, 7000, 8080
echo "=== 4. Configuring Security List Ingress Rules ==="
oci network security-list update --security-list-id "$SL_ID" --ingress-security-rules '[
  {"protocol":"6","source":"0.0.0.0/0","tcpOptions":{"destinationPortRange":{"max":22,"min":22}},"description":"SSH"},
  {"protocol":"6","source":"0.0.0.0/0","tcpOptions":{"destinationPortRange":{"max":7000,"min":7000}},"description":"FRP Control"},
  {"protocol":"6","source":"0.0.0.0/0","tcpOptions":{"destinationPortRange":{"max":8080,"min":8080}},"description":"HTTP Audio Relay"}
]' --force

# 5. Create Public Subnet
echo "=== 5. Creating Public Subnet ==="
SUBNET_ID=$(oci network subnet list --compartment-id "$TENANCY_ID" --vcn-id "$VCN_ID" --query "data[0].id" --raw-output 2>/dev/null || true)
if [ -z "$SUBNET_ID" ] || [ "$SUBNET_ID" == "None" ]; then
  SUBNET_ID=$(oci network subnet create --compartment-id "$TENANCY_ID" --vcn-id "$VCN_ID" --cidr-block "10.0.0.0/24" --display-name "Public Subnet-speechify-vcn" --route-table-id "$RT_ID" --security-list-ids '["'"$SL_ID"'"]' --query "data.id" --raw-output)
fi
echo "Public Subnet ID: $SUBNET_ID"

# 6. Resolve Availability Domain & Image
AD=$(oci iam availability-domain list --compartment-id "$TENANCY_ID" --query "data[0].name" --raw-output)
echo "Availability Domain: $AD"

IMAGE_ID=$(oci compute image list --compartment-id "$TENANCY_ID" --operating-system "Canonical Ubuntu" --operating-system-version "22.04" --shape "VM.Standard.E2.1.Micro" --sort-by TIMECREATED --sort-order DESC --query "data[0].id" --raw-output 2>/dev/null || true)
if [ -z "$IMAGE_ID" ] || [ "$IMAGE_ID" == "None" ]; then
  IMAGE_ID=$(oci compute image list --compartment-id "$TENANCY_ID" --operating-system "Oracle Linux" --operating-system-version "9" --shape "VM.Standard.E2.1.Micro" --sort-by TIMECREATED --sort-order DESC --query "data[0].id" --raw-output 2>/dev/null)
fi
echo "Image ID: $IMAGE_ID"

# 7. Cloud-init Userdata script
cat << 'USERDATA' > /tmp/user_data.sh
#!/bin/bash
iptables -I INPUT 6 -m state --state NEW -p tcp --dport 7000 -j ACCEPT
iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8080 -j ACCEPT
which netfilter-persistent && netfilter-persistent save || true

ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
  FRP_URL="https://github.com/fatedier/frp/releases/download/v0.61.0/frp_0.61.0_linux_amd64.tar.gz"
  FRP_DIR="frp_0.61.0_linux_amd64"
else
  FRP_URL="https://github.com/fatedier/frp/releases/download/v0.61.0/frp_0.61.0_linux_arm64.tar.gz"
  FRP_DIR="frp_0.61.0_linux_arm64"
fi

mkdir -p /opt
cd /opt
curl -sL "$FRP_URL" -o frp.tar.gz
tar -zxvf frp.tar.gz
mv "$FRP_DIR" frp
cd /opt/frp

cat << 'EOF' > frps.toml
bindPort = 7000
vhostHttpPort = 8080
auth.token = "speechify_secure_token_2026"
EOF

cat << 'EOF' > /etc/systemd/system/frps.service
[Unit]
Description=FRP Relay Server for Speechify
After=network.target

[Service]
Type=simple
ExecStart=/opt/frp/frps -c /opt/frp/frps.toml
Restart=always
RestartSec=3s

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now frps
USERDATA

# 8. Ensure SSH Key exists
[ -f ~/.ssh/id_rsa.pub ] || ssh-keygen -t rsa -b 2048 -N "" -f ~/.ssh/id_rsa

# 9. Launch Compute Instance
echo "=== 9. Launching VM.Standard.E2.1.Micro ==="
LAUNCH_OUTPUT=$(oci compute instance launch \
  --compartment-id "$TENANCY_ID" \
  --availability-domain "$AD" \
  --shape "VM.Standard.E2.1.Micro" \
  --subnet-id "$SUBNET_ID" \
  --image-id "$IMAGE_ID" \
  --display-name "speechify-relay-vm" \
  --assign-public-ip true \
  --ssh-authorized-keys-file ~/.ssh/id_rsa.pub \
  --user-data-file /tmp/user_data.sh)

INSTANCE_ID=$(echo "$LAUNCH_OUTPUT" | jq -r '.data.id')
echo "Instance OCID: $INSTANCE_ID"

echo "Waiting for instance to reach RUNNING state..."
oci compute instance get --instance-id "$INSTANCE_ID" --wait-for-state RUNNING --query "data.\"lifecycle-state\""

PUBLIC_IP=$(oci compute instance list-vnics --instance-id "$INSTANCE_ID" --query "data[0].\"public-ip\"" --raw-output)
echo "=========================================================="
echo "SUCCESS! Speechify Relay VM is RUNNING!"
echo "PUBLIC_IP=$PUBLIC_IP"
echo "=========================================================="

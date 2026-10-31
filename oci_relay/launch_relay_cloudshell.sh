#!/bin/bash
set -e

echo "=========================================================="
echo "    Speechify OCI Relay 1-Click Provisioning Script       "
echo "=========================================================="

# 1. Ensure SSH keypair exists in Cloud Shell
if [ ! -f ~/.ssh/id_rsa.pub ]; then
  echo "[+] Generating fresh SSH keypair..."
  ssh-keygen -t rsa -b 2048 -N "" -f ~/.ssh/id_rsa
fi

# 2. Discover Compartment OCID
echo "[+] Discovering 'speechify-relay' compartment..."
COMP_ID=$(oci iam compartment list --name "speechify-relay" --query "data[0].id" --raw-output 2>/dev/null)
if [ -z "$COMP_ID" ] || [ "$COMP_ID" == "None" ]; then
  echo "[!] Compartment 'speechify-relay' not found by name, using root tenancy..."
  TENANCY_ID=$(oci session validate --query "data.tenancy" --raw-output 2>/dev/null || oci iam tenancy get --query "data.id" --raw-output 2>/dev/null)
  COMP_ID="$TENANCY_ID"
fi
echo "[+] Compartment ID: $COMP_ID"

# 3. Availability Domain
AD=$(oci iam availability-domain list --compartment-id "$COMP_ID" --query "data[0].name" --raw-output)
echo "[+] Availability Domain: $AD"

# 4. Discover Subnet
echo "[+] Discovering public subnet..."
SUBNET_ID=$(oci network subnet list --compartment-id "$COMP_ID" --display-name "Public Subnet-speechify-vcn" --query "data[0].id" --raw-output 2>/dev/null)
if [ -z "$SUBNET_ID" ] || [ "$SUBNET_ID" == "None" ]; then
  SUBNET_ID=$(oci network subnet list --compartment-id "$COMP_ID" --query "data[0].id" --raw-output)
fi
echo "[+] Subnet ID: $SUBNET_ID"

# 5. Discover Always-Free OS Image (Ubuntu 22.04 or Oracle Linux 9)
echo "[+] Resolving OS Image..."
IMAGE_ID=$(oci compute image list --compartment-id "$COMP_ID" --operating-system "Canonical Ubuntu" --operating-system-version "22.04" --shape "VM.Standard.E2.1.Micro" --sort-by TIMECREATED --sort-order DESC --query "data[0].id" --raw-output 2>/dev/null)

if [ -z "$IMAGE_ID" ] || [ "$IMAGE_ID" == "None" ]; then
  IMAGE_ID=$(oci compute image list --compartment-id "$COMP_ID" --operating-system "Oracle Linux" --operating-system-version "9" --shape "VM.Standard.E2.1.Micro" --sort-by TIMECREATED --sort-order DESC --query "data[0].id" --raw-output 2>/dev/null)
fi
echo "[+] Image ID: $IMAGE_ID"

# 6. Prepare Cloud-Init bootstrap script
cat << 'USERDATA' > /tmp/user_data.sh
#!/bin/bash
# Firewall rules
iptables -I INPUT 6 -m state --state NEW -p tcp --dport 7000 -j ACCEPT
iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8080 -j ACCEPT
which netfilter-persistent && netfilter-persistent save || true

# Download and install FRP
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

# Configure frps.toml
cat << 'EOF' > frps.toml
bindPort = 7000
vhostHttpPort = 8080
auth.token = "speechify_secure_token_2026"
EOF

# Create persistent systemd unit
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

# 7. Launch VM Instance
echo "[+] Launching VM.Standard.E2.1.Micro instance..."
LAUNCH_OUTPUT=$(oci compute instance launch \
  --compartment-id "$COMP_ID" \
  --availability-domain "$AD" \
  --shape "VM.Standard.E2.1.Micro" \
  --subnet-id "$SUBNET_ID" \
  --image-id "$IMAGE_ID" \
  --display-name "speechify-relay-vm" \
  --assign-public-ip true \
  --ssh-authorized-keys-file ~/.ssh/id_rsa.pub \
  --user-data-file /tmp/user_data.sh)

INSTANCE_ID=$(echo "$LAUNCH_OUTPUT" | jq -r '.data.id')
echo "[+] Instance Created! ID: $INSTANCE_ID"

echo "[+] Waiting for instance to transition to RUNNING state (~30-60s)..."
oci compute instance get --instance-id "$INSTANCE_ID" --wait-for-state RUNNING --query "data.\"lifecycle-state\""

# 8. Query Public IP
PUBLIC_IP=$(oci compute instance list-vnics --instance-id "$INSTANCE_ID" --query "data[0].\"public-ip\"" --raw-output)

echo ""
echo "=========================================================="
echo " SUCCESS! Your Speechify Relay VM is Live!               "
echo " Public IP Address : $PUBLIC_IP"
echo " FRP Control Port  : 7000"
echo " HTTP Audio Relay  : 8080"
echo " Auth Secret Token : speechify_secure_token_2026"
echo "=========================================================="

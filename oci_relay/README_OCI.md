# Oracle Cloud Relay Setup Guide (2-Minute Walkthrough)

This guide shows how to configure your Oracle Cloud Infrastructure (OCI) Virtual Machine as the secure tunnel relay connecting Render to your home GPU.

---

## Step 1: Open Ports in Oracle Cloud Dashboard
In your Oracle Cloud Console:
1. Navigate to: **Networking** -> **Virtual Cloud Networks (VCN)** -> Click your VCN -> **Security Lists** -> **Default Security List**.
2. Click **Add Ingress Rules**:
   - **Rule 1 (FRP Control Port)**:
     - Source CIDR: `0.0.0.0/0`
     - Destination Port Range: `7000`
     - Description: `FRP Tunnel Control`
   - **Rule 2 (HTTP Audio Relay Port)**:
     - Source CIDR: `0.0.0.0/0`
     - Destination Port Range: `8080`
     - Description: `Render to Home GPU Proxy`
3. Click **Add Ingress Rules**.

Also open the ports inside the Ubuntu firewall on the VPS:
```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 7000 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8080 -j ACCEPT
sudo netfilter-persistent save
```

---

## Step 2: Install and Run FRP on Oracle Cloud
SSH into your Oracle Cloud VM:
```bash
# Check architecture (x86_64 or aarch64)
uname -m

# For x86_64 (AMD):
wget https://github.com/fatedier/frp/releases/download/v0.61.0/frp_0.61.0_linux_amd64.tar.gz
tar -zxvf frp_0.61.0_linux_amd64.tar.gz
cd frp_0.61.0_linux_amd64

# For aarch64 (ARM Ampere):
# wget https://github.com/fatedier/frp/releases/download/v0.61.0/frp_0.61.0_linux_arm64.tar.gz
# tar -zxvf frp_0.61.0_linux_arm64.tar.gz
# cd frp_0.61.0_linux_arm64
```

Copy the `frps.toml` configuration:
```toml
bindPort = 7000
vhostHttpPort = 8080
auth.token = "YOUR_SHARED_SECRET_TOKEN"
```

Start the FRP server:
```bash
./frps -c frps.toml
```

---

## Step 3: Run FRP on Your Home PC
1. Download `frp_0.61.0_windows_amd64.zip` from https://github.com/fatedier/frp/releases
2. Extract `frpc.exe` into the `oci_relay/` folder.
3. In `oci_relay/frpc.toml`, replace:
   - `serverAddr = "YOUR_ORACLE_CLOUD_PUBLIC_IP"`
   - `auth.token = "YOUR_SHARED_SECRET_TOKEN"`
4. Double-click `start_gpu_worker.bat`!

---

## Step 4: Configure Render Environment Variables
In your Render dashboard for `speechify-web`:
- `LOCAL_WORKER_URL`: `http://YOUR_ORACLE_CLOUD_PUBLIC_IP:8080`
- `WORKER_SECRET_KEY`: Same as your secret token

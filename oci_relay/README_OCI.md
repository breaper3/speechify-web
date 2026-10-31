# Complete Oracle Cloud (OCI) Relay Setup Guide

This guide walks through setting up an Oracle Cloud Infrastructure (OCI) Always Free instance from scratch to act as a secure, high-speed reverse proxy relay connecting Render to your home GPU worker.

---

## Step 1: Create a Dedicated Compartment (Recommended)

Compartments isolate your project resources and keep your OCI root tenancy organized.

1. In the OCI Console, open the navigation menu (top-left hamburger icon).
2. Go to: **Identity & Security** -> **Compartments**.
3. Click **Create Compartment**:
   - **Name**: `speechify-relay` (or any name you prefer)
   - **Description**: `Compartment for Speechify hybrid relay infrastructure`
   - **Parent Compartment**: Select your root tenancy compartment.
4. Click **Create Compartment**.

---

## Step 2: Create a Virtual Cloud Network (VCN) with Internet Access

The VCN provides networking, IP routing, and firewall rules for your relay VM.

1. Open the top-left menu and navigate to: **Networking** -> **Virtual Cloud Networks**.
2. In the left panel under **List Scope**, set **Compartment** to `speechify-relay` (or the compartment you created in Step 1).
3. Click **Start VCN Wizard** (do not click simple "Create VCN", the wizard automatically configures gateways and routing).
4. Select **Create VCN with Internet Connectivity** and click **Start VCN Wizard**:
   - **VCN Name**: `speechify-vcn`
   - **Compartment**: `speechify-relay`
   - **VCN IPv4 CIDR Block**: `10.0.0.0/16` (default)
   - **Public Subnet IPv4 CIDR Block**: `10.0.0.0/24` (default)
   - **Private Subnet IPv4 CIDR Block**: `10.0.1.0/24` (default)
5. Click **Next**, review the resources (Internet Gateway, Route Table, Security Lists), and click **Create**.
6. Wait for the wizard to show **Complete**, then click **View Virtual Cloud Network**.

---

## Step 3: Configure Ingress Rules in the Security List

By default, OCI blocks incoming traffic except for SSH (port 22). You must allow FRP control (port 7000) and the audio relay (port 8080).

1. In your `speechify-vcn` details page, click **Security Lists** in the left menu (under Resources).
2. Click **Default Security List for speechify-vcn**.
3. Under **Ingress Rules**, click **Add Ingress Rules**.
4. Add the following two rules:

### Rule 1: FRP Control Port (Home PC to OCI tunnel handshake)
- **Stateless**: Unchecked (No)
- **Source Type**: CIDR
- **Source CIDR**: `0.0.0.0/0`
- **IP Protocol**: TCP
- **Source Port Range**: All (leave blank)
- **Destination Port Range**: `7000`
- **Description**: `FRP Tunnel Control Port`

### Rule 2: HTTP Audio Relay Port (Render to OCI proxy traffic)
- **Stateless**: Unchecked (No)
- **Source Type**: CIDR
- **Source CIDR**: `0.0.0.0/0`
- **IP Protocol**: TCP
- **Source Port Range**: All (leave blank)
- **Destination Port Range**: `8080`
- **Description**: `Render to Home GPU Audio Relay`

5. Click **Add Ingress Rules**.

---

## Step 4: Launch the Always Free Relay VM

1. In the OCI Console menu, go to: **Compute** -> **Instances**.
2. Ensure your compartment (`speechify-relay`) is selected on the left.
3. Click **Create Instance**:
   - **Name**: `speechify-relay-vm`
   - **Placement**: Keep default Availability Domain.
   - **Image and Shape**:
     - Image: Canonical Ubuntu 22.04 or 24.04 (or Oracle Linux 8/9).
     - Shape: `VM.Standard.E2.1.Micro` (AMD Always Free) or `VM.Standard.A1.Flex` (ARM Ampere Always Free).
   - **Networking**:
     - Virtual cloud network: `speechify-vcn`
     - Subnet: `Public Subnet-speechify-vcn`
     - Assign a public IPv4 address: **Yes** (mandatory)
   - **Add SSH keys**:
     - Select **Generate a key pair for me** and download both the Private Key (`.key`) and Public Key, OR paste your existing public SSH key.
4. Click **Create** and wait for the instance status to turn green (**Running**).
5. Note down your **Public IP Address** from the instance overview page.

---

## Step 5: Configure the Ubuntu OS Firewall

OCI instances have a local firewall inside the OS (iptables or ufw) that must also permit ports 7000 and 8080.

1. Connect to your instance via SSH:
   ```bash
   ssh -i /path/to/your-private-key.key ubuntu@<YOUR_PUBLIC_IP>
   ```

2. Run the following commands to open ports in Ubuntu iptables:
   ```bash
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 7000 -j ACCEPT
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8080 -j ACCEPT
   sudo netfilter-persistent save
   ```

*(If using Oracle Linux instead of Ubuntu, run: `sudo firewall-cmd --permanent --add-port=7000/tcp --add-port=8080/tcp && sudo firewall-cmd --reload`)*

---

## Step 6: Install and Start FRP Server (frps) on the VM

1. On the OCI instance SSH terminal, check the CPU architecture:
   ```bash
   uname -m
   ```

2. Download and extract FRP:

   **For x86_64 (AMD Micro shape):**
   ```bash
   wget https://github.com/fatedier/frp/releases/download/v0.61.0/frp_0.61.0_linux_amd64.tar.gz
   tar -zxvf frp_0.61.0_linux_amd64.tar.gz
   cd frp_0.61.0_linux_amd64
   ```

   **For aarch64 (ARM Ampere shape):**
   ```bash
   wget https://github.com/fatedier/frp/releases/download/v0.61.0/frp_0.61.0_linux_arm64.tar.gz
   tar -zxvf frp_0.61.0_linux_arm64.tar.gz
   cd frp_0.61.0_linux_arm64
   ```

3. Create the `frps.toml` file:
   ```bash
   nano frps.toml
   ```
   Paste the following:
   ```toml
   bindPort = 7000
   vhostHttpPort = 8080
   auth.token = "speechify_secure_token_2026"
   ```
   Press `Ctrl+O`, `Enter` to save, and `Ctrl+X` to exit.

4. Start `frps` as a background service:
   ```bash
   nohup ./frps -c frps.toml > frps.log 2>&1 &
   ```
   *(To check if it is running: `ps aux | grep frps` or `cat frps.log`)*

---

## Step 7: Configure Your Local Home PC

1. Download `frp_0.61.0_windows_amd64.zip` from:
   https://github.com/fatedier/frp/releases/download/v0.61.0/frp_0.61.0_windows_amd64.zip
2. Extract `frpc.exe` into your local `oci_relay/` directory.
3. Open `oci_relay/frpc.toml` in your editor and update:
   - `serverAddr = "<YOUR_ORACLE_PUBLIC_IP>"`
   - `auth.token = "speechify_secure_token_2026"`
4. Double-click `start_gpu_worker.bat` on your desktop or in this folder.
   Your local GPU models (Jordan Peterson, MrBeast, Kokoro-82M) are now securely routed through your Oracle Cloud IP!

---

## Step 8: Configure Render Web App

In your Render dashboard for `speechify-web`:
1. Navigate to: **Environment** -> **Add Environment Variable**.
2. Add:
   - `LOCAL_WORKER_URL`: `http://<YOUR_ORACLE_PUBLIC_IP>:8080`
   - `WORKER_SECRET_KEY`: `speechify_secure_token_2026`
3. Click **Save Changes**. Render will automatically redeploy.

Once redeployed, the status pill on your live Render web app will turn green:
**"GPU Worker Connected · CUDA"**

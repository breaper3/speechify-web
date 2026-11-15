import subprocess
import re
import sys
import os
import time
import threading
import urllib.request
import json

RENDER_URL = "https://speechify-web.onrender.com"
current_active_url = None

def register_with_render(tunnel_url: str):
    """Notifies the Render web service of the current active Cloudflare tunnel URL."""
    try:
        endpoint = f"{RENDER_URL}/api/register-node"
        payload = json.dumps({"url": tunnel_url}).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "Speechify-Tunnel/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                print(f"[Registry] Connected Render directly to: {tunnel_url}")
    except Exception as e:
        print(f"[Registry Notice] Tunnel registration: {e}")

def keep_render_alive():
    """Pings Render every 5 minutes to prevent free-tier spin-down (cold starts) and keep node registered."""
    health_url = f"{RENDER_URL}/api/health"
    while True:
        time.sleep(300)  # 5 minutes
        try:
            req = urllib.request.Request(health_url, headers={"User-Agent": "Speechify-KeepAlive/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                pass
            global current_active_url
            if current_active_url:
                register_with_render(current_active_url)
        except Exception:
            pass

def main():
    global current_active_url
    cloudflared_path = os.path.join(os.path.dirname(__file__), "cloudflared.exe")
    if not os.path.exists(cloudflared_path):
        print(f"Error: {cloudflared_path} not found.")
        sys.exit(1)

    # Start background keep-alive heartbeat thread
    keep_alive_thread = threading.Thread(target=keep_render_alive, daemon=True)
    keep_alive_thread.start()

    print("Starting Cloudflare Tunnel on http://127.0.0.1:8000...")
    cmd = [cloudflared_path, "tunnel", "--url", "http://127.0.0.1:8000"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

    tunnel_url = None
    url_file = os.path.join(os.path.dirname(__file__), "tunnel_url.txt")

    for line in proc.stdout:
        print("[cloudflared]", line.rstrip())
        if not tunnel_url:
            match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
            if match:
                tunnel_url = match.group(0)
                current_active_url = tunnel_url
                print("\n" + "="*60)
                print(f"  TUNNEL READY: {tunnel_url}")
                print("="*60 + "\n")
                with open(url_file, "w") as f:
                    f.write(tunnel_url)
                register_with_render(tunnel_url)
                sys.stdout.flush()

if __name__ == "__main__":
    main()

import subprocess
import re
import sys
import os
import time

def main():
    cloudflared_path = os.path.join(os.path.dirname(__file__), "cloudflared.exe")
    if not os.path.exists(cloudflared_path):
        print(f"Error: {cloudflared_path} not found.")
        sys.exit(1)

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
                print("\n" + "="*60)
                print(f"  TUNNEL READY: {tunnel_url}")
                print("="*60 + "\n")
                with open(url_file, "w") as f:
                    f.write(tunnel_url)
                sys.stdout.flush()

if __name__ == "__main__":
    main()

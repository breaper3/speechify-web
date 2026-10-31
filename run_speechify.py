import uvicorn
import socket
import sys

import os

# Ensure safe output streams under pythonw.exe
if sys.stdout is None:
    sys.stdout = open(os.path.join(os.path.dirname(__file__), "speechify_server.log"), "a", encoding="utf-8")
elif hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

if sys.stderr is None:
    sys.stderr = open(os.path.join(os.path.dirname(__file__), "speechify_server.log"), "a", encoding="utf-8")

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    local_ip = get_local_ip()
    port = 8000
    print("\n" + "="*60)
    print("   SPEECHIFY LOCAL - NEURAL READER READY")
    print("="*60)
    print(f" [PC Browser]     http://localhost:{port}")
    print(f" [Phone / Wi-Fi]  http://{local_ip}:{port}")
    print("="*60)
    print(" Press Ctrl+C to stop the server.\n")

    uvicorn.run("speechify_local.server:app", host="0.0.0.0", port=port, reload=False, log_level="info")

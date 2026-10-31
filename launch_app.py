import os
import sys
import time
import socket
import webbrowser
import subprocess

# Ensure safe output streams under pythonw.exe
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

def is_server_running(host: str = "127.0.0.1", port: int = 8000) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False

def main():
    target_url = "http://localhost:8000"
    project_dir = os.path.dirname(os.path.abspath(__file__))
    
    if not is_server_running():
        python_exe = sys.executable
        pythonw_exe = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
        exe_to_use = pythonw_exe if os.path.exists(pythonw_exe) else python_exe
        
        script_path = os.path.join(project_dir, "run_speechify.py")
        log_path = os.path.join(project_dir, "speechify_server.log")
        
        creationflags = 0
        if sys.platform == "win32":
            DETACHED_PROCESS = 0x00000008
            CREATE_NO_WINDOW = 0x08000000
            creationflags = DETACHED_PROCESS | CREATE_NO_WINDOW
            
        with open(log_path, "a", encoding="utf-8") as log_file:
            subprocess.Popen(
                [exe_to_use, script_path],
                cwd=project_dir,
                stdout=log_file,
                stderr=log_file,
                creationflags=creationflags,
                close_fds=True
            )
        
        # Wait up to 10 seconds for server to be responsive
        start_time = time.time()
        while time.time() - start_time < 10:
            if is_server_running():
                break
            time.sleep(0.3)
            
    # Open the application in default web browser
    webbrowser.open(target_url)

if __name__ == "__main__":
    main()

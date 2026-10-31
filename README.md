# Speechify Local - Neural Voice Reader (Hybrid Cloud Edition)

A high-performance neural text-to-speech reader with visual PDF tracking, speed gauge controls, responsive mobile drawer, and hybrid GPU cloud acceleration.

---

## Architecture Highlights
- **Cloud Gateway (Render)**: Hosts the web frontend, document parsing (PyMuPDF), and Edge-TTS cloud neural voices.
- **Local GPU Node (Home PC)**: Runs NVIDIA CUDA-accelerated Kokoro-82M and RVC v2 celebrity voices (Dr. Jordan Peterson, MrBeast).
- **Oracle Cloud Relay**: Low-latency reverse proxy tunnel (FRP or SSH) securely connecting Render to your home GPU without opening home router ports.

---

## Deploying to Render
1. Push this repository to GitHub.
2. In Render Dashboard, click **New +** -> **Web Service**.
3. Connect your repository.
4. Render automatically detects `render.yaml` or you can configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn speechify_local.server:app --host 0.0.0.0 --port $PORT`
5. Set Environment Variables:
   - `LOCAL_WORKER_URL`: `http://<YOUR_ORACLE_CLOUD_IP>:8080`
   - `WORKER_SECRET_KEY`: `<YOUR_SECRET_TOKEN>`

---

## Local GPU Worker Setup
To activate Dr. Jordan Peterson, MrBeast, and Kokoro GPU voices:
1. Follow the quick guide in `oci_relay/README_OCI.md`.
2. Run `start_gpu_worker.bat` on your workstation.

import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8500))
    print(f"[*] Starting Antigravity Quant Terminal on 0.0.0.0:{port}...")
    uvicorn.run("server.main:app", host="0.0.0.0", port=port, log_level="info")

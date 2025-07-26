"""Generated REST API skeleton"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import time
import psutil

app = FastAPI(title="Generated API", version="1.0.0")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "timestamp": time.time()
    })

@app.get("/metrics")
async def get_metrics():
    """Metrics endpoint with system stats"""
    process = psutil.Process()
    memory_info = process.memory_info()
    
    return JSONResponse({
        "memory_rss_mb": memory_info.rss / 1024 / 1024,
        "memory_vms_mb": memory_info.vms / 1024 / 1024,
        "cpu_percent": process.cpu_percent(),
        "uptime_seconds": time.time() - process.create_time()
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

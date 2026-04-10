"""
Root-level app.py for Hugging Face Space deployment.
Imports and exposes the FastAPI app from server.app
"""

from server.app import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=False)

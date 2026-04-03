"""
HuggingFace Spaces entry point for SQL Investigation Environment.

This module imports and exposes the FastAPI application from server.app.
For local testing: python app.py
For Docker/HF Spaces: uvicorn app:app --host 0.0.0.0 --port 7860
"""

import sys
import os
from pathlib import Path

# Ensure the parent directory is in the path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    # Import the FastAPI app from server module
    from server.app import app
    
    # Verify app is a FastAPI instance
    if app is None:
        raise RuntimeError("Failed to import app: app is None")
    
    # Log successful import
    print(f"✓ Successfully loaded FastAPI app from server.app", file=sys.stderr)
    
except Exception as e:
    print(f"✗ Error importing app: {e}", file=sys.stderr)
    print(f"✗ sys.path: {sys.path}", file=sys.stderr)
    raise

# Entry point for local testing with python app.py
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

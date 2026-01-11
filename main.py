"""Application entry point."""

from src.logging_config import setup_logging
from src.app import app

# Setup logging before anything else
setup_logging()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

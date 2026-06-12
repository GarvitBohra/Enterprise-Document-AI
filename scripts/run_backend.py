"""Run the FastAPI backend in a predictable local-dev configuration."""

import os
import sys
from pathlib import Path

import uvicorn


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload_enabled = os.getenv("RELOAD", "0") == "1"
    uvicorn.run("backend.main:app", host=host, port=port, reload=reload_enabled, app_dir=str(project_root))


if __name__ == "__main__":
    main()

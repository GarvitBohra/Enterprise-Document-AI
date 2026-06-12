"""Run the Streamlit frontend with the project's local API defaults."""

import os
import subprocess
import sys


def main() -> None:
    port = os.getenv("STREAMLIT_PORT", "8501")
    api_url = os.getenv("API_URL", "http://localhost:8000")
    env = os.environ.copy()
    env["API_URL"] = api_url

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "frontend/streamlit_app.py",
        "--server.port",
        port,
    ]
    raise SystemExit(subprocess.call(cmd, env=env))


if __name__ == "__main__":
    main()

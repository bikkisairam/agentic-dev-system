import subprocess


def deploy_app(host="localhost", port=8000):
    """
    Deploy Agent:
    Launches the generated FastAPI application using uvicorn.
    Returns the process handle so the caller can manage its lifecycle.
    """
    try:
        process = subprocess.Popen(
            ["uvicorn", "generated_api:app", "--host", host, "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return {
            "status": "deployed",
            "pid": process.pid,
            "url": f"http://{host}:{port}"
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e)
        }

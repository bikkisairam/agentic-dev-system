import subprocess


def run_tests():
    """
    Test Runner Agent:
    Executes pytest on the tests directory and returns results.
    """
    try:
        result = subprocess.run(
            ["pytest", "tests/", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=60
        )

        passed = result.returncode == 0

        return {
            "passed": passed,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }

    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "Tests timed out after 60 seconds"
        }
    except Exception as e:
        return {
            "passed": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e)
        }

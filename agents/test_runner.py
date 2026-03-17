import importlib.util
import sys


def run_tests():
    """
    Test Runner Agent:
    Imports generated_api.py directly and tests it with FastAPI TestClient.
    No live server required.
    """
    try:
        from fastapi.testclient import TestClient

        # Remove cached module so re-import always picks up the latest file
        if "generated_api" in sys.modules:
            del sys.modules["generated_api"]

        spec = importlib.util.spec_from_file_location("generated_api", "generated_api.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        app = module.app

        client = TestClient(app)
        response = client.get("/weather")

        data = response.json()
        checks = {
            "status_200":      response.status_code == 200,
            "has_temperature": "temperature" in data,
            "has_humidity":    "humidity" in data,
            "has_weather":     "weather" in data,
        }
        all_passed = all(checks.values())

        return {
            "passed":     all_passed,
            "returncode": 0 if all_passed else 1,
            "checks":     checks,
            "response":   data,
        }

    except Exception as e:
        return {
            "passed":     False,
            "returncode": -1,
            "checks":     {},
            "stderr":     str(e),
        }

Here is a pytest test file that tests the /health endpoint's status and returns OK:

import fastapi
from generated.aa_1.app import app

def test_ac3():
    with client:
        response = client.get("/health")
        assert response.status == 200
        assert response.json() == {"Status": "To Do"}
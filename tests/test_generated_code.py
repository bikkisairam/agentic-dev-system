import requests
from fastapi import FastAPI

app = FastAPI()

@app.get("/weather")
def read_root():
    return {"temperature": 25.3, "humidity": 67, "weather": "sunny"}

def test_read_root():
    response = requests.get("http://127.0.0.1:8000/weather")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "temperature" in response.json()
    assert "humidity" in response.json()
    assert "weather" in response.json()
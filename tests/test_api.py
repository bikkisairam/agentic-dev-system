import requests

def test_weather():
    url = "http://127.0.0.1:8001/weather"
    response = requests.get(url)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
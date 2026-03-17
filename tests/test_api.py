import requests


def test_weather_status():
    url = "http://127.0.0.1:8000/weather"
    response = requests.get(url)
    assert response.status_code == 200


def test_weather_content_type():
    url = "http://127.0.0.1:8000/weather"
    response = requests.get(url)
    assert response.headers["content-type"].startswith("application/json")


def test_weather_fields():
    url = "http://127.0.0.1:8000/weather"
    response = requests.get(url)
    data = response.json()
    assert "temperature" in data
    assert "humidity" in data
    assert "weather" in data

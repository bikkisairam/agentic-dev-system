import uvicorn
from fastapi import FastAPI

app = FastAPI()

dummy_weather_data = {
    "temperature": 25,
    "humidity": 60,
    "weather": "Sunny"
}

@app.get("/weather")
def read_root():
    return dummy_weather_data

if __name__ == '__main__':
    uvicorn.run(app, host='localhost', port=8000)
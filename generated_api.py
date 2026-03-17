from fastapi import FastAPI
import json

app = FastAPI()

@app.get("/weather")
def get_weather():
    # Return STATIC dummy JSON data (DO NOT call any external API)
    return {
        "temperature": 20,
        "humidity": 40,
        "weather": "sunny"
    }

if __name__ == '__main__':
    uvicorn.run(app, host="localhost", port=8000)

After installing the FastAPI framework and Uvicorn:
Run your application by typing the following command in the terminal:
`uvicorn main:app --host localhost --port 8000`
This will start a development server that listens on port 8000.
The URL `http://localhost:8000/weather` should be returned in JSON format with the weather data you specified.
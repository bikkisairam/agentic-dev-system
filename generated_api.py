from fastapi import FastAPI
import uvicorn

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

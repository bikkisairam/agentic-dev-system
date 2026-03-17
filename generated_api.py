from fastapi import FastAPI
app = FastAPI()

@app.get("/weather")
async def read_root():
    return {
        "temperature": 25,
        "humidity": 60,
        "weather": "Sunny"
    }
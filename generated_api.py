import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/weather")
async def read_root():
    return {
        "temperature": 25.3,
        "humidity": 0.64,
        "weather": "sunny"
    }

if __name__ == '__main__':
    uvicorn.run(app, host='localhost', port=8000)
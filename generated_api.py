from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/weather")
def read_root():
    return {
        "temperature": 25,
        "humidity": 60,
        "weather": "Sunny"
    }

if __name__ == '__main__':
    uvicorn.run(app, host='localhost', port=8000)
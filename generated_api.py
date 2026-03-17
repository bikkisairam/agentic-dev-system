from fastapi import FastAPI

app = FastAPI()

@app.get("/weather")
def read_root():
    return {"temperature": 25, "humidity": 40, "weather": "Sunny"}

if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=8000)
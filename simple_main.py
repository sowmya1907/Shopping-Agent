from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def hello():
    print("Root route called")
    return {"message": "Hello World"}

@app.get("/test")
def test():
    print("Test route called")
    return {"message": "Test successful"}
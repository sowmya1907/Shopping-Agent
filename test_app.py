from fastapi import FastAPI

app = FastAPI()

@app.get('/')
def hello():
    return {'message': 'Shopping Agent API is running'}

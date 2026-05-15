from fastapi import FastAPI
from app.database import engine, Base
from app.models.job import Job

Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Job AI Backend Running"}
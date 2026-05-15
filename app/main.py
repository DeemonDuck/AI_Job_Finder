from fastapi import FastAPI
from app.database import engine, Base
from app.models.job import Job
from app.routes.job_routes import router as job_router

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(job_router)

@app.get("/")
def home():
    return {"message": "Job AI Backend Running"}
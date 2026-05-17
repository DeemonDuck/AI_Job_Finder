from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.models.job import Job
from app.routes.job_routes import router as job_router
from app.models.preferences import UserPreferences

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Enable frontend communication with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(job_router)

@app.get("/")
def home():
    return {"message": "Job AI Backend Running"}
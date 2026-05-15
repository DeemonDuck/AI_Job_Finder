from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job import Job
from app.schemas.job_schema import JobCreate

router = APIRouter()

@router.post("/jobs")
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    
    new_job = Job(
        title=job.title,
        company=job.company,
        location=job.location,
        salary=job.salary,
        platform=job.platform,
        job_url=job.job_url,
        description=job.description,
        skills=job.skills
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    return {
        "message": "Job created successfully",
        "job_id": new_job.id
    }

@router.get("/jobs")
def get_jobs(db: Session = Depends(get_db)):
    
    jobs = db.query(Job).all()

    return jobs


@router.get("/jobs/{job_id}")
def get_single_job(job_id: int, db: Session = Depends(get_db)):

    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        return {"error": "Job not found"}

    return job
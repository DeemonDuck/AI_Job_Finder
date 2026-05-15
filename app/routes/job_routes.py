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

# Route to delete a job using its ID
@router.delete("/jobs/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):

    # Find job in database
    job = db.query(Job).filter(Job.id == job_id).first()

    # Return error if job does not exist
    if not job:
        return {"error": "Job not found"}

    # Delete job
    db.delete(job)
    db.commit()

    return {"message": "Job deleted successfully"}

# Route to update an existing job
@router.put("/jobs/{job_id}")
def update_job(job_id: int, updated_job: JobCreate, db: Session = Depends(get_db)):

    # Find existing job
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        return {"error": "Job not found"}

    # Update job fields
    job.title = updated_job.title
    job.company = updated_job.company
    job.location = updated_job.location
    job.salary = updated_job.salary
    job.platform = updated_job.platform
    job.job_url = updated_job.job_url
    job.description = updated_job.description
    job.skills = updated_job.skills

    db.commit()

    return {
        "message": "Job updated successfully"
    }
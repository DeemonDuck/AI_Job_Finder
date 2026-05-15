from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job import Job
from app.schemas.job_schema import JobCreate, JobResponse

router = APIRouter()

# Route to create a new job
@router.post("/jobs", response_model=JobResponse)
def create_job(job: JobCreate, db: Session = Depends(get_db)):

    new_job = Job(
        title=job.title,
        company=job.company,
        location=job.location,
        salary=job.salary,
        platform=job.platform,
        job_url=job.job_url,
        description=job.description,
        skills=job.skills,
        status=job.status
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    return new_job


# Route to fetch jobs with optional filters
@router.get("/jobs", response_model=list[JobResponse])
def get_jobs(
    company: str = None,
    location: str = None,
    skill: str = None,
    db: Session = Depends(get_db)
):

    query = db.query(Job)

    # Filter by company name
    if company:
        query = query.filter(Job.company.ilike(f"%{company}%"))

    # Filter by location
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))

    # Filter by skills
    if skill:
        query = query.filter(Job.skills.ilike(f"%{skill}%"))

    jobs = query.all()

    return jobs

# Route to fetch a single job using its ID
@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_single_job(job_id: int, db: Session = Depends(get_db)):

    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        return {"error": "Job not found"}

    return job


# Route to update an existing job
@router.put("/jobs/{job_id}", response_model=JobResponse)
def update_job(job_id: int, updated_job: JobCreate, db: Session = Depends(get_db)):

    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        return {"error": "Job not found"}

    job.title = updated_job.title
    job.company = updated_job.company
    job.location = updated_job.location
    job.salary = updated_job.salary
    job.platform = updated_job.platform
    job.job_url = updated_job.job_url
    job.description = updated_job.description
    job.skills = updated_job.skills
    job.status = updated_job.status

    db.commit()
    db.refresh(job)

    return job


# Route to delete a job using its ID
@router.delete("/jobs/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):

    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        return {"error": "Job not found"}

    db.delete(job)
    db.commit()

    return {"message": "Job deleted successfully"}
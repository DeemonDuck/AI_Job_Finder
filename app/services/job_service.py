from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.job import Job


# Service to fetch jobs with filters and pagination
def get_all_jobs(
    db: Session,
    company=None,
    location=None,
    skill=None,
    sort_by="created_at",
    skip=0,
    limit=10
):

    query = db.query(Job)

    if company:
        query = query.filter(Job.company.ilike(f"%{company}%"))

    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))

    if skill:
        query = query.filter(Job.skills.ilike(f"%{skill}%"))

    if sort_by == "created_at":
        query = query.order_by(desc(Job.created_at))

    return query.offset(skip).limit(limit).all()
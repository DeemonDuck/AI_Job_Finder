from sqlalchemy import Column, Integer, String, Text
from app.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    company = Column(String, index=True)
    location = Column(String)
    salary = Column(String)
    platform = Column(String)
    job_url = Column(String)
    description = Column(Text)
    skills = Column(String)
from pydantic import BaseModel

class JobCreate(BaseModel):
    title: str
    company: str
    location: str
    salary: str
    platform: str
    job_url: str
    description: str
    skills: str
    status: str = "saved"

class JobResponse(JobCreate):
    id: int

    class Config:
        from_attributes = True
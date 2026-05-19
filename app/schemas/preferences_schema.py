from pydantic import BaseModel
from typing import Optional

class PreferencesCreate(BaseModel):
    preferred_role: str
    preferred_location: str
    preferred_skills: str
    experience_level: str
    job_type: str
    salary_expectation: str
    max_job_age_days: Optional[int] = None


class PreferencesResponse(PreferencesCreate):
    id: int

    class Config:
        from_attributes = True
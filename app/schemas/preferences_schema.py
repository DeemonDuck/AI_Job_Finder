from pydantic import BaseModel


class PreferencesCreate(BaseModel):
    preferred_role: str
    preferred_location: str
    preferred_skills: str
    experience_level: str
    job_type: str
    salary_expectation: str


class PreferencesResponse(PreferencesCreate):
    id: int

    class Config:
        from_attributes = True
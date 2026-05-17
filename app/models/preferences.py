from sqlalchemy import Column, Integer, String
from app.database import Base


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)

    preferred_role = Column(String)
    preferred_location = Column(String)
    preferred_skills = Column(String)

    experience_level = Column(String)

    job_type = Column(String)  # remote, hybrid, onsite

    salary_expectation = Column(String)
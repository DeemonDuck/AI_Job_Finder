from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.preferences import UserPreferences
from app.schemas.preferences_schema import (
    PreferencesCreate,
    PreferencesResponse
)

router = APIRouter(
    prefix="/api/v1/preferences",
    tags=["Preferences"]
)


# Create user preferences
@router.post("/", response_model=PreferencesResponse)
def create_preferences(
    preferences: PreferencesCreate,
    db: Session = Depends(get_db)
):

    new_preferences = UserPreferences(
        preferred_role=preferences.preferred_role,
        preferred_location=preferences.preferred_location,
        preferred_skills=preferences.preferred_skills,
        experience_level=preferences.experience_level,
        job_type=preferences.job_type,
        salary_expectation=preferences.salary_expectation
    )

    db.add(new_preferences)
    db.commit()
    db.refresh(new_preferences)

    return new_preferences


# Fetch all preferences
@router.get("/", response_model=list[PreferencesResponse])
def get_preferences(db: Session = Depends(get_db)):

    preferences = db.query(UserPreferences).all()

    return preferences
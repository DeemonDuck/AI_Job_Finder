from app.database import Base, engine

# Import all models
from app.models.job import Job
from app.models.preferences import UserPreferences
from app.models.internshala_category import (
    InternshalaCategory
)

# Create all tables
Base.metadata.create_all(bind=engine)

print("Database tables created.")
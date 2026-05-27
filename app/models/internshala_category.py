from sqlalchemy import Column, Integer, String
from app.database import Base


class InternshalaCategory(Base):

    __tablename__ = "internshala_categories"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String,
        unique=True,
        nullable=False
    )
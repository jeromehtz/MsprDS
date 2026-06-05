from sqlalchemy import Column, Integer, String
from database import Base

class Trajet(Base):
    __tablename__ = "trajets"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    departure_city = Column(String)
    arrival_city = Column(String)
    duration = Column(String)
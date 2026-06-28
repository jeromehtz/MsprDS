from sqlalchemy import Column, Integer, String, Float
from database import Base

class Trajet(Base):
    __tablename__ = "trajets"

    year = Column(Integer, primary_key=True)
    origin_station_name = Column(String, primary_key=True)
    destination_station_name = Column(String, primary_key=True)
    origin_city = Column(String, primary_key=True)
    destination_city = Column(String, primary_key=True)
    origin_region = Column(String, primary_key=True)
    destination_region = Column(String, primary_key=True)
    passengers_millions = Column("Passengers_millions", Float)
    type = Column("Type", String)
    source = Column(String)
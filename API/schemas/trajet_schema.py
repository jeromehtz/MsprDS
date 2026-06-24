from pydantic import BaseModel

class TrajetCreate(BaseModel):
    year: int
    origin_station_name: str
    destination_station_name: str
    origin_city: str
    destination_city: str
    origin_region: str
    destination_region: str
    passengers_millions: float
    type: str
    source: str


class TrajetResponse(BaseModel):
    year: int
    origin_station_name: str
    destination_station_name: str
    origin_city: str
    destination_city: str
    origin_region: str
    destination_region: str
    passengers_millions: float
    type: str
    source: str

    class Config:
        from_attributes = True

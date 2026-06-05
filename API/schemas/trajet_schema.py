from pydantic import BaseModel


class TrajetCreate(BaseModel):

    departure_city: str
    arrival_city: str
    duration: str


class TrajetResponse(BaseModel):

    id: int
    departure_city: str
    arrival_city: str
    duration: str

    class Config:

        from_attributes = True
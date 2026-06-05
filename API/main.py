from fastapi import FastAPI

from database import Base
from database import engine

from routers.auth_router import router as auth_router
from routers.trajet_router import router as trajet_router

from models.user import User
from models.trajet import Trajet

Base.metadata.create_all(
    bind=engine
)

app = FastAPI(
    title="API MSPR",
    version="1.0.0"
)

app.include_router(auth_router)

app.include_router(trajet_router)


@app.get("/")
def root():

    return {
        "message": "API MSPR RUNNING"
    }
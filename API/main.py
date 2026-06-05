from fastapi import FastAPI
from database import Base, engine
from routers.auth_router import router as auth_router
from routers.trajet_router import router as trajet_router

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
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI(
    title="API MSPR1",
    description="API REST complète avec FastAPI",
    version="1.0.0"
)

# Modèle de données
class User(BaseModel):
    id: int
    nom: str
    email: str
    actif: bool = True


# Base de données 

users_db: List[User] = [
    User(id=1, nom="Alice", email="alice@mail.com"),
    User(id=2, nom="Bob", email="bob@mail.com"),
]



# Routes

@app.get("/")
def accueil():
    return {"message": "API MSPR1 en ligne 🚀"}


# READ - Tous les utilisateurs
@app.get("/users", response_model=List[User])
def get_users():
    return users_db


# READ - Un utilisateur
@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int):
    for user in users_db:
        if user.id == user_id:
            return user
    raise HTTPException(status_code=404, detail="Utilisateur non trouvé")


# Pour Ajouter un utilisateur
@app.post("/users", response_model=User)
def create_user(user: User):
    for u in users_db:
        if u.id == user.id:
            raise HTTPException(status_code=400, detail="ID déjà existant")
    users_db.append(user)
    return user


# Pour Modifier un utilisateur
@app.put("/users/{user_id}", response_model=User)
def update_user(user_id: int, updated_user: User):
    for index, user in enumerate(users_db):
        if user.id == user_id:
            users_db[index] = updated_user
            return updated_user
    raise HTTPException(status_code=404, detail="Utilisateur non trouvé")


# Pour Supprimer un utilisateur
@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    for user in users_db:
        if user.id == user_id:
            users_db.remove(user)
            return {"message": "Utilisateur supprimé"}
    raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

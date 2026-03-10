from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import uvicorn

app = FastAPI(
    title="API MSPR1",
    description="API REST complète avec FastAPI",
    version="1.0.0"
)



# Base de données trajets ferroviaires
# se connecter à../bdd/trajetsFerroviairesBDD.db et créer une classe trajetsFerroviaires avec les champs correspondants à la base de données trajetsInterPays
# on doit pouvoir calculer un itinéraire entre deux villes en utilisant les données dela base de données trajetsFerroviairesBDD.db
import sqlite3

class Trajet(BaseModel):
    origin_city: str
    destination_city: str
    origin_country: str
    destination_country: str
    # Ajoutez d'autres champs selon la structure de votre CSV (ex: distance, flow, etc.)

class trajetsFerroviaires:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        


    def get_trajets(self) -> List[dict]:
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.cursor.execute("SELECT * FROM trajets")
        rows = self.cursor.fetchall()
        # self.conn.close()
        return [dict(row) for row in rows]

    def get_trajets_interpays(self) -> List[dict]:
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.cursor.execute("SELECT * FROM trajetsInterPays")
        rows = self.cursor.fetchall()
        # self.conn.close()
        return [dict(row) for row in rows]

    def calculer_itineraire(self, depart: str, arrivee: str) -> List[dict]:
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        # Exemple de recherche simple (directe)
        try:
            query = f'SELECT * FROM trajets WHERE origin_city = "{depart}" AND destination_city = "{arrivee}"'
            self.cursor.execute(query)
            result = self.cursor.fetchall()

            if result == []:
                query = f'SELECT * FROM trajetsInterPays WHERE origin_city = "{depart}" AND destination_city = "{arrivee}"'
                self.cursor.execute(query)
                result = self.cursor.fetchall()
            if result == []:
                return {"message": "Aucun trajet trouvé entre ces villes."}
            # self.conn.close()
        except:
            return {"message": "Erreur lors de la connexion à la base de données."}
        return [dict(row) for row in result]    

trajets_interpays = trajetsFerroviaires("./bdd/trajetsFerroviairesBDD.db")



# users_db: List[User] = [
#     User(id=1, nom="Alice", email="alice@mail.com"),
#     User(id=2, nom="Bob", email="bob@mail.com"),
# ]




# Routes

@app.get("/")
def accueil():
    return {"message": "API MSPR1 en ligne 🚀"}


# READ - Tous les utilisateurs
@app.get("/trajetsInterPays", response_model=List[dict])
def get_users():
    return trajets_interpays.get_trajets_interpays()

@app.get("/trajets")
def get_trajets():
    trajets = trajetsFerroviaires("./bdd/trajetsFerroviairesBDD.db").get_trajets()
    return trajets

# calculer un itinéraire entre deux villes, il faut pouvoir saisir la ville de départ et la ville d'arrivée en paramètre de l'URL, par exemple /itineraire?depart=Paris&arrivee=Berlin, et faire un input
@app.get("/itineraire")
def calculer_itineraire(depart: str, arrivee: str):
    itineraire = trajets_interpays.calculer_itineraire(depart, arrivee)
    return {"itineraire": itineraire}


if __name__ == "__main__":
    # utilise FastAPI pour lancer l'API sur http://localhost:8000
    uvicorn.run(app, host="127.0.0.1", port=8000)

# normalement il y a u
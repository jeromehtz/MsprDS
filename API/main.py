from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import uvicorn
import sqlite3

app = FastAPI(
    title="API MSPR1",
    description="API REST complète avec FastAPI",
    version="1.0.0"
)

class Trajet(BaseModel):
    origin_city: str
    destination_city: str
    origin_country: str
    destination_country: str

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
        
        return [dict(row) for row in rows]

    def get_trajets_interpays(self) -> List[dict]:
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.cursor.execute("SELECT * FROM trajetsInterPays")
        rows = self.cursor.fetchall()
        
        return [dict(row) for row in rows]

    def calculer_itineraire(self, depart: str, arrivee: str) -> List[dict]:
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
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
            
        except:
            return {"message": "Erreur lors de la connexion à la base de données."}
        return [dict(row) for row in result]    

trajets_interpays = trajetsFerroviaires("../bdd/trajetsFerroviairesBDD.db")




# Routes

@app.get("/")
def accueil():
    return {"message": "API MSPR1 en ligne 🚀"}


@app.get("/trajetsInterPays", response_model=List[dict])
def obetnir_trajets_inter_Pays():
    return trajets_interpays.get_trajets_interpays()

@app.get("/trajets")
def obetnir_trajets():
    trajets = trajetsFerroviaires("../bdd/trajetsFerroviairesBDD.db").get_trajets()
    return trajets

@app.get("/itineraire")
def calculer_itineraire(depart: str, arrivee: str):
    itineraire = trajets_interpays.calculer_itineraire(depart, arrivee)
    return {"itineraire": itineraire}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
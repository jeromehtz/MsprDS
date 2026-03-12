import sqlite3
import pandas as pd
import os

def import_csv_to_db(db_name, csv_path, table_name):
    # connexion (crée la BDD si elle n'existe pas)
    conn = sqlite3.connect(db_name)

    # lecture du CSV
    df = pd.read_csv(csv_path, sep=";")

    # écriture dans la base
    df.to_sql(table_name, conn, if_exists="replace", index=False)

    conn.close()
    print(f"Table '{table_name}' créée / modifiée avec succès dans '{db_name}'")

def main():
    # db_name = input("Nom de la base de données (ex: database.db): ")
    csv_path = "./data/trajets/cross_border_rail_OD_IT_DE_FR_CH_ES_PT_bidirectional.csv" # ou input("Chemin du fichier CSV: ")
    table_name = "trajetsInterPays" # ou input("Nom de la table à créer: ")

    if not os.path.exists(csv_path):
        print("Le fichier CSV n'existe pas.")
        return

    import_csv_to_db("bdd/trajetsFerroviairesBDD.db", csv_path, table_name)

if __name__ == "__main__":
    main()
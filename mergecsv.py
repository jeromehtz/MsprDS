import pandas as pd

# 1. Lister tous les fichiers CSV du dossier
fichiers =["csv/frequentation_gares_allemagne.csv",
           "csv/frequentation_gares_italie.csv",
           "csv/frequentation_gares_france.csv",
        "csv/frequentation_gares_portugal.csv",
        "csv/frequentation_gares_suisse.csv"] # ou utiliser glob.glob("csv/*.csv") pour tous les fichiers du dossier

# 2. Lire chaque fichier et les stocker dans une liste
liste_df = [pd.read_csv(f) for f in fichiers]

# 3. Fusionner tous les DataFrames de la liste
df_final = pd.concat(liste_df, ignore_index=True)

# 4. Sauvegarder le résultat
df_final.to_csv("csv/frequentation_total.csv", index=False)
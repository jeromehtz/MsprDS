import pandas as pd

# 1. Lister tous les fichiers CSV du dossier
fichiers =["data/trajets/cross_border_rail_OD_IT_DE_FR_CH_ES_PT_bidirectional.csv",
           "data/trajets/rail_OD_flows_merged.csv",
        #    "data/trajets/france_rail_OD_flows.csv",
        # "data/trajets/portugal_rail_OD_flows.csv",
        # "data/trajets/switzerland_rail_OD_flows.csv",
        # "data/trajets/spain_rail_OD_flows.csv"
] # ou utiliser glob.glob("csv/*.csv") pour tous les fichiers du dossier

# 2. Lire chaque fichier et les stocker dans une liste
liste_df = [pd.read_csv(f, sep=";") for f in fichiers]

# 3. Fusionner tous les DataFrames de la liste
df_final = pd.concat(liste_df, ignore_index=True)

# 4. Sauvegarder le résultat
df_final.to_csv("data/trajets/trajets.csv", index=False)
#!/usr/bin/env python3
import pandas as pd
import json
from pathlib import Path

# --- Configuration ---

# Dossier des fichiers CSV
BASE_DIR = Path(__file__).resolve().parent
# On assume que les CSV sont dans le sous-dossier 'csv' du répertoire parent
# puisque votre structure de fichier montre 'avec-mongo/csv' et 'avec-redis/csv'
# Pour un script 'denormalisation.py' au niveau de 'avec-mongo' ou 'avec-redis',
# on se base sur la structure locale.
# Si le script est au niveau 'avec-mongo', utilisez:
CSV_DIR = BASE_DIR / "csv" 
# Si le script est au niveau racine 'PROJET-UBER', ajustez le chemin !
# Pour la structure affichée, 'denormalisation.py' semble être dans un sous-dossier
# (ex: 'avec-mongo' ou 'avec-redis'), donc:
# CSV_DIR = BASE_DIR / "csv" 

# Définir les fichiers CSV
FICHIERS_CSV = {
    "clients": CSV_DIR / "CLIENTS.csv",
    "commandes": CSV_DIR / "COMMANDES.csv",
    "details_commandes": CSV_DIR / "DETAILS_COMMANDES.csv",
    "plats": CSV_DIR / "PLATS.csv",
    "restaurants": CSV_DIR / "RESTAURANTS.csv"
}

# --- Fonctions ---

def charger_csv(fichier_path, index_col):
    """Charge un fichier CSV et le retourne sous forme de dictionnaire indexé par 'index_col'."""
    if not fichier_path.exists():
        print(f"⚠️ Fichier manquant : {fichier_path.name}")
        return {}
    
    # Lire le CSV
    df = pd.read_csv(fichier_path)
    # Convertir en dictionnaire pour un accès rapide (clé = index_col)
    # Utiliser 'to_dict' avec 'index' comme orientation et 'orient='records'' puis mapper pour être plus robuste
    records = df.to_dict(orient="records")
    return {record[index_col]: record for record in records}

def denormaliser_donnees():
    """Charge et dénormalise les données autour des commandes."""
    
    print("⏳ Chargement des données CSV...")
    
    # 1. Chargement des données et création des maps pour accès rapide (lookup)
    
    # Mappage : id_client -> infos client
    clients_map = charger_csv(FICHIERS_CSV["clients"], 'id_client')
    # Mappage : id_restaurant -> infos restaurant
    restaurants_map = charger_csv(FICHIERS_CSV["restaurants"], 'id_restaurant')
    # Mappage : id_plat -> infos plat
    plats_map = charger_csv(FICHIERS_CSV["plats"], 'id_plat')
    
    # Liste des commandes (structure principale de la dénormalisation)
    commandes_df = pd.read_csv(FICHIERS_CSV["commandes"])
    commandes = commandes_df.to_dict(orient="records")

    # Liste des détails de commande pour l'agrégation
    details_commandes_df = pd.read_csv(FICHIERS_CSV["details_commandes"])
    # Grouper par commande pour un accès plus simple
    details_par_commande = details_commandes_df.groupby('id_commande').apply(lambda x: x.to_dict('records')).to_dict()

    print("⏳ Dénormalisation des commandes...")
    commandes_denormalisees = []

    # 2. Dénormalisation
    for cmd in commandes:
        cmd_id = cmd['id_commande']
        
        # Récupérer les détails de la commande (les plats)
        cmd_details = details_par_commande.get(cmd_id, [])
        
        # Construire la liste des items (plat + quantité)
        items = []
        for d in cmd_details:
            plat_info = plats_map.get(d['id_plat'], {})
            
            # Note : Assurez-vous que les colonnes 'quantite' et 'id_plat' existent dans votre CSV DETAILS_COMMANDES.
            # On copie les infos du plat pour l'intégrer dans la commande
            items.append({
                "plat": plat_info,
                "quantite": d.get("quantite", 1)  # Utiliser 1 comme défaut si 'quantite' est manquante
            })

        # Construire l'enregistrement de la commande dénormalisée
        commande_denormalisee = {
            **cmd, # Toutes les infos de la commande
            "client": clients_map.get(cmd['id_client'], {}),
            "restaurant": restaurants_map.get(cmd['id_restaurant'], {}),
            "items": items # Liste des plats
        }
        
        commandes_denormalisees.append(commande_denormalisee)

    return commandes_denormalisees

# --- Script Principal ---

if __name__ == "__main__":
    try:
        # 1. Dénormaliser les données
        data_denormalisee = denormaliser_donnees()
        
        # 2. Écrire le JSON final
        output_json = BASE_DIR / "denormalisation.json"
        with output_json.open("w", encoding="utf-8") as f:
            # Utiliser 'ensure_ascii=False' pour conserver les caractères spéciaux (é, à, etc.)
            json.dump(data_denormalisee, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Dénormalisation terminée : {output_json.name} généré ({len(data_denormalisee)} commandes dénormalisées).")
        
    except FileNotFoundError as e:
        print(f"\n❌ ERREUR : Un fichier CSV est introuvable. Veuillez vérifier le chemin dans CSV_DIR et le nom des fichiers. Détail: {e}")
    except KeyError as e:
        print(f"\n❌ ERREUR : Colonne manquante dans un fichier CSV. Détail de la colonne : {e}. Assurez-vous d'avoir les IDs corrects ('id_client', 'id_restaurant', 'id_plat', 'id_commande', 'quantite').")
    except Exception as e:
        print(f"\n❌ ERREUR inattendue lors de la dénormalisation : {e}")
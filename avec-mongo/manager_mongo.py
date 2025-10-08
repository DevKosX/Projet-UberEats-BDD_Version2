#!/usr/bin/env python3
import time
import random
import json
from pathlib import Path
from pymongo import MongoClient

# Configuration
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "uber_mongo"
COLLECTION_ANNONCES = "annonces"

BASE_DIR = Path(__file__).resolve().parent
DENORMALISATION_FILE = BASE_DIR / "denormalisation.json"

# Initialisation MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
annonces_collection = db[COLLECTION_ANNONCES]

# Fonctions Utilitaires
def charger_donnees_commandes():
    try:
        with DENORMALISATION_FILE.open('r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Erreur: Le fichier {DENORMALISATION_FILE.name} est introuvable. Exécutez d'abord denormalisation.py.")
        return []
    except json.JSONDecodeError:
        print(f"Erreur de décodage JSON dans {DENORMALISATION_FILE.name}.")
        return []

def simuler_nouvelle_course(commandes):
    if not commandes:
        return

    course_data = random.choice(commandes)
    
    id_course = str(course_data['id_commande'])

    restaurant_loc = course_data['restaurant'].get('adresse_restaurant', 'Restaurant Inconnu')
    client_loc = course_data['client'].get('adresse_client', 'Client Inconnu')
    retribution = round(random.uniform(5.00, 15.00), 2)

    annonce = {
        '_id': id_course,
        'id_course': id_course,
        'point_retrait': restaurant_loc,
        'point_livraison': client_loc,
        'retribution': retribution,
        'statut': 'ANNONCE_PUBLIEE',
        'heure_annonce': time.time(),
        'interets_livreurs': []
    }

    try:
        annonces_collection.insert_one(annonce)
        print(f"\nMANAGER insère l'annonce pour la course {id_course} (Retribution: {retribution}€).")
        print(f"   Destination: {client_loc}")
        return id_course
    except Exception as e:
        print(f"Avertissement : Erreur lors de l'insertion de la course {id_course} : {e}")
        return None

def main():
    commandes = charger_donnees_commandes()
    if not commandes:
        return

    try:
        client.admin.command('ping')
    except Exception:
        print("\nATTENTION: Connexion à MongoDB réussie, mais assurez-vous que MongoDB est lancé en Replica Set (rs0).")
    
    annonces_collection.delete_many({})
    
    print("--- Démarrage du Manager UberEats (MongoDB Change Streams) ---")
    
    try:
        while True:
            simuler_nouvelle_course(commandes)
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\nArrêt du Manager.")
    except Exception as e:
        print(f"\nErreur inattendue: {e}")

if __name__ == '__main__':
    main()
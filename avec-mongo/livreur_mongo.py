#!/usr/bin/env python3
import time
import random
import json
from pymongo import MongoClient
from pymongo.errors import OperationFailure

# Configuration
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "uber_mongo"
COLLECTION_ANNONCES = "annonces"

LIVREUR_ID = f'LIVREUR_{random.randint(100, 999)}' 

# Initialisation MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
annonces_collection = db[COLLECTION_ANNONCES]

# Fonctions de Traitement
def manifester_interet(id_course):
    result = annonces_collection.update_one(
        {
            '_id': id_course,
            'statut': 'ANNONCE_PUBLIEE'
        },
        {
            '$addToSet': {'interets_livreurs': LIVREUR_ID}
        }
    )
    
    if result.modified_count > 0:
        print(f"-> {LIVREUR_ID} manifeste son intérêt pour la course {id_course}.")
        tenter_selection(id_course)

def tenter_selection(id_course):
    result = annonces_collection.update_one(
        {
            '_id': id_course,
            'statut': 'ANNONCE_PUBLIEE',
            'interets_livreurs': {'$in': [LIVREUR_ID]}
        },
        {
            '$set': {
                'statut': 'LIVREUR_SELECTIONNE',
                'livreur_selectionne': LIVREUR_ID,
                'heure_selection': time.time()
            }
        }
    )
    
    if result.modified_count > 0:
        print(f"-> {LIVREUR_ID} S'AUTO-SÉLECTIONNE pour la course {id_course}!")

def ecouter_change_stream():
    pipeline = [
        {
            '$match': {
                'operationType': {'$in': ['insert', 'update']},
                'fullDocument.statut': {'$in': ['ANNONCE_PUBLIEE', 'LIVREUR_SELECTIONNE']}
            }
        }
    ]
    
    print(f"En attente des annonces pour le livreur: {LIVREUR_ID}...")

    with annonces_collection.watch(pipeline=pipeline, full_document='updateLookup') as stream:
        for change in stream:
            doc = change.get('fullDocument')
            if not doc:
                continue

            id_course = doc['_id']
            statut = doc['statut']
            
            if change['operationType'] == 'insert':
                retribution = doc.get('retribution', 0)
                print(f"\n{LIVREUR_ID} reçoit une annonce pour la course {id_course} (Retribution: {retribution}€).")
                
                if random.random() < 0.8: 
                    manifester_interet(id_course)
                else:
                    print(f"-> {LIVREUR_ID} ignore la course {id_course}.")
            
            elif change['operationType'] == 'update':
                selectionne = doc.get('livreur_selectionne')
                if statut == 'LIVREUR_SELECTIONNE':
                    if selectionne == LIVREUR_ID:
                        print(f"\n{LIVREUR_ID} : FÉLICITATIONS ! Vous avez été sélectionné pour la course {id_course}!")
                        annonces_collection.update_one({'_id': id_course}, {'$set': {'statut': 'ACCEPTEE'}})
                        print(f"-> {LIVREUR_ID} a accepté la course et part au restaurant.")
                    else:
                        print(f"{LIVREUR_ID} : La course {id_course} a été attribuée à {selectionne}.")


def main():
    print(f"--- Démarrage du Livreur UberEats : {LIVREUR_ID} (MongoDB Change Streams) ---")
    
    try:
        ecouter_change_stream()
    except OperationFailure as e:
        if "The client is not allowed to use change streams" in str(e) or "not a replica set" in str(e):
            print("\nERREUR FATALE: MongoDB doit être configuré en Replica Set (rs0) pour utiliser les Change Streams.")
        else:
            print(f"\nERREUR MongoDB: {e}")
    except Exception as e:
        print(f"\nERREUR inattendue: {e}")
    except KeyboardInterrupt:
        print("\nArrêt du Livreur.")


if __name__ == '__main__':
    main()
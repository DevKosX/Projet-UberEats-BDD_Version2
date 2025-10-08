#!/usr/bin/env python3
import redis
import json
import time
import random
from pathlib import Path

REDIS_HOST = 'localhost'
REDIS_PORT = 6379

CHANNEL_ANNONCE = 'ubereats:annonces:nouvelle_course'
KEY_COURSE_ACTIVE = 'ubereats:course:active'

BASE_DIR = Path(__file__).resolve().parent
DENORMALISATION_FILE = BASE_DIR / "denormalisation.json"

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def charger_donnees_commandes():
    try:
        with DENORMALISATION_FILE.open('r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except:
        return []

def simuler_nouvelle_course(commandes):
    if not commandes:
        return

    course_data = random.choice(commandes)

    restaurant_loc = course_data['restaurant'].get('adresse_restaurant', 'Restaurant Inconnu')
    client_loc = course_data['client'].get('adresse_client', 'Client Inconnu')
    retribution = round(random.uniform(5.00, 15.00), 2)

    annonce = {
        'id_course': course_data['id_commande'],
        'point_retrait': restaurant_loc,
        'point_livraison': client_loc,
        'retribution': retribution,
        'heure_annonce': time.time()
    }

    r.publish(CHANNEL_ANNONCE, json.dumps(annonce))
    print(f"\nMANAGER publie l'annonce pour la course {annonce['id_course']} (Retribution: {retribution}€).")
    print(f"   Destination: {client_loc}")
    
    return annonce['id_course']

def selectionner_livreur(id_course, delai_sec=5):
    print(f"MANAGER attend les réponses des livreurs pour la course {id_course} pendant {delai_sec}s...")

    key_interets = f'ubereats:interet:{id_course}'

    time.sleep(delai_sec)

    interets = r.hgetall(key_interets)
    
    if not interets:
        print(f"Aucune réponse reçue pour la course {id_course}. Course annulée/republiée.")
        r.delete(key_interets)
        return

    # CORRECTION APPLIQUÉE : Suppression des appels .decode()
    # Les résultats de r.hgetall() sont déjà des chaînes de caractères (str) grâce à decode_responses=True.
    meilleurs_interets = {livreur_id: float(timestamp) 
                          for livreur_id, timestamp in interets.items()}
                          
    livreur_selectionne = min(meilleurs_interets, key=meilleurs_interets.get)
    
    print(f"MANAGER sélectionne le livreur {livreur_selectionne}.")
    
    course_active = {
        'id_course': id_course,
        'livreur_selectionne': livreur_selectionne,
        'statut': 'ATTENTE_ACCEPTATION'
    }
    r.set(KEY_COURSE_ACTIVE, json.dumps(course_active))
    
    r.delete(key_interets)

def main():
    commandes = charger_donnees_commandes()
    if not commandes:
        print("Erreur: Données de commande non disponibles.")
        return

    print("--- Démarrage du Manager UberEats (Redis) ---")
    
    try:
        r.delete(KEY_COURSE_ACTIVE)
        
        while True:
            course_id = simuler_nouvelle_course(commandes)
            selectionner_livreur(course_id, delai_sec=5)
            time.sleep(10)
            
    except redis.exceptions.ConnectionError:
        print("\nERREUR: Impossible de se connecter à Redis.")
    except KeyboardInterrupt:
        print("\nArrêt du Manager.")

if __name__ == '__main__':
    main()
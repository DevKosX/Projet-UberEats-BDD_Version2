#!/usr/bin/env python3
import redis
import json
import time
import random
import threading

REDIS_HOST = 'localhost'
REDIS_PORT = 6379

CHANNEL_ANNONCE = 'ubereats:annonces:nouvelle_course'
KEY_COURSE_ACTIVE = 'ubereats:course:active'

LIVREUR_ID = f'LIVREUR_{random.randint(100, 999)}' 

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def manifester_interet(id_course):
    key_interets = f'ubereats:interet:{id_course}'
    r.hset(key_interets, LIVREUR_ID, time.time())
    print(f"{LIVREUR_ID} manifeste son intérêt pour la course {id_course} (rapide!).")

def traiter_annonce(message):
    try:
        data = json.loads(message['data'])
        id_course = data['id_course']
        retribution = data['retribution']
        
        print(f"\n{LIVREUR_ID} a reçu une annonce pour la course {id_course} (Retribution: {retribution}€).")
        
        if random.random() < 0.8:
            manifester_interet(id_course)
        else:
            print(f"{LIVREUR_ID} ignore la course {id_course}.")
            
    except json.JSONDecodeError:
        pass

def surveiller_selection(id_course):
    max_attente = 10
    debut = time.time()
    
    while time.time() - debut < max_attente:
        time.sleep(1) 
        
        course_active_data = r.get(KEY_COURSE_ACTIVE)
        
        if course_active_data:
            course_active = json.loads(course_active_data)
            
            if course_active['id_course'] == id_course and course_active['livreur_selectionne'] == LIVREUR_ID:
                print(f"\n{LIVREUR_ID} : FÉLICITATIONS ! Vous avez été sélectionné pour la course {id_course}!")
                
                time.sleep(2)
                r.set(KEY_COURSE_ACTIVE, json.dumps({'id_course': id_course, 'livreur_selectionne': LIVREUR_ID, 'statut': 'ACCEPTEE'}))
                print(f"{LIVREUR_ID} a accepté la course et part au restaurant.")
                
                break
                
            elif course_active['id_course'] == id_course:
                print(f"{LIVREUR_ID} : La course {id_course} a été attribuée à {course_active['livreur_selectionne']}.")
                break
                
        if time.time() - debut >= max_attente:
            print(f"{LIVREUR_ID} : Fin d'attente pour la course {id_course}.")

def ecouter_annonces():
    pubsub = r.pubsub()
    pubsub.subscribe(CHANNEL_ANNONCE)
    print(f"{LIVREUR_ID} est en ligne et écoute le canal '{CHANNEL_ANNONCE}'.")
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            traiter_annonce(message)
            
            # Lancement d'un thread de surveillance pour ne pas bloquer l'écoute Pub/Sub
            id_course = json.loads(message['data'])['id_course']
            threading.Thread(target=surveiller_selection, args=(id_course,)).start()

def main():
    print(f"--- Démarrage du Livreur UberEats : {LIVREUR_ID} (Redis) ---")
    
    try:
        ecouter_annonces()
    except redis.exceptions.ConnectionError:
        print("\nERREUR: Impossible de se connecter à Redis.")
    except KeyboardInterrupt:
        print("\nArrêt du Livreur.")

if __name__ == '__main__':
    main()
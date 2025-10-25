#!/usr/bin/env python3
# J'importe 'time' pour le timestamp quand je postule.
import time
# J'importe 'random' pour simuler ma décision d'accepter ou non une course.
import random
# J'importe 'json' car les messages Redis (annonces, notifications)
# seront au format JSON.
import json
# J'importe 'threading' car je vais avoir besoin de deux processus d'écoute en parallèle :
# 1. Écouter les *nouvelles* annonces.
# 2. Écouter les *résultats* (notifications de gain/perte).
import threading
# J'importe 'redis' pour me connecter au serveur Redis.
import redis
# J'importe 'sys' pour pouvoir lire les arguments passés en ligne de commande
# (mon ID et mon nom).
import sys

# --- Configuration ---
# Je définis les infos de connexion à Redis.
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
# Je définis le nom du "channel" (canal) sur lequel les nouvelles
# annonces seront publiées (broadcastées).
ANNONCES_CHANNEL = 'annonces_channel'
# Je définis un canal séparé pour les notifications de résultat.
NOTIFICATIONS_CHANNEL = 'notifications_channel'

# --- Identité du Livreur (via arguments) ---
# Je vérifie que j'ai bien reçu 3 arguments au total :
# 1. le nom du script (ex: livreur_redis.py)
# 2. mon ID (ex: "1")
# 3. mon nom (ex: "Auguste Tanguy")
if len(sys.argv) != 3:
    print("Erreur: Vous devez fournir un ID et un nom.")
    print("Usage: python3 livreur_redis.py <id_livreur> \"<nom_livreur>\"")
    print("Exemple: python3 livreur_redis.py 1 \"Auguste Tanguy\"")
    # Si ce n'est pas le cas, j'affiche comment utiliser le script et je quitte.
    exit()

# Je récupère mon identité depuis les arguments.
LIVREUR_ID = sys.argv[1] # ex: "1"
LIVREUR_NOM = sys.argv[2] # ex: "Auguste Tanguy"

# --- Connexion à Redis ---
try:
    # J'ai besoin de *deux* connexions.
    # La première, 'r_command', sera pour écouter les annonces (thread principal)
    # et pour envoyer des commandes (comme HSET).
    # 'decode_responses=True' est crucial : ça convertit les réponses
    # de Redis (qui sont en bytes) directement en chaînes de caractères (str).
    r_command = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    
    # La deuxième connexion, 'r_listen', est nécessaire car une connexion
    # utilisée pour un 'pubsub.listen()' (écoute) est "bloquée" et ne peut
    # pas être utilisée pour envoyer d'autres commandes.
    # Je vais l'utiliser dans mon thread de notification.
    r_listen = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    
    # Je fais un 'ping()' pour vérifier que la connexion fonctionne.
    # Si Redis est éteint, ça lèvera une exception.
    r_command.ping()
    print(f"LIVREUR ({LIVREUR_NOM}, ID: {LIVREUR_ID}) connecté à Redis.")
except Exception as e:
    # Si le ping échoue, j'affiche l'erreur et j'arrête le script.
    print(f"Erreur de connexion à Redis pour {LIVREUR_ID}.\n   Détail: {e}")
    exit()

# --- Fonctions ---

def manifester_interet(annonce_id):
    """
    Ici, je n'utilise pas PUBLISH. Je vais utiliser une structure de données Redis : un Hash.
    Je vais créer un Hash pour chaque annonce (ex: "interets:annonce_123").
    Dans ce Hash, je vais stocker mon ID comme clé et mon timestamp comme valeur.
    """
    # Je définis le nom de la clé Redis pour cette annonce.
    key_interets = f"interets:{annonce_id}"
    # Je prends le timestamp *maintenant*.
    timestamp = time.time()
    
    # J'utilise HSET. C'est atomique (Redis le fait en une seule opération).
    # HSET = "Hash SET"
    # Syntaxe : HSET <nom_du_hash> <clé_dans_le_hash> <valeur>
    # Exemple : HSET interets:annonce_123 1 1678886400.123
    r_command.hset(key_interets, LIVREUR_ID, timestamp)
    print(f"{LIVREUR_NOM} manifeste son intérêt pour l'annonce '{annonce_id}'.")

def ecouter_notifications():
    """
    Cette fonction va tourner dans un thread séparé.
    Son seul rôle est d'écouter le canal des notifications pour
    savoir si j'ai gagné ou perdu une course.
    """
    # J'utilise ma deuxième connexion Redis ('r_listen').
    pubsub = r_listen.pubsub()
    # Je m'abonne au canal des notifications.
    pubsub.subscribe(NOTIFICATIONS_CHANNEL)
    
    # 'pubsub.listen()' est une boucle bloquante qui attend des messages.
    for message in pubsub.listen():
        # Je vérifie que c'est bien un message (et pas un message de service
        # comme la confirmation d'abonnement).
        if message['type'] == 'message':
            try:
                # Je décode le message JSON.
                notification = json.loads(message['data'])
                annonce_id = notification['annonce_id']

                # Je regarde le statut de la notification.
                if notification['status'] == 'ATTRIBUEE':
                    # Si c'est attribué, je regarde qui a gagné.
                    gagnant_id = notification['gagnant']['id_livreur']
                    if gagnant_id == LIVREUR_ID:
                        # Si l'ID gagnant est le mien, j'ai gagné !
                        print(f"GAGNÉ ! {LIVREUR_NOM} a obtenu la course '{annonce_id}'!")
                    else:
                        # Sinon, j'ai perdu.
                        print(f"PERDU... La course '{annonce_id}' a été prise par '{gagnant_id}'.")
                elif notification['status'] == 'ANNULEE':
                    # Je gère aussi le cas où personne n'a répondu.
                     print(f"ANNULÉE... La course '{annonce_id}' n'a pas trouvé de livreur.")

            except (json.JSONDecodeError, KeyError) as e:
                # Je me protège contre les messages JSON mal formés.
                print(f"[ERREUR NOTIF] Problème avec le message: {e} - Message: {message.get('data', '')}")


def ecouter_annonces():
    """
    C'est ma fonction principale. Elle écoute les *nouvelles* annonces
    et décide d'y répondre ou non.
    """
    # J'utilise ma connexion principale ('r_command').
    pubsub = r_command.pubsub()
    # Je m'abonne au canal des annonces.
    pubsub.subscribe(ANNONCES_CHANNEL)
    
    print(f"{LIVREUR_NOM} est en ligne et écoute les annonces sur '{ANNONCES_CHANNEL}'...")

    # C'est la boucle principale de mon script. Elle attend les messages.
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                # Je décode l'annonce JSON.
                annonce = json.loads(message['data'])
                annonce_id = annonce['_id']
                print(f"\n{LIVREUR_NOM} a reçu l'annonce '{annonce_id}' pour {annonce['retribution_livreur']}€.")
                
                # Je simule ma décision (80% de chances de répondre oui).
                if random.random() < 0.8:
                    # Si oui, j'appelle ma fonction pour m'enregistrer dans le Hash.
                    manifester_interet(annonce_id)
                else:
                    print(f"{LIVREUR_NOM} ignore cette annonce.")
            except (json.JSONDecodeError, KeyError) as e:
                # Je me protège contre les messages JSON mal formés.
                 print(f"[ERREUR ANNONCE] Problème avec le message: {e} - Message: {message.get('data', '')}")


# --- Script Principal ---
if __name__ == "__main__":
    try:
        # Je crée le thread pour écouter les notifications.
        # Je lui passe ma fonction 'ecouter_notifications'.
        # 'daemon=True' est important : ça veut dire que si mon thread principal
        # (celui qui écoute les annonces) s'arrête (par ex. avec Ctrl+C),
        # ce thread de notification s'arrêtera aussi automatiquement.
        notification_thread = threading.Thread(target=ecouter_notifications, daemon=True)
        # Je démarre le thread. Il tourne maintenant en arrière-plan.
        notification_thread.start()
        
        # Je lance ma fonction d'écoute des annonces dans le thread principal.
        # Mon script va "bloquer" ici, dans la boucle 'pubsub.listen()' de cette fonction.
        ecouter_annonces()
        
    except KeyboardInterrupt:
        # Si je fais Ctrl+C, je sors de la boucle 'ecouter_annonces'
        # et j'affiche un message de déconnexion.
        print(f"\n{LIVREUR_NOM} se déconnecte.")
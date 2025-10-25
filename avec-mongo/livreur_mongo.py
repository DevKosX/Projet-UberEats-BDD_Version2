#!/usr/bin/env python3
# J'importe 'time' pour pouvoir horodater mes actions,
# notamment quand je manifeste mon intérêt pour une course.
import time
# J'importe 'random' pour simuler un comportement (par exemple, décider
# si une course m'intéresse) et pour me donner un ID et un nom uniques
# à chaque fois que je lance ce script.
import random
# J'importe 'MongoClient' qui est la brique de base pour me connecter à MongoDB.
from pymongo import MongoClient
# J'importe 'OperationFailure' spécifiquement. C'est l'erreur que MongoDB
# lève si j'essaie d'utiliser les Change Streams sans un Replica Set.
# Je veux la capturer pour donner un message d'erreur clair.
from pymongo.errors import OperationFailure

# --- Configuration ---

# Je définis mon URI de connexion.
# Je commente que le 'replicaSet=rs0' est obligatoire,
# car je sais que la fonction 'watch' (Change Streams) ne fonctionne que comme ça.
MONGO_URI = "mongodb://localhost:27017/?replicaSet=rs0"
# Je définis le nom de la base de données sur laquelle je vais travailler.
DB_NAME = "uber_eats_poc"
# Je définis le nom de la collection que je vais écouter.
COLLECTION_ANNONCES = "annonces"

# Je me crée une identité pour cette session.
# C'est important pour que le système sache qui je suis
# quand je postule à une annonce.
LIVREUR_INFO = {
    "id_livreur": f'livreur_{random.randint(100, 999)}', # Je me donne un ID aléatoire
    "nom_livreur": random.choice(["Karim Le Véloce", "Laura La Rapide", "David Le Précis", "Fatima La Fiable"]) # Et un nom sympa
}

# --- Connexion à MongoDB ---
try:
    # J'initialise le client MongoDB. Je mets un 'serverSelectionTimeoutMS'
    # à 5000ms (5 secondes) pour que le script ne bloque pas
    # indéfiniment si la BDD n'est pas joignable.
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    
    # J'appelle 'server_info()'. C'est une étape cruciale.
    # Ça force le client à vérifier la connexion immédiatement.
    # Si le serveur n'est pas là ou si le replica set est mal configuré,
    # ça va lever une exception que je pourrai attraper.
    client.server_info()
    
    # Si tout va bien, je sélectionne ma base de données...
    db = client[DB_NAME]
    # ...et ma collection.
    annonces_collection = db[COLLECTION_ANNONCES]
    
    # Je m'affiche un message pour confirmer que je suis prêt.
    print(f"{LIVREUR_INFO['nom_livreur']} ({LIVREUR_INFO['id_livreur']}) connecté à MongoDB.")

except Exception as e:
    # Si 'server_info()' ou la connexion initiale échoue...
    print(f"Erreur de connexion. Assure-toi que MongoDB est lancé en Replica Set ('rs0').\n   Détail: {e}")
    # Si je ne peux pas me connecter, ça ne sert à rien de continuer.
    exit()

# --- Fonctions ---

def manifester_interet(annonce_id):
    """J'encapsule la logique pour postuler à une annonce dans une fonction."""
    print(f"{LIVREUR_INFO['nom_livreur']} est intéressé par l'annonce '{annonce_id}'.")
    
    # J'effectue la mise à jour dans la base de données.
    annonces_collection.update_one(
        # Mon filtre est double :
        # 1. Je cible l'ID de l'annonce spécifique.
        # 2. Je vérifie qu'elle a toujours le statut "PUBLIEE". Si elle
        #    a été attribuée entre-temps, cette opération ne fera rien.
        {"_id": annonce_id, "statut": "PUBLIEE"},
        
        # Mon opération de mise à jour :
        {
            # J'utilise '$addToSet'. C'est mieux que '$push' ici car si
            # mon script bugue et appelle cette fonction deux fois pour
            # la même annonce, '$addToSet' garantit que je ne serai
            # ajouté qu'une seule fois à la liste.
            "$addToSet": {
                "interets_livreurs": {
                    # J'utilise l'opérateur 'splat' (**) pour déballer
                    # mon dictionnaire LIVREUR_INFO (id + nom) directement ici.
                    **LIVREUR_INFO,
                    # J'ajoute un timestamp précis au moment où je postule.
                    # C'est ce que le "serveur" (l'autre script)
                    # utilisera pour déterminer qui a été le plus rapide.
                    "timestamp_interet": time.time()
                }
            }
        }
    )

def ecouter_les_annonces():
    """C'est la fonction principale, mon "radar".
       Elle va utiliser les Change Streams pour écouter en temps réel."""
    
    # Je définis un 'pipeline' pour mon Change Stream.
    # Je ne veux pas être notifié de *tous* les changements.
    pipeline = [
        # Je filtre pour ne recevoir que les opérations 'insert'
        # (les nouvelles annonces) et 'update' (les attributions).
        {'$match': {'operationType': {'$in': ['insert', 'update']}}}
    ]

    print(f"{LIVREUR_INFO['nom_livreur']} est en ligne et écoute les annonces...")
    
    try:
        # J'ouvre le 'Change Stream' sur ma collection, en lui passant mon pipeline.
        # J'utilise 'with ... as ...' pour être sûr que le stream
        # sera correctement fermé si je sors de la boucle (par ex. avec Ctrl+C).
        with annonces_collection.watch(pipeline) as stream:
            # C'est la boucle principale. Le script va "bloquer" ici
            # et attendre que des changements arrivent.
            for change in stream:
                
                # --- Cas 1: Une nouvelle annonce est publiée ---
                if change['operationType'] == 'insert':
                    # Je récupère le document complet qui vient d'être inséré.
                    annonce = change['fullDocument']
                    print(f"\nNOUVELLE ANNONCE Reçue : '{annonce['_id']}' pour {annonce['retribution_livreur']}€.")
                    
                    # Je simule ma décision : j'ai 80% de chances d'accepter.
                    if random.random() < 0.8:
                        # Si j'accepte, j'appelle ma fonction pour postuler.
                        manifester_interet(annonce['_id'])
                    else:
                        print(f"{LIVREUR_INFO['nom_livreur']} ignore cette annonce.")

                # --- Cas 2: Une annonce est mise à jour (probablement attribuée) ---
                elif change['operationType'] == 'update':
                    # Pour une mise à jour, je dois vérifier ce qui a changé.
                    # Je regarde si le champ 'livreur_attribue' fait
                    # partie des champs qui ont été mis à jour.
                    if 'livreur_attribue' in change['updateDescription']['updatedFields']:
                        # Si oui, ça veut dire qu'une attribution a eu lieu.
                        # Je récupère l'ID de l'annonce concernée...
                        annonce_id = change['documentKey']['_id']
                        # ...et je récupère la *nouvelle valeur* du champ.
                        livreur_attribue = change['updateDescription']['updatedFields']['livreur_attribue']
                        
                        # Je vérifie si l'ID du livreur attribué est MON ID.
                        if livreur_attribue and livreur_attribue['id_livreur'] == LIVREUR_INFO['id_livreur']:
                            print(f"GAGNÉ ! {LIVREUR_INFO['nom_livreur']} a obtenu la course '{annonce_id}'!")
                        else:
                            # Si ce n'est pas moi, j'affiche qui l'a eue.
                            print(f"PERDU... La course '{annonce_id}' a été prise par '{livreur_attribue['nom_livreur']}'.")

    except OperationFailure as e:
        # J'attrape l'erreur spécifique si le Replica Set n'est pas configuré.
        print(f"\nERREUR FATALE: Les Change Streams nécessitent un Replica Set. Lance MongoDB avec '--replSet rs0'.\n   Détail: {e}")
    except Exception as e:
        # J'attrape toute autre erreur inattendue.
        print(f"Erreur inattendue : {e}")

# --- Script Principal ---
if __name__ == "__main__":
    try:
        # Je lance ma fonction principale d'écoute.
        ecouter_les_annonces()
    except KeyboardInterrupt:
        # Je gère le cas où l'utilisateur fait Ctrl+C pour
        # arrêter le script proprement.
        print(f"\n{LIVREUR_INFO['nom_livreur']} se déconnecte.")
    finally:
        # Quoi qu'il arrive (erreur ou arrêt manuel),
        # je m'assure de fermer la connexion à MongoDB.
        client.close()
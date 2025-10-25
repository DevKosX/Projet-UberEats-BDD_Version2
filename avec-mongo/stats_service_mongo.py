#!/usr/bin/env python3
# J'importe 'time' pour gérer les pauses (time.sleep)
import time
# J'importe 'random' pour choisir une annonce au hasard dans ma liste
import random
# J'importe 'json' pour lire le fichier d'annonces
import json
# J'importe 'Path' de 'pathlib', c'est plus moderne pour gérer les chemins de fichiers
from pathlib import Path
# J'importe 'MongoClient' pour me connecter à MongoDB
from pymongo import MongoClient

# --- Configuration ---
# Je définis mon URI de connexion standard
MONGO_URI = "mongodb://localhost:27017/"
# Je définis le nom de la base de données
DB_NAME = "uber_eats_poc"
# Je définis le nom de la collection où je vais publier les annonces
COLLECTION_ANNONCES = "annonces"
# Je définis le temps (en secondes) que j'attends avant de choisir
# un livreur parmi ceux qui ont répondu.
DELAI_ATTENTE_SECONDES = 10

# --- Connexion à MongoDB ---
try:
    # J'initialise mon client. Je mets un timeout de 5s au cas où le serveur ne répond pas.
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # Je force la connexion avec 'server_info()'. Si ça échoue,
    # le 'except' plus bas sera déclenché.
    client.server_info()
    # Je sélectionne ma base de données...
    db = client[DB_NAME]
    # ...et ma collection.
    annonces_collection = db[COLLECTION_ANNONCES]
    print("Connexion à MongoDB réussie.")
except Exception as e:
    # Si la connexion échoue, j'affiche l'erreur et j'arrête le script.
    print(f"Erreur de connexion à MongoDB. Assure-toi qu'il est lancé et accessible.\n   Détail: {e}")
    exit()

# --- Fonctions ---

def charger_annonces_locales():
    """Je définis une fonction pour lire le fichier annonces.json."""
    # Je construis le chemin vers 'annonces.json' en me basant sur
    # l'emplacement de ce script Python.
    annonces_file = Path(__file__).resolve().parent / "annonces.json"
    
    # Je vérifie si le fichier existe avant d'essayer de l'ouvrir.
    if not annonces_file.exists():
        print(f"Fichier 'annonces.json' introuvable. Exécute d'abord le script de dénormalisation.")
        return [] # Je retourne une liste vide pour éviter un crash
    
    # J'ouvre le fichier en mode lecture ("r")
    with annonces_file.open("r", encoding="utf-8") as f:
        # Je charge le contenu JSON et je le retourne.
        return json.load(f)

def publier_annonce(annonce):
    """J'insère une annonce dans MongoDB. C'est ça qui va
       déclencher le 'Change Stream' chez les livreurs."""
    try:
        # Avant d'insérer, je m'assure que l'annonce est "propre".
        # Je la mets au statut 'PUBLIEE'.
        annonce['statut'] = 'PUBLIEE'
        # Je m'assure que la liste des intéressés est vide.
        annonce['interets_livreurs'] = []
        # Je m'assure qu'aucun livreur n'est encore attribué.
        annonce['livreur_attribue'] = None
        
        # J'insère l'annonce dans la collection.
        annonces_collection.insert_one(annonce)
        print(f"\n[MANAGER] Annonce '{annonce['_id']}' publiée pour {annonce['retribution_livreur']}€.")
        # Je retourne l'ID de l'annonce que je viens de créer.
        return annonce['_id']
    except Exception as e:
        # Si 'insert_one' échoue (par exemple, si l'_id existe déjà),
        # je ne veux pas que le script plante.
        print(f"[MANAGER] Annonce '{annonce['_id']}' existe déjà. On passe à la suivante.")
        # Je retourne None pour signaler que la publication a échoué.
        return None

def attribuer_course(annonce_id):
    """Ici, je récupère les intérêts, je choisis un livreur
       et je mets l'annonce à jour."""
    print(f"[MANAGER] Attente de {DELAI_ATTENTE_SECONDES} secondes pour les réponses...")
    # Je fais une pause. C'est la fenêtre pendant laquelle les livreurs
    # peuvent postuler (en mettant à jour l'annonce de leur côté).
    time.sleep(DELAI_ATTENTE_SECONDES)

    # Après la pause, je récupère la version la plus récente de l'annonce
    # depuis la base. Elle contient maintenant les réponses des livreurs.
    annonce = annonces_collection.find_one({"_id": annonce_id})
    
    # Je vérifie si l'annonce existe toujours et si quelqu'un (au moins un livreur)
    # s'est manifesté.
    if not annonce or not annonce.get('interets_livreurs'):
        print(f"[MANAGER] Personne n'a répondu à l'annonce '{annonce_id}'. Annulation.")
        # Si personne n'a répondu, je mets à jour l'annonce pour la marquer comme 'ANNULEE'.
        annonces_collection.update_one({"_id": annonce_id}, {"$set": {"statut": "ANNULEE"}})
        return # Je sors de la fonction

    # --- Logique de sélection ---
    # Si j'ai des réponses, je trie la liste 'interets_livreurs'.
    # J'utilise 'key=' avec une fonction lambda pour trier
    # en fonction du 'timestamp_interet', du plus petit (le plus tôt) au plus grand.
    interets = sorted(annonce['interets_livreurs'], key=lambda x: x['timestamp_interet'])
    
    # Je sélectionne le gagnant : c'est le premier de la liste triée (le plus rapide).
    livreur_gagnant = interets[0]

    print(f"[MANAGER] Le livreur '{livreur_gagnant['nom_livreur']}' a été choisi pour l'annonce '{annonce_id}'.")

    # Je prépare la mise à jour finale.
    annonces_collection.update_one(
        {"_id": annonce_id}, # Je cible l'annonce par son ID
        {
            "$set": { # Je mets à jour ces champs:
                "statut": "ATTRIBUEE", # Je la marque comme attribuée
                "livreur_attribue": { # J'enregistre qui a gagné
                    "id_livreur": livreur_gagnant['id_livreur'],
                    "nom_livreur": livreur_gagnant['nom_livreur']
                }
            }
        }
    )
    # C'est cette mise à jour que les livreurs vont recevoir
    # pour savoir s'ils ont gagné ou perdu.

# --- Script Principal ---
if __name__ == "__main__":
    # Au démarrage, je charge toutes les annonces depuis le fichier JSON.
    annonces_a_publier = charger_annonces_locales()
    if not annonces_a_publier:
        # Si le fichier est vide ou introuvable, j'arrête.
        exit()

    print("--- Démarrage du Manager Bot (MongoDB) ---")
    
    # Pour que la démo soit propre à chaque fois, je vide la collection.
    annonces_collection.delete_many({})
    print("Collection 'annonces' nettoyée.")
    
    try:
        # Je lance une boucle infinie pour publier des annonces en continu.
        while True:
            # Je choisis une annonce au hasard dans ma liste.
            annonce_choisie = random.choice(annonces_a_publier)
            
            # Je la publie. 'annonce_id' contiendra l'ID si ça réussit, ou None si c'est un doublon.
            annonce_id = publier_annonce(annonce_choisie)
            
            # Si la publication a fonctionné (l'ID n'est pas None)...
            if annonce_id:
                # ...je lance le processus d'attribution (attente + sélection).
                attribuer_course(annonce_id)
            
            # Je fais une pause avant de publier la prochaine annonce.
            print("\n--- Prochaine annonce dans 15 secondes ---")
            time.sleep(15)

    except KeyboardInterrupt:
        # Si je fais Ctrl+C dans le terminal, je sors de la boucle proprement.
        print("\nArrêt du Manager.")
    finally:
        # Quoi qu'il arrive (erreur ou arrêt manuel),
        # je m'assure de fermer la connexion à MongoDB.
        client.close()
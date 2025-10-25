#!/usr/bin/env python3
# J'importe Flask, qui est la base de mon serveur web.
# J'importe render_template pour pouvoir générer ma page HTML.
# J'importe request pour savoir quel livreur l'utilisateur a sélectionné.
from flask import Flask, render_template, request
# J'importe pandas, c'est ce qui me permet de lire facilement mon fichier CSV.
import pandas as pd
# J'importe redis pour me connecter à ma base de données de statistiques.
import redis
# J'importe datetime pour savoir quelle est la date d'aujourd'hui
# (car mes stats sont stockées par jour).
from datetime import datetime
# J'importe Path pour gérer les chemins de fichiers proprement.
from pathlib import Path
# J'importe random (même s'il n'est pas utilisé ici, il était dans le fichier original).
import random 

# --- Configuration ---
# Je définis le dossier de base de mon script pour trouver les autres fichiers.
BASE_DIR = Path(__file__).resolve().parent
# Je construis le chemin vers mon fichier CSV de livreurs.
CSV_FILE_PATH = BASE_DIR / "csv" / "Livreurs.csv" 

# Je définis les infos de connexion pour ma base de données Redis
# où sont stockées les statistiques.
REDIS_HOST = 'localhost'
REDIS_PORT = 6379

# --- Connexion BDD (Redis) ---
try:
    # J'initialise ma connexion à Redis.
    # J'utilise 'decode_responses=True' pour que Redis me renvoie
    # des chaînes de caractères (str) plutôt que des bytes.
    r_stats = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    # Je fais un 'ping' pour vérifier que la connexion fonctionne.
    r_stats.ping()
    print("Connexion à Redis pour les stats réussie.")
except Exception as e:
    # Si Redis n'est pas démarré, je ne veux pas que mon dashboard plante.
    # Je mets juste ma variable de connexion à None et j'affiche un avertissement.
    print(f"AVERTISSEMENT: Erreur connexion BDD Stats Redis: {e}")
    r_stats = None

# --- Initialisation de Flask ---
# Je crée mon application web Flask.
app = Flask(__name__)

def get_all_livreurs_from_csv():
    """
    Je crée une fonction pour lire mon 'Livreurs.csv'.
    Le but est d'avoir la liste complète pour remplir le menu déroulant.
    """
    try:
        # Je lis le fichier CSV avec pandas, en n'oubliant pas
        # que mon séparateur est un point-virgule ';'.
        df = pd.read_csv(CSV_FILE_PATH, sep=';')
        # Je convertis le DataFrame en une liste de dictionnaires.
        # C'est un format parfait pour mon template HTML.
        livreurs = df.to_dict(orient='records')
        print(f"Trouvé {len(livreurs)} livreurs dans le CSV.")
        return livreurs
    except FileNotFoundError:
        # Si le fichier n'est pas là, j'affiche une erreur claire.
        print(f"ERREUR: Fichier {CSV_FILE_PATH} introuvable. Vérifie le chemin.")
        return []
    except Exception as e:
        print(f"Erreur en lisant le CSV: {e}")
        return []

def get_stats_for_livreur(livreur_id, nom_livreur):
    """
    C'est la fonction qui va chercher les VRAIES stats du jour
    pour un livreur spécifique dans ma base Redis.
    """
    # D'abord, je vérifie si ma connexion à Redis a fonctionné au démarrage.
    if not r_stats:
        print("Service de stats Redis non connecté.")
        return None

    # Je récupère la date d'aujourd'hui au format 'AAAA-MM-JJ'.
    date_str = datetime.now().strftime('%Y-%m-%d')
    # Je reconstruis la clé de stat *exactement* comme mon autre script
    # ('stats_service_redis.py') l'a créée.
    cle_stats = f"stats:{livreur_id}:{date_str}" 
    
    try:
        # J'utilise HGETALL (Hash Get All) pour récupérer tous les champs
        # (gains_du_jour, courses_terminees) de ce Hash d'un coup.
        stats_data = r_stats.hgetall(cle_stats)
        
        if stats_data:
            # Si j'ai trouvé des données (le Hash n'est pas vide)...
            # Je prépare un dictionnaire propre.
            stats_data_complet = {
                "nom_livreur": nom_livreur,
                # Je convertis en 'float' ce que Redis m'a donné en 'str'.
                # J'utilise .get() avec 0.0 par défaut par sécurité.
                "gains_du_jour": float(stats_data.get("gains_du_jour", 0.0)),
                # Pareil pour le nombre de courses, mais en 'int'.
                "courses_terminees": int(stats_data.get("courses_terminees", 0))
            }
            print(f"Stats réelles trouvées pour {livreur_id}: {stats_data_complet}")
            return stats_data_complet
        else:
            # Si le Hash est vide, ça veut dire que ce livreur
            # n'a juste pas encore fait de course aujourd'hui.
            print(f"Aucune stat pour aujourd'hui trouvée pour {livreur_id}. Renvoi 0.")
            # Je renvoie quand même un objet avec des zéros.
            return {
                "nom_livreur": nom_livreur,
                "gains_du_jour": 0,
                "courses_terminees": 0
            }
            
    except Exception as e:
        # Si la commande Redis plante, je logue l'erreur.
        print(f"Erreur en récupérant les stats Redis pour {livreur_id}: {e}")
        return None

# --- Définition de la Route (URL) ---
# Je définis l'URL de mon dashboard.
@app.route("/dashboard")
def show_dashboard():
    
    # Je regarde si l'URL contient un 'livreurId' (ex: /dashboard?livreurId=3)
    # C'est ce qui se passe quand l'utilisateur choisit dans le menu.
    selected_livreur_id_str = request.args.get('livreurId')
    
    # Je charge la liste complète de tous les livreurs pour le menu déroulant.
    tous_les_livreurs = get_all_livreurs_from_csv()
    
    # J'initialise les stats du livreur à None.
    stats_livreur_selectionne = None
    
    # Si l'utilisateur a bien sélectionné un livreur (l'ID est dans l'URL)...
    if selected_livreur_id_str:
        try:
            # Je dois retrouver les infos complètes (surtout le nom)
            # de ce livreur à partir de son ID.
            # J'utilise 'next' pour trouver le premier livreur dans ma liste
            # qui correspond à l'ID.
            livreur_selectionne = next(
                (l for l in tous_les_livreurs if str(l['id_livreur']) == selected_livreur_id_str), 
                None
            )
            
            if livreur_selectionne:
                # Si je l'ai trouvé, je récupère son nom.
                nom_livreur = livreur_selectionne.get('nom_livreur', 'Inconnu')
                # Et maintenant, j'appelle ma fonction Redis
                # pour avoir ses vraies stats.
                stats_livreur_selectionne = get_stats_for_livreur(livreur_selectionne['id_livreur'], nom_livreur)
            else:
                print(f"ID Livreur {selected_livreur_id_str} sélectionné mais non trouvé dans le CSV.")

        except Exception as e:
            print(f"Erreur lors de la récupération des stats: {e}")
            stats_livreur_selectionne = None
            
    # C'est l'étape finale : je renvoie le fichier HTML 'dashboard.html'
    # et je lui "passe" les variables dont il a besoin.
    return render_template(
        'dashboard.html', 
        allLivreurs=tous_les_livreurs,         # Pour remplir le menu déroulant
        selectedLivreurId=selected_livreur_id_str, # Pour que le menu affiche le bon nom
        stats=stats_livreur_selectionne         # L'objet contenant les chiffres à afficher
    )

# --- Démarrage du serveur ---
if __name__ == "__main__":
    print("--- Démarrage du serveur Dashboard Python (Flask) ---")
    print("Ouvrez http://127.0.0.1:5000/dashboard dans votre navigateur.")
    # Je lance le serveur. 'debug=True' est pratique car
    # il redémarre le serveur tout seul à chaque fois que je sauvegarde ce fichier.
    app.run(debug=True, port=5000)

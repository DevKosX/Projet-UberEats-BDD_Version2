#!/usr/bin/env python3
# J'ajoute le shebang pour indiquer que c'est un script Python 3.
import pandas as pd
import json
from pathlib import Path
import math

# J'importe pandas, c'est mon outil principal pour lire et manipuler les fichiers CSV.
# J'importe json pour pouvoir écrire le fichier JSON final.
# J'importe Path de pathlib. C'est beaucoup plus propre pour gérer les chemins de fichiers.
# J'importe math. J'en ai besoin spécifiquement pour 'math.isnan'
# afin de vérifier si un 'id_livreur_attribue' est vide (NaN) dans mes données pandas.


# --- Configuration ---
# Je définis le dossier de base de mon script.
# `Path(__file__).resolve().parent` c'est la façon fiable d'obtenir le dossier
# où se trouve ce script.
BASE_DIR = Path(__file__).resolve().parent
# Je définis le sous-dossier 'csv' qui se trouve à côté de mon script.
CSV_DIR = BASE_DIR / "csv" 

# Je crée un dictionnaire qui centralise tous les chemins vers mes fichiers CSV.
# C'est plus simple à gérer. Si un nom de fichier change, je n'aurai
# qu'à le modifier ici.
FICHIERS_CSV = {
    "clients": CSV_DIR / "Clients.csv",
    "restaurants": CSV_DIR / "Restaurants.csv",
    "plats": CSV_DIR / "Plats.csv",
    "livreurs": CSV_DIR / "Livreurs.csv",
    "managers": CSV_DIR / "Managers.csv",
    "commandes": CSV_DIR / "Commandes.csv",
    "details_commandes": CSV_DIR / "Details_Commande.csv",
    "interets_livreurs": CSV_DIR / "Interets_Livreurs.csv"
}

# --- Fonctions ---

def charger_csv(fichier_path, index_col):
    """
    Je crée une fonction réutilisable pour charger un CSV.
    Elle prend le chemin du fichier et la colonne que je veux utiliser
    comme clé (index_col) pour mon futur dictionnaire.
    Elle retourne les données comme un dictionnaire (une map).
    """
    # Je fais une vérification. Si le fichier n'existe pas,
    # j'affiche un avertissement et je retourne un dictionnaire vide
    # pour que le reste du script ne plante pas.
    if not fichier_path.exists():
        print(f"Fichier manquant : {fichier_path.name}")
        return {}
    
    # J'utilise pandas pour lire le CSV. Je spécifie bien sep=';'
    # car mes fichiers ne sont pas séparés par des virgules.
    df = pd.read_csv(fichier_path, sep=';')
    
    # Ça, c'est une étape importante. Pandas utilise 'NaN' pour les cases vides.
    # JSON ne sait pas gérer 'NaN'. Donc je remplace tous les 'NaN' par 'None',
    # qui sera correctement converti en 'null' dans le JSON final.
    df = df.where(pd.notna(df), None)
    
    # Je convertis tout mon DataFrame en une liste de dictionnaires,
    # où chaque dictionnaire représente une ligne du CSV.
    records = df.to_dict(orient="records")
    
    # Je transforme cette liste en un gros dictionnaire.
    # J'utilise l'index_col (ex: 'id_client') comme clé.
    # Ça me permet de faire des recherches très rapides (ex: clients_map[123])
    # au lieu de devoir boucler sur une liste à chaque fois. C'est une "lookup map".
    return {record[index_col]: record for record in records}

def denormaliser_donnees():
    """C'est la fonction principale qui va charger et assembler (dénormaliser)
    toutes les données pour créer les annonces."""
    
    print("Chargement de toutes les données CSV...")
    
    # J'appelle ma fonction 'charger_csv' pour chaque fichier "parent" (clients, restaurants, etc.).
    # J'obtiens des dictionnaires "map" pour un accès instantané aux données.
    clients_map = charger_csv(FICHIERS_CSV["clients"], 'id_client')
    restaurants_map = charger_csv(FICHIERS_CSV["restaurants"], 'id_restaurant')
    plats_map = charger_csv(FICHIERS_CSV["plats"], 'id_plat')
    livreurs_map = charger_csv(FICHIERS_CSV["livreurs"], 'id_livreur')
    managers_map = charger_csv(FICHIERS_CSV["managers"], 'id_manager')
    
    # Pour les commandes, je n'ai pas besoin d'une map. Je vais boucler dessus.
    # Je les charge simplement en tant que DataFrame...
    commandes_df = pd.read_csv(FICHIERS_CSV["commandes"], sep=';')
    # ...et je les convertis en liste de dictionnaires.
    commandes = commandes_df.to_dict(orient="records")

    # Pour les 'details_commandes', c'est une relation 1-à-N.
    # Une commande peut avoir plusieurs plats. Je charge tout...
    details_df = pd.read_csv(FICHIERS_CSV["details_commandes"], sep=';')
    # ...et j'utilise 'groupby('id_commande')' de pandas.
    # Ça me crée un dictionnaire où chaque clé est un 'id_commande'
    # et la valeur est la liste de tous les plats (détails) de cette commande.
    details_par_commande = details_df.groupby('id_commande').apply(lambda x: x.to_dict('records')).to_dict()

    # Je fais exactement la même chose pour les intérêts des livreurs.
    interets_df = pd.read_csv(FICHIERS_CSV["interets_livreurs"], sep=';')
    # J'obtiens une map où 'id_commande' me donne la liste des livreurs intéressés.
    interets_par_commande = interets_df.groupby('id_commande').apply(lambda x: x.to_dict('records')).to_dict()

    print("Dénormalisation des annonces en cours...")
    # J'initialise la liste qui contiendra mes documents JSON finaux.
    annonces_denormalisees = []

    # Je commence ma boucle principale. Je vais traiter chaque commande, une par une.
    for cmd in commandes:
        # Je récupère l'ID de la commande en cours.
        cmd_id = cmd['id_commande']
        
        # --- Dénormalisation des détails de la commande (les plats) ---
        # Je vais chercher les détails (plats) pour cet ID de commande.
        # J'utilise .get(cmd_id, []) pour avoir une liste vide si jamais
        # une commande n'a aucun plat (ce qui évite un crash).
        details_bruts = details_par_commande.get(cmd_id, [])
        items_commande = [] # J'initialise la liste des plats pour cette commande.
        for detail in details_bruts:
            # Pour chaque plat, je vais chercher ses infos complètes (nom, prix)
            # dans la 'plats_map' que j'ai chargée au début.
            # J'utilise .get() avec un dict vide {} au cas où un plat serait introuvable.
            plat_info = plats_map.get(detail['id_plat'], {})
            # Je construis mon sous-document "item" propre.
            items_commande.append({
                "id_plat": plat_info.get('id_plat'),
                "nom_plat": plat_info.get('nom_plat'),
                "quantite": detail.get("quantite", 1),
                "prix": plat_info.get('prix_plat')
            })

        # --- Dénormalisation des intérêts livreurs ---
        # Je fais la même logique pour les livreurs intéressés.
        # Je récupère la liste des intérêts pour cette commande.
        interets_bruts = interets_par_commande.get(cmd_id, [])
        livreurs_interesses = []
        for interet in interets_bruts:
            # Pour chaque intérêt, je vais chercher les infos complètes du livreur
            # dans ma 'livreurs_map'.
            livreur_info = livreurs_map.get(interet['id_livreur'], {})
            # J'ajoute le livreur et son timestamp à ma liste.
            livreurs_interesses.append({
                "id_livreur": livreur_info.get('id_livreur'),
                "nom_livreur": livreur_info.get('nom_livreur'),
                "timestamp_interet": interet.get('timestamp_interet')
            })

        # --- Gestion du livreur attribué (qui a gagné la course) ---
        # Ici, je gère le cas du livreur qui a *gagné* la course.
        # Je récupère l'ID du livreur attribué. Il peut être vide.
        livreur_attribue_id = cmd.get('id_livreur_attribue')
        
        # Je dois vérifier deux choses :
        # 1. Que l'ID n'est pas None (ou vide).
        # 2. Qu'il n'est pas 'NaN' (ce que pandas fait pour les nombres vides).
        # C'est pour ça que j'ai importé 'math.isnan'.
        if livreur_attribue_id and not math.isnan(livreur_attribue_id):
            # Si j'ai un ID valide, je vais chercher les infos du livreur.
            # Je dois le convertir en 'int()' car pandas le lit parfois comme un float (ex: 123.0).
            livreur_attribue_info = livreurs_map.get(int(livreur_attribue_id))
        else:
            # Si personne n'est attribué, je mets 'None'.
            livreur_attribue_info = None

        # --- Assemblage final de l'annonce ---
        # C'est l'étape finale. Je construis mon gros objet JSON "annonce".
        annonce = {
            "_id": f"annonce_{cmd_id}", # Je crée un _id unique pour MongoDB.
            "statut": cmd.get('statut_commande'),
            "date_creation": cmd.get('date_creation'),
            
            # Et là, j'intègre directement les objets complets (dénormalisation).
            # Au lieu d'un simple 'id_client', je mets tout l'objet 'client'.
            "client": clients_map.get(cmd['id_client'], {}),
            "restaurant": restaurants_map.get(cmd['id_restaurant'], {}),
            "publication_par": managers_map.get(cmd['id_manager_publication'], {}),
            
            # J'ajoute les listes que j'ai construites juste avant.
            "details_commande": items_commande,
            "prix_total": cmd.get('prix_total'),
            "retribution_livreur": cmd.get('retribution_livreur'),
            
            "interets_livreurs": livreurs_interesses,
            # Et enfin, le livreur gagnant (qui peut être 'None').
            "livreur_attribue": livreur_attribue_info
        }
        
        # J'ajoute cette annonce complète à ma liste finale.
        annonces_denormalisees.append(annonce)

    # Une fois la boucle sur toutes les commandes terminée, je retourne la liste complète.
    return annonces_denormalisees

# C'est le point d'entrée de mon script.
if __name__ == "__main__":
    # Je mets tout mon processus principal dans un bloc 'try...except'.
    # C'est plus robuste. Si quelque chose plante (ex: un fichier manquant),
    # j'aurai un message d'erreur clair au lieu d'un crash moche.
    try:
        # J'appelle ma fonction principale pour récupérer toutes les données.
        data_denormalisee = denormaliser_donnees()
        
        # Je définis le nom de mon fichier de sortie.
        output_json = BASE_DIR / "annonces.json"
        
        # J'ouvre ce fichier en mode écriture ("w").
        # J'utilise 'encoding="utf-8"' pour être sûr de bien gérer les accents.
        with output_json.open("w", encoding="utf-8") as f:
            # J'utilise 'json.dump' pour écrire mes données.
            # 'ensure_ascii=False' est très important pour que les accents
            # (comme 'Véloce') soient écrits tels quels et non en codes \uXXXX.
            # 'indent=2' c'est pour que le JSON soit lisible (joli).
            json.dump(data_denormalisee, f, ensure_ascii=False, indent=2)

        # Je confirme que tout s'est bien passé.
        print(f"\nDénormalisation terminée : {output_json.name} généré ({len(data_denormalisee)} annonces dénormalisées).")
        
    except FileNotFoundError as e:
        # J'attrape spécifiquement l'erreur si un fichier CSV n'est pas trouvé.
        print(f"\nERREUR : Fichier CSV introuvable. Vérifie que tous tes fichiers sont dans le dossier 'csv/'.\n   Détail: {e}")
    except KeyError as e:
        # J'attrape l'erreur si un nom de colonne (ex: 'id_client')
        # n'est pas trouvé dans un CSV. Ça veut dire qu'il y a une
        # incohérence entre mon code et mes fichiers.
        print(f"\nERREUR : Colonne manquante dans un CSV. Nom de la colonne : {e}.\n   Vérifie que les en-têtes de tes fichiers CSV correspondent bien au code.")
    except Exception as e:
        # J'attrape toutes les autres erreurs possibles.
        print(f"\nERREUR inattendue : {e}")
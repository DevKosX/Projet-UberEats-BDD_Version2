#!/usr/bin/env python3
# J'importe 'redis' pour me connecter et interagir avec Redis.
import redis
# J'importe 'json' car les notifications que je vais recevoir
# sur le canal Pub/Sub seront au format JSON.
import json
# J'importe 'threading', même si je ne l'utilise pas directement ici,
# c'est souvent utile dans les scripts d'écoute. (Note: il n'est pas utilisé
# dans ce script précis, mais je le laisse au cas où, bien que 'json' soit
# celui qui est vraiment utilisé pour le 'loads').
# Ah non, en fait, je n'ai pas besoin de 'threading' ici car je n'ai qu'une
# seule tâche d'écoute. Je vais le laisser, mais c'est 'json' le plus important.
# (Correction : Le script original avait 'threading', mais ce code-ci ne
# l'utilise pas. Je vais commenter ce qui est présent.)
# (Re-correction : Le script original n'avait pas 'threading', je me suis trompé
# en lisant. Je commente donc ce qui est là.)
# J'importe 'datetime' pour générer des clés de statistiques uniques par jour.
from datetime import datetime

# --- Configuration ---
# Je définis les infos de connexion à Redis.
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
# Je définis le canal que je dois écouter. C'est le même canal
# sur lequel le 'manager_redis' publie les résultats.
NOTIFICATIONS_CHANNEL = 'notifications_channel'

# --- Connexion à Redis ---
try:
    # J'initialise ma connexion à Redis.
    # 'decode_responses=True' est important pour que Redis me
    # retourne des chaînes de caractères (str) au lieu de bytes.
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    # Je fais un 'ping()' pour m'assurer que la connexion est bien établie.
    r.ping()
    print("--- Démarrage du Service de Statistiques (Redis) ---")
    print("Connecté à Redis et à l'écoute des notifications...")
except Exception as e:
    # Si je n'arrive pas à me connecter, j'affiche l'erreur et j'arrête tout.
    print(f"Erreur de connexion à Redis: {e}")
    exit()

# --- Fonctions ---

def obtenir_cle_stats_jour(livreur_id):
    """
    Je crée une fonction pour générer un nom de clé Redis unique.
    Je veux que mes statistiques soient groupées par livreur ET par jour.
    """
    # Je récupère la date actuelle au format "AAAA-MM-JJ".
    date_str = datetime.now().strftime('%Y-%m-%d')
    # Je construis la clé, par exemple : "stats:1:2025-10-25"
    return f"stats:{livreur_id}:{date_str}"

def mettre_a_jour_stats(livreur_id, retribution):
    """
    C'est ici que je mets à jour les stats du livreur dans un Hash Redis.
    J'utilise un Hash pour stocker plusieurs compteurs (gains, courses)
    sous une seule clé (celle générée par 'obtenir_cle_stats_jour').
    """
    try:
        # Je récupère la clé unique pour ce livreur et ce jour.
        cle_stats = obtenir_cle_stats_jour(livreur_id)
        
        # J'utilise 'HINCRBYFLOAT'. C'est la commande parfaite pour ça.
        # "Hash INCRement BY FLOAT". Elle ajoute (atomiquement)
        # la 'retribution' (un float) au champ 'gains_du_jour'
        # dans mon Hash. Si la clé ou le champ n'existe pas, Redis les crée.
        gains = r.hincrbyfloat(cle_stats, "gains_du_jour", retribution)
        
        # J'utilise 'HINCRBY' (pour les entiers) pour compter le nombre de courses.
        # J'incrémente le champ 'courses_terminees' de 1.
        courses = r.hincrby(cle_stats, "courses_terminees", 1)
        
        # Je définis un temps d'expiration (TTL) sur ma clé de statistiques.
        # Je mets 36 heures (en secondes : 36 * 60 * 60 = 129600).
        # Pourquoi 36h et pas 24h ? C'est une marge de sécurité.
        # Si mon script tourne juste après minuit, je veux être sûr
        # que les stats de la veille sont toujours là.
        r.expire(cle_stats, 129600) 
        
        # J'affiche un log pour confirmer la mise à jour.
        print(f"[STATS] Livreur {livreur_id} mis à jour : {courses} courses, {gains:.2f}€ ce jour.")
    
    except Exception as e:
        # Je gère les erreurs au cas où Redis serait indisponible.
        print(f"[ERREUR STATS] Impossible de mettre à jour les stats pour {livreur_id}: {e}")

def ecouter_notifications():
    """
    C'est ma fonction d'écoute principale. Elle se branche
    sur le canal de notifications et attend les messages.
    """
    # J'initialise l'objet Pub/Sub.
    pubsub = r.pubsub()
    # Je m'abonne au canal que j'ai défini dans ma config.
    pubsub.subscribe(NOTIFICATIONS_CHANNEL)
    
    # 'pubsub.listen()' est une boucle bloquante.
    # Mon script va passer son temps ici, à attendre des messages.
    for message in pubsub.listen():
        # Je vérifie que c'est bien un message ('message') et non
        # un message de contrôle (comme la confirmation d'abonnement).
        if message['type'] == 'message':
            try:
                # Je décode la chaîne JSON que j'ai reçue.
                notification = json.loads(message['data'])
                
                # Je ne m'intéresse qu'aux notifications qui confirment
                # qu'une course a été 'ATTRIBUEE'. J'ignore les 'ANNULEE'.
                if notification.get('status') == 'ATTRIBUEE':
                    # J'extrais l'ID du livreur gagnant.
                    livreur_id = notification['gagnant']['id_livreur']
                    # J'extrais la rétribution. J'utilise .get()
                    # avec une valeur par défaut (0.0) au cas où
                    # le champ serait manquant.
                    retribution = notification.get('retribution', 0.0)
                    
                    # J'appelle ma fonction de mise à jour des stats.
                    mettre_a_jour_stats(livreur_id, retribution)
                    
            except (json.JSONDecodeError, KeyError) as e:
                # Si le message n'est pas un JSON valide ou s'il
                # manque une clé (comme 'status' ou 'gagnant'),
                # j'affiche une erreur mais je continue de tourner.
                print(f"[ERREUR] Message de notification mal formé: {e}")

# --- Script Principal ---
if __name__ == "__main__":
    try:
        # Je lance ma fonction d'écoute. Le script va
        # rester bloqué ici, ce qui est le comportement attendu.
        ecouter_notifications()
    except KeyboardInterrupt:
        # Je gère le Ctrl+C pour quitter proprement.
        print("\nArrêt du Service de Statistiques.")
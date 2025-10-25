# 🛵 Simulation UberEats V2 : MongoDB, Redis & Dashboard Flask

Ce projet simule un système de dispatch de courses en temps réel, similaire à UberEats, en utilisant deux backends (MongoDB et Redis). Il inclut désormais un **dashboard web en direct** (via Flask) pour visualiser les statistiques des livreurs (nombre de courses et gains) au fur et à mesure que la simulation se déroule.

---

## 1. Architecture du Projet

Le projet est divisé en trois piliers principaux :

### 1.1 La Simulation (Producteurs/Consommateurs)

* `manager_redis.py` / `manager_mongo.py` : Agit comme la plateforme (Producteur). Il lit les courses depuis `annonces.json` et les publie (soit sur un canal Redis, soit en les insérant dans MongoDB).
* `livreur_redis.py` / `livreur_mongo.py` : Agit comme le livreur (Consommateur). Il écoute les nouvelles courses, décide d'y répondre (en compétition avec d'autres livreurs) et reçoit une notification de gain ou de perte.

### 1.2 Le Service de Statistiques (L'Auditeur)

* `stats_service_redis.py` / `stats_service_mongo.py` : Un service crucial qui écoute en permanence les notifications d'attribution de courses.
* Quand un livreur gagne une course, ce service intercepte l'information et **met à jour les statistiques (gains, nb_courses) dans une base de données Redis**.

### 1.3 Le Dashboard (L'Interface de Visualisation)

* `app.py` : Un serveur web léger (utilisant **Flask**) qui sert l'interface utilisateur.
* `templates/dashboard.html` : La page web que vous consultez.
* **Logique :** Quand vous chargez le dashboard dans votre navigateur, le serveur `app.py` va **lire les statistiques directement depuis la base de données Redis** (mise à jour par le `stats_service_redis`) et les affiche.

**Note importante :** Dans cette version, le `dashboard.html` (via `app.py`) est câblé pour lire les statistiques **uniquement depuis Redis**. Par conséquent, seules les simulations lancées avec `manager_redis.py` et `livreur_redis.py` mettront à jour le dashboard.

---

## 2. Prérequis

Avant de commencer, assurez-vous d'avoir :

* Python 3.x
* Les serveurs de base de données en cours d'exécution :
    * **Redis Server** (lancez `redis-server`)
    * **MongoDB Server** (lancé en mode Replica Set, ex: `mongod --replSet rs0`)
* Les bibliothèques Python requises. Installez-les avec pip :

    ```bash
    pip install flask pandas redis pymongo
    ```

* Le fichier `annonces.json`. S'il n'existe pas, générez-le en lançant :

    ```bash
    python denormalisation.py
    ```

---

## 3. Comment Lancer la Simulation (Redis) et Voir le Dashboard

Pour voir le système complet en action, vous aurez besoin d'ouvrir **5 terminaux**. Suivez cet ordre :

### Étape 1 : Lancer le Serveur Redis

(Assurez-vous qu'il tourne sur le port 6379 par défaut)

```bash
redis-server

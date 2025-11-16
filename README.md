# Simulation UberEats V2 : MongoDB, Redis & Dashboard Flask

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

### Étape 0 : Générer le fichier annonces.json (Terminal 0)

```bash
source myredis/bin/activate 
python denormalisation.py
```

    

## 3. Comment Lancer la Simulation (Redis) et Voir le Dashboard

Pour voir le système complet en action, vous aurez besoin d'ouvrir **5 terminaux**. Suivez cet ordre :

### Étape 1 : Lancer le Serveur Redis (Terminal 1)

(Assurez-vous qu'il tourne sur le port 6379 par défaut)

```bash
redis-server
```
---

### Étape 2 : Lancer le back-end pour avoir le dashbord (Terminal 2)

```bash
source myredis/bin/activate
python stats_service_redis.py
```
---


### Étape 3 : Lancer le app.py pour avoir un dashbord (Terminal 3)

```bash
source venv/bin/activate
python app.py
```
---


### Étape 4 : Lancer le livreur 1 : Auguste Tanguy (Terminal 4)

```bash
source myredis/bin/activate
python3 livreur_redis.py 1 "Auguste Tanguy"
```
---


### Étape 5 : Lancer le livreur 2 : Julie de la Lévêque (Terminal 5)

```bash
source myredis/bin/activate
python3 livreur_redis.py 2 "Julie de la Lévêque"
```
---


### Étape 6 : Lancer le livreur 3 : Julien Jacquet-Barbier (Terminal 6)

```bash
source myredis/bin/activate
python3 livreur_redis.py 3 "Julien Jacquet-Barbier"
```
---

### Étape 7 : Lancer le manager (Terminal 7)

```bash
source myredis/bin/activate
python3 manager_redis.py 
```
---
### Étape 8 : Acceder à la page web 

```bash

http://127.0.0.1:5000/dashboard?livreurId=
```
---

# Guide de Lancement : Simulation MongoDB

Ce guide explique comment lancer les 4 services (Dashboard, Stats, Manager, Livreurs) pour la version MongoDB.

---

### Prérequis Impératif : MongoDB Replica Set

Avant de lancer quoi que ce soit, vérifiez que votre serveur MongoDB tourne en mode "Replica Set". Les Change Streams (`watch()`) ne fonctionnent **pas** sans cela.

```bash
# Si ce n'est pas fait, lancez-le une fois
mongosh --eval "rs.initiate()"
```

### Étape 0 : Générer le fichier annonces.json (Terminal 0)

```bash
source mongo/bin/activate
python denormalisation.py
```

### Étape 1 : Lancer le back-end des stats livreur (Terminal 1)

(Assurez-vous qu'il tourne sur le port 6379 par défaut)

```bash
source mongo/bin/activate
python3 stats_service_mongo.py 
```


### Étape 2 : Lancer le app.py (Terminal 2)
```bash
source venv/bin/activate
python app.py
```

### Étape 3 : Lancer le livreur 1 (Terminal 3)
```bash
source mongo/bin/activate
python3 livreur_mongo.py 1 "Auguste Tanguy"

```

### Étape 4 : Lancer le livreur 2 (Terminal 4)
```bash
source mongo/bin/activate
python3 livreur_mongo.py 2 "Julie de la Lévêque"
```

### Étape 5 : Lancer le manager (Terminal 6)
```bash
source mongo/bin/activate
python3 manager_mongo.py
```

### Guide : Consulter vos Bases de Données (Redis & MongoDB)

Voici les commandes essentielles pour inspecter vos données "en direct" pendant que vos simulations tournent.

### 1. Consulter Redis (L'info "à chaud")
-

- Ouvrez un nouveau terminal et lancez l'interface de commande Redis.
```bash
redis-cli
```
---

Une fois dedans (vous verrez 127.0.0.1:6379>), voici les commandes les plus utiles pour votre projet :

Voir les clés de statistiques (Dashboard)

Pour voir les statistiques du livreur "Julie" (ID 2) pour aujourd'hui (par exemple, 16 Nov 2025) :

# HGETALL = "Hash Get All" (Obtenir tous les champs et valeurs d'un Hash)
# Remplacez l'ID et la date par ce que vous testez
HGETALL stats:2:2025-11-16


Résultat attendu :

1) "gains_du_jour"
2) "28.5"
3) "courses_terminees"
4) "2"


Voir la compétition en direct (Debug)

La commande MONITOR vous montre toutes les commandes que Redis reçoit en temps réel. C'est le meilleur moyen de voir la compétition.

MONITOR


Vous verrez en direct :

... "HSET" "interets:annonce_123" "1" "1678886400.123"
... "HSET" "interets:annonce_123" "2" "1678886400.125"
... "HGETALL" "interets:annonce_123"
... "SET" "KEY_COURSE_ACTIVE" "..."


### 2. Consulter MongoDB (L'info "durable")
---

Vous avez deux options :

### Option A : En ligne de commande (Rapide)

```bash
mongosh
```
---
Une fois dedans, voici les commandes (bien que ce soit du Javascript, je les mets en bash comme demandé) :

// 1. Sélectionner votre base de données


```bash
use uber_eats_poc
```
---

// 2. Voir toutes les annonces de course qui ont été insérées

```bash
db.annonces.find().pretty()
```

// 3. Voir l'état d'une course spécifique (ex: qui a postulé)
```bash
db.annonces.find({ _id: "annonce_M-9672" }).pretty()
```
---

// 4. Voir les statistiques du dashboard
```bash
db.stats_livreurs.find().pretty()
```

### Option B : Avec l'Interface Graphique (Recommandé)

Pour une vue claire, utilisez MongoDB Compass (l'outil graphique officiel).

Lancez Compass et connectez-vous à votre base locale (mongodb://localhost:27017/).

Sur la gauche, cliquez sur la base de données uber_eats_poc.

Cliquez sur la collection annonces ou stats_livreurs.

Vous pouvez voir toutes les données, les filtrer et même les modifier visuellement.







### 👤 Auteur
---
## Mohamed Kosbar - Projet Universitaire BUT3 


# 🛵 Projet Simulation UberEats : Comparaison Redis vs. MongoDB

Ce projet vise à simuler la logique de gestion des courses (dispatch) d'une plateforme de livraison (type UberEats) en utilisant deux architectures de bases de données distribuées différentes : **Redis (Pub/Sub)** et **MongoDB (Change Streams)**.

---

## 1. Architecture du Projet

Le cœur du projet repose sur le concept de **Producteur/Consommateur** et de **Compétition en temps réel** entre les Livreurs.

### 1.1 Composants Communs

| Composant | Rôle | Description |
| :--- | :--- | :--- |
| **Manager** | **Producteur** | Simule la plateforme. Publie l'annonce d'une nouvelle course et sélectionne le Livreur le plus rapide. |
| **Livreur** | **Consommateur/Compétiteur** | Simule l'application du Livreur. Reçoit l'annonce, manifeste son intérêt, et accepte la course s'il est sélectionné. |
| **`denormalisation.json`** | **Source de Données** | Fichier unique contenant les données de commandes (restaurants, clients, etc.) utilisées pour simuler les annonces. |

---

### 1.2 Architecture Redis (Messagerie Événementielle)

Cette architecture utilise **Redis** comme un courtier de messages et un magasin de données temporaire.

* **Communication :** Utilisation du modèle **Pub/Sub** pour la diffusion instantanée des annonces aux Livreurs.
* **Sélection :** Le Manager attend pendant un temps défini (5 secondes) que les Livreurs enregistrent leur intérêt via la commande `HSET`. La sélection est basée sur le **timestamp le plus précoce**.
* **État :** Stockage de l'état temporaire (`ubereats:course:active`) et des intérêts (`ubereats:interet:Oxxxx`) via des commandes Redis classiques.

---

### 1.3 Architecture MongoDB (Flux de Changement Persistant)

Cette architecture utilise **MongoDB** (lancé en Replica Set) comme base de données principale et exploite ses **Change Streams** pour la communication en temps réel.

* **Communication :** Le Manager insère un document. Les Livreurs surveillent la collection (`annonces`) via un **Change Stream** et reçoivent l'événement d'insertion en temps réel.
* **Sélection :** La sélection est gérée par une **mise à jour atomique conditionnelle** (`$set` avec une condition sur le statut). Le premier Livreur à réussir à changer le statut du document de `ANNONCE_PUBLIEE` à `LIVREUR_SELECTIONNE` gagne.
* **État :** L'état de la course est persistant et contenu intégralement dans un **unique document JSON** dans la collection `annonces`.

---

## 2. Prérequis Techniques

Pour exécuter ce projet, vous devez disposer des éléments suivants :

* **Python 3.x** (avec des environnements virtuels `myredis` et `mymongo`)
* **Redis Server** (version 5.0 ou supérieure recommandée)
* **MongoDB Server** (version 4.0 ou supérieure, **doit être lancé en Replica Set**).
* **Librairies Python :** `redis`, `pymongo`, `dnspython` (à installer dans les environnements virtuels respectifs).

---

## 3. Structure des Dossiers

Voici le contenu intégral de votre fichier README.md, incluant l'architecture, les prérequis, la structure des dossiers, et les instructions de lancement détaillées, le tout formaté en Markdown.
Markdown

# 🛵 Projet Simulation UberEats : Comparaison Redis vs. MongoDB

Ce projet vise à simuler la logique de gestion des courses (dispatch) d'une plateforme de livraison (type UberEats) en utilisant deux architectures de bases de données distribuées différentes : **Redis (Pub/Sub)** et **MongoDB (Change Streams)**.

---

## 1. Architecture du Projet

Le cœur du projet repose sur le concept de **Producteur/Consommateur** et de **Compétition en temps réel** entre les Livreurs.

### 1.1 Composants Communs

| Composant | Rôle | Description |
| :--- | :--- | :--- |
| **Manager** | **Producteur** | Simule la plateforme. Publie l'annonce d'une nouvelle course et sélectionne le Livreur le plus rapide. |
| **Livreur** | **Consommateur/Compétiteur** | Simule l'application du Livreur. Reçoit l'annonce, manifeste son intérêt, et accepte la course s'il est sélectionné. |
| **`denormalisation.json`** | **Source de Données** | Fichier unique contenant les données de commandes (restaurants, clients, etc.) utilisées pour simuler les annonces. |

---

### 1.2 Architecture Redis (Messagerie Événementielle)

Cette architecture utilise **Redis** comme un courtier de messages et un magasin de données temporaire.

* **Communication :** Utilisation du modèle **Pub/Sub** pour la diffusion instantanée des annonces aux Livreurs.
* **Sélection :** Le Manager attend pendant un temps défini (5 secondes) que les Livreurs enregistrent leur intérêt via la commande `HSET`. La sélection est basée sur le **timestamp le plus précoce**.
* **État :** Stockage de l'état temporaire (`ubereats:course:active`) et des intérêts (`ubereats:interet:Oxxxx`) via des commandes Redis classiques.

---

### 1.3 Architecture MongoDB (Flux de Changement Persistant)

Cette architecture utilise **MongoDB** (lancé en Replica Set) comme base de données principale et exploite ses **Change Streams** pour la communication en temps réel.

* **Communication :** Le Manager insère un document. Les Livreurs surveillent la collection (`annonces`) via un **Change Stream** et reçoivent l'événement d'insertion en temps réel.
* **Sélection :** La sélection est gérée par une **mise à jour atomique conditionnelle** (`$set` avec une condition sur le statut). Le premier Livreur à réussir à changer le statut du document de `ANNONCE_PUBLIEE` à `LIVREUR_SELECTIONNE` gagne.
* **État :** L'état de la course est persistant et contenu intégralement dans un **unique document JSON** dans la collection `annonces`.

---

## 2. Prérequis Techniques

Pour exécuter ce projet, vous devez disposer des éléments suivants :

* **Python 3.x** (avec des environnements virtuels `myredis` et `mymongo`)
* **Redis Server** (version 5.0 ou supérieure recommandée)
* **MongoDB Server** (version 4.0 ou supérieure, **doit être lancé en Replica Set**).
* **Librairies Python :** `redis`, `pymongo`, `dnspython` (à installer dans les environnements virtuels respectifs).

---

## 3. Structure des Dossiers

projet_uber
├── avec-mongo/
│   ├── denormalisation.json     # Données sources
│   ├── manager_mongo.py         # Manager utilisant MongoDB
│   └── livreur_mongo.py         # Livreur utilisant MongoDB
├── avec-redis/
│   ├── denormalisation.json     # Données sources
│   ├── manager_ubereats.py      # Manager utilisant Redis
│   └── livreur_ubereats.py      # Livreur utilisant Redis
└── denormalisation.py           # Script initial de préparation des données


MONGODB : 

###  PREMIER TERMINAL : 

```bash
mongod --port 27017 --dbpath /home/narz/BUT3/Base_De_Donnees/projet/projet-uber/avec-mongo/data/db --replSet rs0

### DEUXIEME TERMINAL : 
```bash
cd BUT3/Base_De_Donnees/projet/projet-uber/avec-mongo
source mymongo/bin/activate
python livreur_mongo.py

### TROISIEME TERMINAL : 
```bash 
cd BUT3/Base_De_Donnees/projet/projet-uber/avec-mongo
source mymongo/bin/activate
python manager_mongo.py

###  TERMINAL : 
```bash
mongosh
use uber_mongo
db.annonces.find().pretty()


### REDIS :

### SERVEUR TERMINAL : 

```bash
cd redis/redis-stable/src
./redis-server

### CLIENT TERMINAL : 

```bash
cd ~/redis/redis-stable/src
./redis-cli

--- Apres ---

```bash 
GET ubereats:course:active

### PREMIER TERMINAL :

```bash
cd BUT3/Base_De_Donnees/projet/projet-uber/avec-redis
source myredis/bin/activate 
python livreur_redis.py

### DEUXIEME TERMINAL : 

```bash
cd BUT3/Base_De_Donnees/projet/projet-uber/avec-redis
source myredis/bin/activate 
python manager_redis.py




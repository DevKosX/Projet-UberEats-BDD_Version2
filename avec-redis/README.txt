
Projet Uber Eats - CSV & scripts
Contenu:
- csv/RESTAURANTS.csv
- csv/PLATS.csv
- csv/CLIENTS.csv
- csv/COMMANDES.csv
- csv/DETAILS_COMMANDES.csv
- scripts/denormalisation_ubereats.py
- scripts/manager_ubereats.py
- scripts/livreur_ubereats.py

Instructions rapides:
1) Installer dépendances: pip install pandas redis
2) Placer Redis en route (si vous voulez tester l'insertion dans Redis)
3) Lancer: python scripts/denormalisation_ubereats.py
4) Lancer un ou plusieurs livreurs: python scripts/livreur_ubereats.py --id L1 --accept_prob 0.8
5) Lancer le manager (publie une annonce à partir d'une commande cachée): python scripts/manager_ubereats.py --from_cached --window 8

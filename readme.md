### Projet Agile 

## Planning Poker 

Dans le cadre de notre projet en TD Agile, nous devions concevoir une application de planning Poker.

Le Planning Poker est une méthode de planification agile utilisée pour estimer l'effort ou la complexité des tâches dans un projet (souvent en développement logiciel). Elle est collaborative, ludique et vise à obtenir un consensus au sein de l'équipe. 

Liste des outils et technologies employés :
- Flask (Python)
- HTML, CSS 
- Javascript (côté client)
- SocketIO (établir communication en temps réel entre un client et un serveur)
- Reste des bibliothèques dans "requierements.txt"

### Etapes pour lancer l'application :

1. Cloner le dépôt :

```bash
git clone https://github.com/nic0119/projet_agile.git
cd projet_agile
```

2. Créer un environnement virtuel et l'activer :

```bash
python3 -m venv venv
source venv/bin/activate
```

3. Installer les dépendances :
   
```bash
pip install -r requirements.txt
```

4. Lancer l'application :

```bash
python app.py 
```

### Consulter la documentation :

1. Javascript

```bash
projet_agile/Documentation/Javascript/out/index.html -> Ouvrir avec un navigateur
```

2. Python

```bash
projet_agile/Documentation/Python/html/index.html -> Ouvrir avec un navigateur
```

### Réaliser tests unitaires : 

1. Javascript (avec jest)

```bash
npm install
npm run test
```

2. Python (avec PyTest)

```bash
pip install pytest
pytest -v test/test_routes.py
```

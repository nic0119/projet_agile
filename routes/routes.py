from flask import render_template, request, redirect, url_for, session, jsonify
from flask_socketio import join_room, emit
import os
import sys
from extensions import app, socketio, games, db
from models.user import User
import random
import json


# Fonction pour générer un ID de partie unique
def generate_unique_game_id():
    while True:
        game_id = str(random.randint(1000, 9999))
        if game_id not in games:
            return game_id



## Login et Signup 

@app.route("/", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        pseudo = request.form.get("pseudo")
        if pseudo:
            existing_user = User.query.filter_by(pseudo=pseudo).first()
            if existing_user:
                error = "Ce pseudo est déjà pris. Choisissez un autre pseudo."
                return render_template("signup.html", error=error)
            new_user = User(pseudo=pseudo)
            db.session.add(new_user)
            db.session.commit()
            session["pseudo"] = pseudo
            return redirect(url_for("dashboard"))
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pseudo = request.form.get("pseudo")
        user = User.query.filter_by(pseudo=pseudo).first()
        if user:
            session["pseudo"] = pseudo
            return redirect(url_for("dashboard"))
        else:
            error = "Pseudo incorrect. Veuillez vous inscrire."
            return render_template("login.html", error=error)
    return render_template("login.html")

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "pseudo" not in session:
        return redirect(url_for("signup"))
    
    if request.method == "POST":
        if "create_game" in request.form:
            game_mode = request.form["game_mode"]
            number_player = request.form["number_player"]
            game_id = generate_unique_game_id()
            games[game_id] = {
                "mode": game_mode,
                "players": [session["pseudo"]],
                "number_player": number_player,
                "host": session["pseudo"],
                "status": "waiting",
                "problems": [],
                "resultats": [],
                "votes": {}
            }

            session["game_id"] = game_id
            route = "game_room"

            if route:
                return redirect(url_for(route, game_id=game_id))

        elif "join_game" in request.form:
            game_id = request.form["game_id"]
    
            if game_id in games:
                current_players = len(games[game_id]['players'])
                max_players = int(games[game_id]["number_player"])

                if current_players >= max_players:
                    error = "La partie est déjà complète. Impossible de rejoindre."
                    return render_template("dashboard.html", pseudo=session["pseudo"], error=error)
                else:                
                    if session["pseudo"] not in games[game_id]["players"]:
                        games[game_id]["players"].append(session["pseudo"])

                    session["game_id"] = game_id

                    # Récupérer le mode de jeu de la partie
                    game_mode = games[game_id]["mode"]
                    route = "game_room"

                    if route:
                        return redirect(url_for(route, game_id=game_id))
            else:
                error = "L'ID de partie n'existe pas."
                return render_template("dashboard.html", pseudo=session["pseudo"], error=error)
        
    return render_template("dashboard.html", pseudo=session["pseudo"])



## - Game Room - ##

@socketio.on("start_game")
def handle_start_game(data):
    game_id = data["game_id"]

    if session["pseudo"] == games[game_id]["host"]: 
        games[game_id]["status"] = "active"
        emit("start_game", {"game_id": game_id}, room=game_id)


@socketio.on("select_problem")
def handle_select_problem(data):
    game_id = data["game_id"]
    problem = data["problem"]

    games[game_id]["current_problem"] = problem 

    # Diffuse pour tous les joueurs
    emit("problem_selected", {"problem": problem}, room=game_id) 

@socketio.on("start_vote")
def handle_start_vote(data):
    game_id = data["game_id"]
    problem = data["problem"]
    
    games[game_id]["votes"][problem] = {} # Initialiser les votes pour le problème
    
    emit("vote_started", {"problem": problem}, room=game_id) # Notifier tous les joueurs pour démarrer le vote

@socketio.on("cast_vote")
def handle_cast_vote(data):
    game_id = data["game_id"]
    problem = data["problem"]
    vote = data["vote"]
    pseudo = data["pseudo"]

    # Vérifie si le vote pour ce problème est déjà conclu
    if problem in games[game_id].get("concluded_votes", {}):
        return  

    # Enregistre le vote pour le joueur et le problème
    games[game_id]["votes"][problem][pseudo] = vote

    # Notifie tous les joueurs des votes en cours 
    emit("update_votes", {"problem": problem, "votes": games[game_id]["votes"][problem]}, room=game_id)


@socketio.on("join_room")
def handle_join(data):
    game_id = data["game_id"]
    pseudo = data["pseudo"]

    if game_id not in games:
        emit("error", {"message": "La partie n'existe pas."}, room=request.sid)
        return
    
    # Vérification nombre joueurs dans la partie
    current_players = len(games[game_id]["players"])
    max_players = int(games[game_id]["number_player"])

    if current_players >= max_players + 1:
        emit("error", {"message": "La partie est déjà complète."}, room=request.sid)
        return

    if pseudo not in games[game_id]["players"]:
        games[game_id]["players"].append(pseudo)
    
    join_room(game_id)

    # Prépare les données pour la partie
    game_data = {
        "status": games[game_id]["status"],
        "current_problem": games[game_id].get("current_problem", None),
        "problems": games[game_id]["problems"],
        "votes": games[game_id]["votes"],
        "concluded_votes": games[game_id].get("concluded_votes", {})
    }

    # Envoie l'état actuel de la partie et les problèmes/votes au client
    emit("update_players", {"players": games[game_id]["players"], "host": games[game_id]["host"]}, room=game_id)
    emit("game_state", game_data, room=request.sid)


@socketio.on("add_problem")
def handle_add_problem(data):
    game_id = data["game_id"]
    problem = data["problem"]
    games[game_id]["problems"].append(problem)
    games[game_id]["votes"][problem] = {}
    emit("new_problem", {"problem": problem}, room=game_id)


@socketio.on("end_game")
def handle_end_game(data):
    game_id = data["game_id"]
    pseudo = session.get("pseudo")

    if game_id not in games:
        emit("error", {"message": "La partie n'existe pas ou a déjà été terminée."}, room=request.sid)
        return

    if games[game_id]["host"] == pseudo:
        emit("game_ended", {"message": "La partie a été terminée par l'hôte."}, room=game_id)
        del games[game_id]





@app.route("/game_room/<game_id>")
def game_room(game_id):
    
    if game_id not in games or session["pseudo"] not in games[game_id]["players"]:
        return redirect(url_for("dashboard"))

    players = games[game_id]["players"]
    mode = games[game_id]["mode"]

    mode_labels = {
        "strict": "Strict (Unanimité)",
        "moyenne": "Moyenne",
        "mediane": "Médiane",
        "majorite_absolue": "Majorité absolue",
        "majorite_relative": "Majorité relative",
    }
    resultats = games[game_id].get("resultats", {})

    return render_template("game_room.html", 
                           game_id=game_id, 
                           pseudo=session["pseudo"], 
                           host=games[game_id]["host"], 
                           mode=mode, 
                           mode_label=mode_labels[mode], 
                           players=players,
                           results=resultats)


@socketio.on("devoiler_vote")
def devoiler_vote(data):
    game_id = data["game_id"]
    problem = data["problem"]
    compteur = data["compteur"]

    if game_id not in games or problem not in games[game_id]["votes"]:
        emit("error", {"message": "Partie ou problème invalide."}, room=request.sid)
        return

    votes = games[game_id]["votes"].get(problem, {})
    players = games[game_id]["players"]
    mode = games[game_id]["mode"]


    # Si tous les votes sont "café"
    if all(vote == "cafe" for vote in votes.values()) and len(votes) == len(players):
        print("Tous les joueurs ont voté café, sauvegarde automatique...", flush=True)
        
        # Sauvegarder automatiquement la partie
        handle_save_resultats({"game_id": game_id})

        emit("unanimous_vote", {
            "problem": problem,
            "result": "cafe",
            "votes": votes
        }, room=game_id)

        return

    if "results" not in games[game_id]:
        games[game_id]["results"] = {} 

    if compteur == 1 or mode == "strict":
        if len(set(votes.values())) == 1 and len(votes) == len(players):
            unanimous_vote = list(votes.values())[0]
            games[game_id].setdefault("concluded_votes", {})[problem] = unanimous_vote
            games[game_id].setdefault("results", {})[problem] = unanimous_vote
            socketio.emit("unanimous_vote", {
                "problem": problem,
                "result": unanimous_vote,
                "votes": votes
            }, room=game_id)

            socketio.emit("refresh_ui", room=game_id)
        else:
            socketio.emit("revote", {
                "problem": problem,
                "message": f"Re votez pour le problème {problem}",
                "votes": votes
            }, room=game_id)
    else:
        if mode == "moyenne":
            devoiler_vote_moyenne(game_id, problem, votes)
        elif mode == "mediane":
            devoiler_vote_mediane(game_id, problem, votes)
        elif mode == "majorite_absolue":
            devoiler_vote_majorite_absolue(game_id, problem, votes)
        elif mode == "majorite_relative":
            devoiler_vote_majorite_relative(game_id, problem, votes)


def devoiler_vote_moyenne(game_id, problem, votes):

    valid_votes = [vote for vote in votes.values() if isinstance(vote, (int, float))]
    
    if valid_votes:
        moyenne_vote = sum(valid_votes) / len(valid_votes)
        games[game_id].setdefault("concluded_votes", {})[problem] = moyenne_vote
        games[game_id].setdefault("results", {})[problem] = moyenne_vote
        socketio.emit("average_vote", {
            "problem": problem,
            "average_result": moyenne_vote,
            "votes": votes
        }, room=game_id)

        socketio.emit("refresh_ui", room=game_id)
    else:
        socketio.emit("error", {
            "problem": problem,
            "message": "Aucun vote valide pour calculer la moyenne."
        }, room=game_id)


def devoiler_vote_mediane(game_id, problem, votes):

    valid_votes = [vote for vote in votes.values() if isinstance(vote, (int, float))]
    if valid_votes:
        sorted_votes = sorted(valid_votes)
        n = len(sorted_votes)
        mediane_vote = (sorted_votes[n // 2] if n % 2 == 1 else
                        (sorted_votes[n // 2 - 1] + sorted_votes[n // 2]) / 2)
        games[game_id].setdefault("concluded_votes", {})[problem] = mediane_vote
        games[game_id].setdefault("results", {})[problem] = mediane_vote
        socketio.emit("median_vote", {
            "problem": problem,
            "median_result": mediane_vote,
            "votes": votes
        }, room=game_id)

        socketio.emit("refresh_ui", room=game_id)

    else:
        socketio.emit("error", {
            "problem": problem,
            "message": "Aucun vote valide pour calculer la médiane."
        }, room=game_id)

def devoiler_vote_majorite_absolue(game_id, problem, votes):
    if votes:
        vote_counts = {vote: list(votes.values()).count(vote) for vote in set(votes.values())}
        majorite_vote = max(vote_counts, key=vote_counts.get)
        
        if vote_counts[majorite_vote] > len(votes) / 2:
            games[game_id].setdefault("concluded_votes", {})[problem] = majorite_vote
            games[game_id].setdefault("results", {})[problem] = majorite_vote
            socketio.emit("majority_vote", {
                "problem": problem,
                "majority_result": majorite_vote,
                "votes": votes
            }, room=game_id)

            socketio.emit("refresh_ui", room=game_id)
        else:
            socketio.emit("revote", {
                "problem": problem,
                "message": "Pas de majorité absolue. Re votez.",
                "votes": votes
            }, room=game_id)


def devoiler_vote_majorite_relative(game_id, problem, votes):
    if votes:
        vote_counts = {vote: list(votes.values()).count(vote) for vote in set(votes.values())}
        max_count = max(vote_counts.values())
        vote_max_nb = [vote for vote, count in vote_counts.items() if count == max_count]

        if len(vote_max_nb) == 1:
            majorite_relative_vote = vote_max_nb[0]
            games[game_id].setdefault("concluded_votes", {})[problem] = majorite_relative_vote
            games[game_id].setdefault("results", {})[problem] = majorite_relative_vote
            socketio.emit("relative_majority_vote", {
                "problem": problem,
                "majority_result": majorite_relative_vote,
                "votes": votes
            }, room=game_id)

            socketio.emit("refresh_ui", room=game_id)
        else:
            socketio.emit("revote", {
                "problem": problem,
                "message": "Pas de majorité relative claire. Re votez.",
                "votes": votes
            }, room=game_id)




#JSON 


@socketio.on("upload_backlog")
def handle_upload_backlog(data):
    file_data = data["file_data"]  #Contenu du JSON 
    try:
        #Charger le JSON 
        backlog = json.loads(file_data)

        game_id = backlog.get("partie_id")
        mode_de_jeu = backlog.get("mode_de_jeu")
        resultats = backlog.get("resultats", [])
        number_player = backlog.get("number_player")

        games[game_id] = {
            "mode": mode_de_jeu,
            "players": [session["pseudo"]],
            "number_player": number_player,
            "host": session["pseudo"],
            "status": "waiting",
            "problems": [entry["probleme"] for entry in resultats],
            "difficulte": {entry["probleme"]: entry["difficulte"] for entry in resultats},  # Stocke les difficultés
            "votes": {},
            "results": resultats
        }
        for entry in resultats:
            games[game_id]["votes"][entry["probleme"]] = {}
    
        emit("redirect_to_game_room", {"game_id": game_id})
    except Exception as e:
        emit("error", {"message": f"Erreur lors de l'import du JSON : {str(e)}"})


@socketio.on("save_resultats")
def handle_save_resultats(data):
    game_id = data["game_id"]

    if game_id not in games:
        emit("error", {"message": "La partie n'existe pas."}, room=request.sid)
        return

    resultats = games[game_id].get("resultats", {})
    problemes = games[game_id]["problems"]
    mode_de_jeu = games[game_id]["mode"] 
    max_player = games[game_id]["number_player"]
    resultats = games[game_id]["results"]
    # Inclure le mode de jeu et les résultats
    fichier = {
        "partie_id": game_id,
        "mode_de_jeu": mode_de_jeu,
        "number_player": max_player,
        "resultats": [
            {"probleme": probleme, "difficulte": resultats.get(probleme)}
            for probleme in problemes
        ]
    }
    # Enregistre les résultats dans un fichier JSON
    file_name = f"{game_id}_resultats.json"
    with open(file_name, "w") as file:
        json.dump(fichier, file, indent=4)

    emit("resultats_saved", {
        "message": "Tous les joueurs ont voté café. Fin de la partie !",
        "file_name": file_name
    }, room=game_id)

    del games[game_id]
    return



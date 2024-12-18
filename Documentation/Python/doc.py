"""
@file routes.py
@brief Ce fichier gère les routes principales de l'application Flask et les événements Socket.IO pour une application de planning poker.

@details
- Gère les fonctionnalités d'inscription, de connexion et de tableau de bord.
- Permet de créer et rejoindre des parties de planning poker.
- Gère les interactions en temps réel entre les joueurs avec Socket.IO.
"""

from flask import render_template, request, redirect, url_for, session, jsonify
from flask_socketio import join_room, emit
import os
import sys
from extensions import app, socketio, games, db
from models.user import User
import random
import json





def generate_unique_game_id():
    """
    @brief Génère un ID de partie unique.
    @return Un identifiant aléatoire qui n'est pas déjà utilisé.
    """
    while True:
        game_id = str(random.randint(1000, 9999))
        if game_id not in games:
            return game_id





@app.route("/", methods=["GET", "POST"])
def signup():
    """
    @brief Gère l'inscription des utilisateurs.
    @details Affiche un formulaire pour s'inscrire ou ajoute un nouvel utilisateur si le pseudo est unique.
    @return Page d'inscription ou redirection vers le tableau de bord.
    """
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
    """
    @brief Gère la connexion des utilisateurs.
    @details Vérifie si l'utilisateur existe et enregistre son pseudo dans la session.
    @return Page de connexion ou redirection vers le tableau de bord.
    """
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

    """
    @brief Page principale après connexion.
    @details Permet de créer une partie ou de rejoindre une partie existante.
    @return Page du tableau de bord.
    """
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
            return redirect(url_for("game_room", game_id=game_id))
        elif "join_game" in request.form:
            game_id = request.form["game_id"]
            if game_id in games:
                if len(games[game_id]['players']) < int(games[game_id]["number_player"]):
                    if session["pseudo"] not in games[game_id]["players"]:
                        games[game_id]["players"].append(session["pseudo"])
                    session["game_id"] = game_id
                    return redirect(url_for("game_room", game_id=game_id))
                else:
                    error = "La partie est déjà complète."
                    return render_template("dashboard.html", pseudo=session["pseudo"], error=error)
            else:
                error = "L'ID de partie n'existe pas."
                return render_template("dashboard.html", pseudo=session["pseudo"], error=error)
    return render_template("dashboard.html", pseudo=session["pseudo"])


@socketio.on("start_game")
def handle_start_game(data):

    """
    @brief Démarre une partie.
    @details Change l'état de la partie à "active" et notifie tous les joueurs.
    @param data Contient l'ID de la partie.
    """
    game_id = data["game_id"]
    if session["pseudo"] == games[game_id]["host"]:
        games[game_id]["status"] = "active"
        emit("start_game", {"game_id": game_id}, room=game_id)

@socketio.on("select_problem")
def handle_select_problem(data):
    
    """
    @brief Sélectionne un problème pour le vote.
    @param data Contient l'ID de la partie et le problème sélectionné.
    """
    game_id = data["game_id"]
    problem = data["problem"]
    games[game_id]["current_problem"] = problem
    emit("problem_selected", {"problem": problem}, room=game_id)


@socketio.on("cast_vote")
def handle_cast_vote(data):
    """
    @brief Enregistre les votes des joueurs.
    @param data Contient l'ID de la partie, le problème, et les votes des joueurs.
    """
    game_id = data["game_id"]
    problem = data["problem"]
    vote = data["vote"]
    pseudo = data["pseudo"]
    games[game_id]["votes"][problem][pseudo] = vote
    emit("update_votes", {"problem": problem, "votes": games[game_id]["votes"][problem]}, room=game_id)

# (Autres fonctions à documenter de la même manière.)

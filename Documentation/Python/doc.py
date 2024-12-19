"""
@file routes.py
@brief Ce fichier gère les routes principales de l'application Flask et les événements Socket.IO côté serveur.

@details
- Gère les fonctionnalités d'inscription, de connexion et de tableau de bord.
- Permet de créer et rejoindre des parties de planning poker.
- Gère les interactions en temps réel entre les joueurs avec Socket.IO dans la partie.

@mainpage Documentation de l'application Planning Poker sur Flask

@section overview Vue d'ensemble

Cette application Flask permet de gérer des parties de planning poker avec des fonctionnalités en temps réel.
Les fonctionnalités incluent :
- Gestion des utilisateurs (inscription, connexion).
- Création et gestion des parties (mode de jeu, votes, problèmes).
- Communication en temps réel avec Socket.IO.
- Sauvegarder et import de backlog (Json)

"""

# === Gestion des sessions et des utilisateurs ===

def signup():
    """
    @brief Gère l'inscription des utilisateurs.
    @details Affiche un formulaire pour s'inscrire ou ajoute un nouvel utilisateur si le pseudo est unique.
    @return Page d'inscription ou redirection vers le tableau de bord en cas de succès.
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



def login():
    """
    @brief Gère la connexion des utilisateurs.
    @details Vérifie si l'utilisateur existe et enregistre son pseudo dans la session.
    @return Page de connexion ou redirection vers le tableau de bord en cas de succès.
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



def dashboard():
    """
    @brief Page principale après connexion.
    @details Permet de créer une partie, de rejoindre une partie existante ou charger backlog.
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




# === Gestion des parties ===


def generate_unique_game_id():
    """
    @brief Génère un ID de partie unique.
    @return Un identifiant aléatoire qui n'est pas déjà utilisé.
    """
    while True:
        game_id = str(random.randint(1000, 9999))
        if game_id not in games:
            return game_id


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


def handle_select_problem(data):  
    """
    @brief Sélectionne un problème pour le vote.
    @param data Contient l'ID de la partie et le problème sélectionné.
    """
    game_id = data["game_id"]
    problem = data["problem"]
    games[game_id]["current_problem"] = problem
    emit("problem_selected", {"problem": problem}, room=game_id)



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


def handle_join(data):
     """
    @brief Gère l'événement de connexion d'un joueur à une partie.

    @param data Dictionnaire contenant :
        - "game_id" (str) : l'identifiant de la partie.
        - "pseudo" (str) : le pseudo du joueur.

    @details
    - Vérifie l'existence et la disponibilité de la partie.
    - Ajoute le joueur si les conditions sont remplies.
    - Met à jour les joueurs et l'état de la partie.

    @emit
    - "error" : en cas d'erreur.
    - "update_players" : mise à jour de la liste des joueurs.
    - "game_state" : état actuel de la partie.

    @return None
    """
     
    game_id = data["game_id"]
    pseudo = data["pseudo"]

    if game_id not in games:
        emit("error", {"message": "La partie n'existe pas."}, room=request.sid)
        return

    current_players = len(games[game_id]["players"])
    max_players = int(games[game_id]["number_player"])

    if current_players >= max_players + 1:
        emit("error", {"message": "La partie est déjà complète."}, room=request.sid)
        return

    if pseudo not in games[game_id]["players"]:
        games[game_id]["players"].append(pseudo)
    
    join_room(game_id)

    game_data = {
        "status": games[game_id]["status"],
        "current_problem": games[game_id].get("current_problem", None),
        "problems": games[game_id]["problems"],
        "votes": games[game_id]["votes"],
        "concluded_votes": games[game_id].get("concluded_votes", {})
    }

    emit("update_players", {"players": games[game_id]["players"], "host": games[game_id]["host"]}, room=game_id)
    emit("game_state", game_data, room=request.sid)



def handle_add_problem(data):
    """
    @brief Ajoute un nouveau problème à la partie spécifiée.

    @param data Dictionnaire contenant :
        - "game_id" (str) : l'identifiant de la partie.
        - "problem" (str) : la description du problème à ajouter.

    @details
    - Ajoute le problème à la liste des problèmes de la partie.
    - Initialise les votes pour ce problème.
    - Informe tous les joueurs de la partie via l'événement "new_problem".

    @emit
    - "new_problem" : notifie les joueurs qu'un nouveau problème a été ajouté.

    @return None
    """
    game_id = data["game_id"]
    problem = data["problem"]
    games[game_id]["problems"].append(problem)
    games[game_id]["votes"][problem] = {}
    emit("new_problem", {"problem": problem}, room=game_id)


def handle_end_game(data):
    """
    @brief Termine une partie existante.

    @param data Dictionnaire contenant :
        - "game_id" (str) : l'identifiant de la partie.

    @details
    - Vérifie si la partie existe.
    - Vérifie si l'utilisateur est l'hôte de la partie.
    - Notifie tous les joueurs que la partie est terminée.
    - Supprime la partie des données si elle est terminée par l'hôte.

    @emit
    - "error" : en cas d'échec (partie inexistante ou déjà terminée).
    - "game_ended" : notifie tous les joueurs que la partie est terminée.

    @return None
    """
    game_id = data["game_id"]
    pseudo = session.get("pseudo")

    if game_id not in games:
        emit("error", {"message": "La partie n'existe pas ou a déjà été terminée."}, room=request.sid)
        return
    
    if games[game_id]["host"] == pseudo:
        emit("game_ended", {"message": "La partie a été terminée par l'hôte."}, room=game_id)
        del games[game_id]


def game_room(game_id):
    """
    @brief Gère l'accès à une salle de jeu spécifique.

    @param game_id Identifiant unique de la partie.

    @details
    - Redirige vers le tableau de bord si la partie n'existe pas ou si l'utilisateur n'en fait pas partie.
    - Récupère les informations sur les joueurs, le mode de jeu, et les résultats.
    - Rend la page HTML associée avec les données nécessaires.

    @return Une page HTML ou une redirection vers le tableau de bord.
    """
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


/**
 * \subsection Gestion des votes
 */


def devoiler_vote(data):
    """
    @brief Gère les votes pour un problème spécifique dans une partie.

    @param data Dictionnaire contenant :
        - "game_id" (str) : l'identifiant de la partie.
        - "problem" (str) : le problème pour lequel les votes sont dévoilés.
        - "compteur" (int) : compteur pour savoir le numéro du tour.

    @details
    - Vérifie que la partie et le problème existent.
    - Traite le mode de jeu Strict et les votes unanimes des premiers tours
    - Si tous les joueurs ont voté "cafe", la partie est automatiquement sauvegardée.
    - Traite les votes en fonction du mode de jeu (ég. stricte, moyenne, médiane, etc.).
    - Notifie les joueurs du résultat ou demande un nouveau vote si nécessaire.

    @emit
    - "error" : en cas de problème avec la partie ou le problème.
    - "unanimous_vote" : si tous les joueurs ont voté la même chose.
    - "revote" : demande aux joueurs de revoter si pas de résultat possible
    - "refresh_ui" : met à jour l'interface utilisateur.
    """
    game_id = data["game_id"]
    problem = data["problem"]
    compteur = data["compteur"]

    if game_id not in games or problem not in games[game_id]["votes"]:
        emit("error", {"message": "Partie ou problème invalide."}, room=request.sid)
        return

    votes = games[game_id]["votes"].get(problem, {})
    players = games[game_id]["players"]
    mode = games[game_id]["mode"]

    if all(vote == "cafe" for vote in votes.values()) and len(votes) == len(players):
        print("Tous les joueurs ont voté café, sauvegarde automatique...", flush=True)
        
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





def devoiler_vote_mediane(game_id, problem, votes):
    """
    @brief Calcule la médiane des votes.

    @param game_id (str) : L'identifiant de la partie.
    @param problem (str) : Le problème pour lequel la médiane des votes est calculée.
    @param votes (dict) : Un dictionnaire des votes des joueurs.

    @details
    - Filtre les votes pour ne garder que les valeurs numériques en ignorant les cartes ? et café.
    - Calcule la médiane et l'enregistre dans les résultats de la partie.
    - Émet l'événement "median_vote" avec les résultats.
    - En cas d'absence de votes valides, émet un message d'erreur.

    @emit
    - "median_vote" : Contient le résultat de la médiane.
    - "error" : En cas d'absence de votes valides.

    @return None
    """
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
    """
    @brief Calcule le vote majoritaire absolu.

    @param game_id (str) : L'identifiant de la partie.
    @param problem (str) : Le problème pour lequel la majorité absolue est calculée.
    @param votes (dict) : Un dictionnaire des votes des joueurs.

    @details
    - Compte les occurrences de chaque vote.
    - Vérifie si un vote obtient plus de 50% des votes totaux.
    - Si oui, enregistre et émet le résultat. Sinon, demande un nouveau vote.

    @emit
    - "majority_vote" : Contient le résultat de la majorité absolue.
    - "revote" : Demande un nouveau vote si aucune majorité absolue.

    """

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
    """
    @brief Calcule le vote majoritaire relatif.

    @param game_id (str) : L'identifiant de la partie.
    @param problem (str) : Le problème pour lequel la majorité relative est calculée.
    @param votes (dict) : Un dictionnaire des votes des joueurs.

    @details
    - Compte les occurrences de chaque vote.
    - Si un vote a le plus grand nombre d'occurrences unique, enregistre et émet le résultat.
    - Sinon, demande un nouveau vote en cas d'égalité.

    @emit
    - "relative_majority_vote" : Contient le résultat de la majorité relative.
    - "revote" : Demande un nouveau vote si aucune majorité claire n'est atteinte.
    """
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


/**
 * \section Backlog (Json)
 */

/**
 * \subsection Charger une partie
 */


def handle_upload_backlog(data):
    """
    @brief Gère l'import d'un backlog au format JSON et initialise les données pour la partie

    @param data (dict) : Contient le contenu JSON envoyé par le client "file_data" (str).

    @details
    - Charge le JSON reçu pour extraire les informations de la partie (mode de jeu, joueurs, résultats, etc.).
    - Initialise les votes et les problèmes associés dans la structure de jeu.
    - Redirige le joueur vers la salle de jeu si l'import est réussi.
    - Émet un message d'erreur en cas d'échec du traitement JSON.

    @emit
    - "redirect_to_game_room" : Redirige le joueur vers la salle de jeu avec l'identifiant de la partie.
    - "error" : En cas d'échec lors du traitement du fichier JSON.
    """
    file_data = data["file_data"]  
    try:
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
        # Rediriger vers la salle de jeu
        emit("redirect_to_game_room", {"game_id": game_id})
    except Exception as e:
        emit("error", {"message": f"Erreur lors de l'import du JSON : {str(e)}"})


/**
 * \subsection Sauvegarder une partie
 */


def handle_save_resultats(data):
    """
    @brief Enregistre les résultats d'une partie dans un fichier JSON.

    @param data (dict) : game_id" (str) : L'identifiant de la partie.

    @details
    - Vérifie que la partie existe.
    - Extrait les résultats, les problèmes et le mode de jeu.
    - Sauvegarde ces données dans un fichier JSON nommé "<game_id>_resultats.json".
    - Supprime la partie de la mémoire après sauvegarde.

    @emit
    - "resultats_saved" : Contient le nom du fichier sauvegardé et un message de confirmation.
    - "error" : Si la partie n'existe pas.

    """
    game_id = data["game_id"]

    if game_id not in games:
        emit("error", {"message": "La partie n'existe pas."}, room=request.sid)
        return

    resultats = games[game_id].get("resultats", {})
    problemes = games[game_id]["problems"]
    mode_de_jeu = games[game_id]["mode"] 
    max_player = games[game_id]["number_player"]
    resultats = games[game_id]["results"]

    fichier = {
        "partie_id": game_id,
        "mode_de_jeu": mode_de_jeu,
        "number_player": max_player,
        "resultats": [
            {"probleme": probleme, "difficulte": resultats.get(probleme)}
            for probleme in problemes
        ]
    }

    file_name = f"{game_id}_resultats.json"
    with open(file_name, "w") as file:
        json.dump(fichier, file, indent=4)

    emit("resultats_saved", {
        "message": "Les résultats ont été sauvegardés avec succès.",
        "file_name": file_name
    }, room=game_id)

    del games[game_id]
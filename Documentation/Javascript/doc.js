/**
 * @fileoverview 
 * 
 * Script principal pour la gestion de la salle de jeu du Planning Poker.
 * Il gère les interactions entre le client et le serveur via Socket.IO, 
 * l'affichage des joueurs, des problèmes et des votes en temps réel.
 *
 * @author Nicolas Tran et Hubert Geoffray
 */


// ==================== Variables Globales ==================== //

/** Connexion au serveur Socket.IO */
const socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);

/** @type {string} - ID de la partie actuelle */
const gameId = "{{ game_id }}";

/** @type {string} - Pseudo du joueur actuel */
const pseudo = "{{ pseudo }}";

/** @type {string} - Problème actuellement sélectionné pour le vote */
let currentProblem = "";

/** @type {number} - Compteur de tours pour le dévoilement des votes */
let compteur = 1;



// ==================== Fonctions  ==================== //

/**
 * @function addProblemToUI
 * @description Ajoute un problème à l'interface utilisateur dans la liste des problèmes disponibles.
 * 
 * @param {string} problem - Le nom du problème à ajouter à la liste.
 * 
 * @details
 * - Crée un nouvel élément `<li>` contenant le problème et ses contrôles associés.
 * - Si l'utilisateur est l'hôte, un bouton "Voter pour ce problème" est ajouté.
 * - Initialise l'affichage du résultat avec "En attente".
 */
function addProblemToUI(problem) {
    const problemList = document.getElementById("problems-list");
    const li = document.createElement("li");

    // Conteneur principal en flexbox
    const problemContainer = document.createElement("div");
    problemContainer.style.display = "flex";
    problemContainer.style.justifyContent = "space-between";
    problemContainer.style.alignItems = "center";
    problemContainer.style.padding = "10px 0";
    problemContainer.style.borderBottom = "1px solid #ddd";

    // Partie gauche : Nom du problème + Bouton voter
    const leftContainer = document.createElement("div");
    leftContainer.style.display = "flex";
    leftContainer.style.alignItems = "center";

    // Nom du problème
    const problemName = document.createElement("span");
    problemName.textContent = problem;
    problemName.style.marginRight = "10px";

    // Bouton "Voter pour ce problème" uniquement pour l'hôte
    // {% if pseudo == host %}
    // const voteButton = document.createElement("button");
    // voteButton.textContent = "Voter pour ce problème";
    // voteButton.className = "btn btn-success"; // Style Bootstrap
    // voteButton.onclick = () => selectProblem(problem);
    // voteButton.style.marginRight = "10px";
    // leftContainer.appendChild(voteButton);
    // {% endif %}

    leftContainer.appendChild(problemName);

    // Partie droite : Résultat aligné à droite
    const resultSpan = document.createElement("span");
    resultSpan.id = `result-${encodeURIComponent(problem)}`;
    resultSpan.textContent = "Résultat : En attente"; // Texte par défaut
    resultSpan.style.fontWeight = "bold";
    resultSpan.style.whiteSpace = "nowrap";

    // Assemblage des conteneurs
    problemContainer.appendChild(leftContainer); // Partie gauche
    problemContainer.appendChild(resultSpan); // Partie droite

    li.appendChild(problemContainer); // Ajoute tout au <li>
    problemList.appendChild(li); // Ajoute au <ul>

}

/**
 * @function displayConcluedVote
 * @description Met à jour l'interface pour afficher le résultat d'un vote conclu pour un problème donné.
 * 
 * @param {string} problem - Le problème pour lequel le vote a été conclu.
 * @param {string|number} result - Le résultat du vote (peut être une chaîne ou un nombre selon le mode).
 * 
 * @details
 * - Recherche l'élément HTML correspondant au problème dans la liste via son ID.
 * - Met à jour le contenu textuel du résultat en fonction du mode de jeu sélectionné (ex. : strict, moyenne, médiane).
 * - Prend en compte différents modes de jeu pour formater le texte du résultat.
 */
function displayConcluedVote(problem, result) {
    const resultSpan = document.getElementById(`result-${encodeURIComponent(problem)}`);
    if (resultSpan) {
        // {% if mode_label == "Strict (Unanimité)" %}
        //     resultSpan.textContent = `Résultat unanime : ${result}`;
        // {% elif mode_label == "Moyenne" %}
        //     resultSpan.textContent = `Résultat moyenne : ${result}`;
        // {% elif mode_label == "Médiane" %}
        //     resultSpan.textContent = `Résultat médiane : ${result}`;
        // {% elif mode_label == "Majorité absolue" %}
        //     resultSpan.textContent = `Résultat majorité : ${result}`;
        // {% elif mode_label == "Majorité relative" %}
        //     resultSpan.textContent = `Résultat majorité relative : ${result}`;
        // {% endif %}
    }
}


/**
 * @function displayVote
 * @description Affiche ou met à jour le vote d'un joueur pour un problème.
 * 
 * @param {string} problem - Le problème sélectionné.
 * @param {string} player - Le pseudo du joueur ayant voté.
 * @param {string|number} vote - La valeur du vote du joueur.
 * 
 * @details
 * - Recherche ou crée un élément HTML pour afficher le vote du joueur.
 * - Si un élément pour ce joueur et problème n'existe pas, il est créé dynamiquement.
 * - Ajoute ou met à jour le contenu textuel de l'élément pour inclure le vote du joueur.
 */
function displayVote(problem, player, vote) {
    const problemVotesList = document.getElementById(`result-${problem}`);
    let voteDisplay = document.getElementById(`vote-${player}-${problem}`);

    // Crée ou met à jour le vote du joueur
    if (!voteDisplay) {
        voteDisplay = document.createElement("span");
        voteDisplay.id = `vote-${player}-${problem}`;
        problemVotesList.appendChild(voteDisplay);
    }
    votes = "Votes : ";
    votes += (`${player} : ? | `);
    voteDisplay.textContent = votes;
}


/**
 * @function startGame
 * @description Permet à l'hôte de démarrer la partie en cours.
 * 
 * @details
 * - Émet un événement `start_game` via Socket.IO pour indiquer que la partie a commencé.
 * - Masque le bouton "Démarrer la partie" une fois la partie lancée
 * 
 * @emits start_game
 * - `game_id` : L'ID de la partie en cours.
 */
function startGame() {
    socket.emit("start_game", {game_id: gameId});
    document.getElementById("start-game-button").style.display = "none";  // Masquer le bouto
}




/**
 * @function addProblem
 * @description Permet à l'hôte d'ajouter un nouveau problème à l'aide d'un prompt.
 * 
 * @details
 * - Affiche une boîte de dialogue pour que l'utilisateur puisse entrer un nouveau problème.
 * - Émet un événement `add_problem` via Socket.IO avec le problème ajouté et l'ID de la partie.
 * 
 * @emits add_problem
 * - `game_id` : L'ID de la partie en cours.
 * - `problem` : Le nouveau problème ajouté.
 */
function addProblem() {
    const problem = prompt("Entrez un nouveau problème :");
    if (problem) {
        socket.emit("add_problem", { game_id: gameId, problem: problem });
    }
}


/**
 * @function selectProblem
 * @description Permet à l'hôte de sélectionner un problème pour que les joueurs puissent voter dessus.
 * 
 * @param {string} problem - Le problème sélectionné par l'hôte.
 * 
 * @details
 * - Met à jour le problème actuellement sélectionné dans la variable `currentProblem`.
 * - Émet un événement `select_problem` via Socket.IO avec les détails du problème sélectionné.
 * 
 * @emits select_problem
 * - `game_id` : L'ID de la partie en cours.
 * - `problem` : Le problème sélectionné pour le vote.
 */
function selectProblem(problem) {
    currentProblem = problem;
    socket.emit("select_problem", {game_id: gameId, problem: problem});
}


/**
 * @function devoilerVote
 * @description Permet à l'hôte de dévoiler les votes pour le problème actuellement sélectionné lorsque tous les joueurs ont voté.
 * 
 * @details
 * - Vérifie qu'un problème est sélectionné avant de tenter de dévoiler les votes.
 * - Si aucun problème n'est sélectionné, affiche une alerte à l'utilisateur.
 * - Émet un événement `devoiler_vote` via Socket.IO contenant les détails nécessaires.
 * - Incrémente le compteur pour suivre le nombre de dévoilements effectués.
 * 
 * @emits devoiler_vote
 * - `game_id` : L'ID de la partie en cours.
 * - `problem` : Le problème pour lequel les votes sont dévoilés.
 * - `compteur` : Le nombre de fois que les votes ont été dévoilés pour le problème actuel.
 */
function devoilerVote() {
    if (!currentProblem) {
        alert("Aucun problème sélectionné pour dévoiler les votes.");
        return;
    }
    socket.emit("devoiler_vote", { game_id: gameId, problem: currentProblem, compteur: compteur });
    
    // Augmenter le compteur après le dévoilement
    compteur += 1;
}


/**
 * @function castVote
 * @description Soumet un vote pour le problème actuellement sélectionné.
 * 
 * @param {string|number} vote - La valeur du vote soumis par le joueur.
 * 
 * @details
 * - Vérifie si un problème est sélectionné avant de soumettre un vote.
 * - Si aucun problème n'est sélectionné, affiche une alerte à l'utilisateur.
 * - Émet un événement `cast_vote` via Socket.IO avec les détails du vote.
 * 
 * @emits cast_vote
 * - `game_id` : L'ID de la partie en cours.
 * - `problem` : Le problème actuellement sélectionné pour le vote.
 * - `vote` : La valeur du vote soumis.
 * - `pseudo` : Le pseudo du joueur.
 */
function castVote(vote) {
    if (!currentProblem) {
        alert("Aucun problème sélectionné pour le vote.");
        return;
    }
    socket.emit("cast_vote", {game_id: gameId, problem: currentProblem, vote: vote, pseudo: pseudo});
}


/**
 * @function endGame
 * @description Permet à l'hôte de terminer la partie.
 * 
 * @details
 * - Affiche une boîte de confirmation pour demander à l'utilisateur de confirmer l'action.
 * - Si l'utilisateur confirme, émet un événement `end_game` via Socket.IO avec l'ID de la partie.
 * 
 * @emits end_game
 * - `game_id` : L'identifiant unique de la partie en cours.
 */
function endGame() {
    if (confirm("Êtes-vous sûr de vouloir terminer la partie ?")) {
        socket.emit("end_game", { game_id: gameId });
    }
}


/**
 * @function uploadBacklog
 * @description Permet à l'utilisateur d'importer un fichier JSON contenant un backlog pour initialiser ou mettre à jour une partie.
 * 
 * @details
 * - Lit le contenu du fichier en tant que texte via un FileReader().
 * - Analyse le contenu JSON du fichier et l'envoie au serveur via un événement `upload_backlog` avec l'ID de la partie et le backlog.
 * - Affiche une alerte si aucun fichier n'est sélectionné.
 * 
 * @emits upload_backlog
 * - `game_id` : L'ID de la partie en cours.
 * - `backlog` : Les données du fichier JSON importé.
 */
function uploadBacklog() {
    const fileInput = document.getElementById("backlog-file");
    const file = fileInput.files[0];

    if (file) {
        const reader = new FileReader();
        reader.onload = function (event) {
            const backlog = JSON.parse(event.target.result);
            socket.emit("upload_backlog", { game_id: gameId, backlog: backlog });
        };
        reader.readAsText(file);
    } else {
        alert("Veuillez sélectionner un fichier JSON.");
    }
}


/**
 * @function downloadResultats
 * @description Demande au serveur de sauvegarder les résultats de la partie
 * 
 * @details
 * - Émet un événement `save_resultats` via Socket.IO en envoyant l'ID de la partie.
 * - Le serveur traite la requête et génère un fichier JSON contenant les résultats de la partie.
 * 
 * @emits save_resultats
 * - `game_id` : L'identifiant unique de la partie en cours.
 */

function downloadResultats() {
    socket.emit("save_resultats", { game_id: gameId });
}



// ==================== Événements Socket.IO ==================== //

/**
 * @function socket.on
 *
 * @description
 * Les événements socket.on permettent les intérecations en temps réel entre les joueurs et le serveur.
 * Cela permet de synchroniser entre tous les joueurs et avoir une application fluide. L'interface utilisateur est mise à jour automatiquement.
 * 
 * @socket
 * Exemple : 
 * 
 * socket.on "update_player" :
 * - Il met à jour en temps réel les joueurs qui rejoignent ou qui quittent la partie.
 * 
 * socket.on "problem_selected" :
 * - Afficher le problème sélectionner à voter 
 *
 * socket.on "game_ended" :
 * - Notifier les joueurs que la partie est terminée
 * 
 * socket.on "votes_updated" :
 * - Mise à jour des progression des votes pour le problèmes en cours  
 * 
 */
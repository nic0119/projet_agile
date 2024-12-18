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

// ==================== Événements Socket.IO ==================== //

/**
 * Émet un événement pour rejoindre une salle de jeu.
 */
socket.emit("join_room", { game_id: gameId, pseudo: pseudo });

/**
 * Met à jour l'état de la partie au chargement.
 * @event socket#game_state
 * @param {Object} data - Données de l'état actuel de la partie.
 * @param {string} data.status - Statut de la partie ("active" ou "waiting").
 * @param {string} data.current_problem - Problème actuellement sélectionné.
 * @param {Array<string>} data.problems - Liste des problèmes ajoutés.
 * @param {Object} data.votes - Votes des joueurs pour chaque problème.
 * @param {Object} data.concluded_votes - Résultats des votes déjà dévoilés.
 */
socket.on("game_state", (data) => {
    if (data.status === "active") {
        document.getElementById("game-section").style.display = "block";
        const startButton = document.getElementById("start-game-button");
        if (startButton) startButton.style.display = "none";
    }

    if (data.current_problem) {
        currentProblem = data.current_problem;
        document.getElementById("problem").innerHTML = 
            `Voter pour le problème sélectionné : ${currentProblem}`;
    }

    // Mise à jour des problèmes
    const problemList = document.getElementById("problems-list");
    problemList.innerHTML = "";
    data.problems.forEach(problem => addProblemToUI(problem));

    // Mise à jour des votes
    for (let problem in data.votes) {
        for (let player in data.votes[problem]) {
            displayVote(problem, player, data.votes[problem][player]);
        }
    }

    // Mise à jour des votes conclus
    for (let problem in data.concluded_votes) {
        displayConcluedVote(problem, data.concluded_votes[problem]);
    }
});

/**
 * Affiche un message d'erreur reçu du serveur.
 * @event socket#error
 * @param {Object} data - Contient le message d'erreur.
 * @param {string} data.message - Message d'erreur à afficher.
 */
socket.on("error", (data) => {
    alert(data.message);
});

// ==================== Fonctions Principales ==================== //

/**
 * Ajoute un problème à l'interface utilisateur.
 * @param {string} problem - Le nom du problème à ajouter.
 */
function addProblemToUI(problem) {
    const problemList = document.getElementById("problems-list");
    const li = document.createElement("li");
    li.textContent = problem;
    problemList.appendChild(li);
}

/**
 * Affiche un vote pour un problème spécifique.
 * @param {string} problem - Le problème pour lequel le vote est effectué.
 * @param {string} player - Le pseudo du joueur ayant voté.
 * @param {string|number} vote - La valeur du vote (ex: 1, 5, "café").
 */
function displayVote(problem, player, vote) {
    const problemElement = document.getElementById(`result-${problem}`);
    if (!problemElement) return;

    let voteSpan = document.getElementById(`vote-${player}-${problem}`);
    if (!voteSpan) {
        voteSpan = document.createElement("span");
        voteSpan.id = `vote-${player}-${problem}`;
        problemElement.appendChild(voteSpan);
    }
    voteSpan.textContent = `${player} : ${vote}`;
}

/**
 * Sélectionne un problème pour le vote (hôte uniquement).
 * @param {string} problem - Le problème à sélectionner pour le vote.
 */
function selectProblem(problem) {
    currentProblem = problem;
    socket.emit("select_problem", { game_id: gameId, problem: problem });
}

/**
 * Dévoile les votes pour le problème sélectionné.
 * Accessible uniquement à l'hôte.
 */
function devoilerVote() {
    if (!currentProblem) {
        alert("Aucun problème sélectionné pour dévoiler les votes.");
        return;
    }
    socket.emit("devoiler_vote", { game_id: gameId, problem: currentProblem, compteur: compteur });
    compteur += 1;
}

/**
 * Affiche le résultat dévoilé pour un problème.
 * @param {string} problem - Le problème concerné.
 * @param {string|number} result - Le résultat final des votes.
 */
function displayConcluedVote(problem, result) {
    const resultElement = document.getElementById(`result-${problem}`);
    if (resultElement) {
        resultElement.textContent = `Résultat : ${result}`;
    }
}

// ==================== Autres Fonctions ==================== //

/**
 * Termine la partie en cours (hôte uniquement).
 */
function endGame() {
    if (confirm("Êtes-vous sûr de vouloir terminer la partie ?")) {
        socket.emit("end_game", { game_id: gameId });
    }
}

/**
 * Émet un événement pour ajouter un problème à la partie.
 */
function addProblem() {
    const problem = prompt("Entrez un nouveau problème :");
    if (problem) {
        socket.emit("add_problem", { game_id: gameId, problem: problem });
    }
}

/**
 * Télécharge les résultats de la partie.
 */
function downloadResultats() {
    socket.emit("save_resultats", { game_id: gameId });
}

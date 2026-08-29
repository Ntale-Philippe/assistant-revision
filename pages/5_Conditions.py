"""Conditions d'utilisation : page publique, aucune identification requise."""

import streamlit as st

from core.navigation import afficher_navigation

st.set_page_config(page_title="Conditions d'utilisation", page_icon="assets/icone.png", layout="centered")
afficher_navigation()

st.title("Conditions d'utilisation")

st.markdown(
    """
### 1. Objet

Cette application aide à réviser un cours à partir de documents déposés par
l'utilisateur (notes, PDF, images) : génération d'une fiche de synthèse, de quiz,
et d'une discussion libre avec une intelligence artificielle (Google Gemini).
Date de dernière mise à jour: 28/08/2026

### 2. Accès

L'accès à l'appli se fait avec un prénom et une clé API Gemini propre à chaque
utilisateur (gratuite, à créer soi-même sur Google AI Studio). L'appli est
actuellement gratuite ; ces conditions seront mises à jour si un modèle payant
est introduit par la suite.

### 3. Données et confidentialité

Le contenu des documents déposés est envoyé à l'API Google Gemini pour être analysé ;
c'est le seul tiers avec lequel ce contenu est partagé. Les données de chaque
utilisateur (cours, documents, scores, historique de discussion) sont strictement
privées : aucun autre utilisateur de l'appli n'y a accès. Sans le lien personnel et
la clé associés, ces données ne peuvent pas être retrouvées.

### 4. Limites de responsabilité

Cette application dépend de services tiers (Google Gemini pour l'intelligence
artificielle, Turso pour le stockage des données, Streamlit pour l'hébergement) dont
la disponibilité n'est pas garantie à 100 %. Le contenu généré par l'intelligence
artificielle (synthèses, quiz, réponses) peut contenir des erreurs ou des
approximations : il est fourni à titre d'aide à la révision et ne remplace pas les
supports de cours officiels ni le jugement de l'étudiant.

### 5. Restitution ou suppression des données

Sur simple demande via le contact ci-dessous, il est possible d'obtenir un export de
ses données (contenu de ses cours) ou leur suppression complète.

### 6. Contact

Pour toute question ou réclamation :
+243 849721720 / assistantrevision@gmail.com
"""
)

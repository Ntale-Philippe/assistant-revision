"""Conditions d'utilisation : page publique, aucune identification requise."""

import streamlit as st

st.set_page_config(page_title="Conditions d'utilisation", layout="centered")

st.title("Conditions d'utilisation")
st.caption("Dernière mise à jour : à compléter par le vendeur avant la mise en ligne.")

st.markdown(
    """
### 1. Objet

Cette application aide à réviser un cours à partir de documents déposés par
l'utilisateur (notes, PDF, images) : génération d'une fiche de synthèse, de quiz,
et d'une discussion libre avec une intelligence artificielle (Google Gemini).

### 2. Accès et compte

L'accès à l'appli se fait avec un prénom, un code d'accès personnel fourni par le
vendeur après paiement, et une clé API Gemini propre à chaque utilisateur (gratuite,
à créer soi-même sur Google AI Studio). Ce code est **personnel et non transférable** :
le vendeur peut le désactiver s'il constate un partage non autorisé.

### 3. Durée et renouvellement

Chaque code a une durée d'accès définie au moment de l'achat (par exemple un mois ou
un semestre). Passé ce délai, l'accès est automatiquement suspendu. Le renouvellement
se fait en recontactant le vendeur.

### 4. Paiement

Le paiement s'effectue directement auprès du vendeur, par le moyen convenu avec lui
(l'application elle-même ne traite aucun paiement). Les modalités de remboursement,
le cas échéant, sont à discuter au cas par cas directement avec le vendeur.

### 5. Données et confidentialité

Le contenu des documents déposés est envoyé à l'API Google Gemini pour être analysé ;
c'est le seul tiers avec lequel ce contenu est partagé. Les données de chaque
utilisateur (cours, documents, scores, historique de discussion) sont strictement
privées : aucun autre utilisateur de l'appli, ni le vendeur, n'y a accès. Sans le
code d'accès et le prénom associés, ces données ne peuvent pas être retrouvées.

### 6. Limites de responsabilité

Cette application dépend de services tiers (Google Gemini pour l'intelligence
artificielle, Turso pour le stockage des données, Streamlit pour l'hébergement) dont
la disponibilité n'est pas garantie à 100 %. Le contenu généré par l'intelligence
artificielle (synthèses, quiz, réponses) peut contenir des erreurs ou des
approximations : il est fourni à titre d'aide à la révision et ne remplace pas les
supports de cours officiels ni le jugement de l'étudiant.

### 7. Résiliation

Le vendeur se réserve le droit de suspendre ou révoquer un accès en cas d'usage
abusif, de partage non autorisé du code, ou de non-respect des présentes conditions.

### 7bis. Restitution des données à la clôture

Sur simple demande via le contact ci-dessous, le vendeur peut fournir un export des
données d'un utilisateur (ex: contenu de ses cours) avant suppression de son compte.

### 8. Contact

Pour toute question, réclamation ou demande de renouvellement :
**à compléter par le vendeur (e-mail ou numéro de contact).**
"""
)

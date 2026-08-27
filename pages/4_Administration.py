"""Page d'administration : génération et gestion des codes de licence.

Réservée au vendeur (toi). Protégée par un mot de passe (ADMIN_PASSWORD dans
.streamlit/secrets.toml) — sans ce mot de passe, personne d'autre ne peut y accéder,
même en connaissant l'adresse de la page.
"""

import streamlit as st

from core import repository
from core.db import init_db

st.set_page_config(page_title="Administration", layout="centered")
init_db()

st.title("Administration")

try:
    mot_de_passe_attendu = st.secrets["ADMIN_PASSWORD"]
except Exception:
    mot_de_passe_attendu = None

if not mot_de_passe_attendu:
    st.error(
        "Aucun mot de passe administrateur configuré. Ajoute "
        "`ADMIN_PASSWORD = \"...\"` dans `.streamlit/secrets.toml` (en local) ou dans "
        "les secrets de ton appli sur share.streamlit.io (en ligne)."
    )
    st.stop()

if not st.session_state.get("admin_ok"):
    with st.form("admin_login"):
        saisi = st.text_input("Mot de passe administrateur", type="password")
        ok = st.form_submit_button("Entrer")
        if ok:
            if saisi == mot_de_passe_attendu:
                st.session_state["admin_ok"] = True
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")
    st.stop()

st.success("Accès administrateur confirmé.")

st.divider()

# --- Générer un nouveau code -------------------------------------------------

st.subheader("Générer un nouveau code de licence")
st.caption("À faire après avoir reçu un paiement. Donne ensuite ce code au client.")

with st.form("nouveau_code_form", clear_on_submit=True):
    note = st.text_input("Note (pour toi seulement)", placeholder="Ex : Alice - payé le 27/08")
    generer = st.form_submit_button("Générer un code")
    if generer:
        nouveau_code = repository.generer_code_licence()
        repository.creer_licence(nouveau_code, note.strip())
        st.session_state["dernier_code_genere"] = nouveau_code

if st.session_state.get("dernier_code_genere"):
    st.success("Nouveau code généré — copie-le et envoie-le au client :")
    st.code(st.session_state["dernier_code_genere"], language=None)

st.divider()

# --- Liste des codes -----------------------------------------------------------

st.subheader("Tous les codes")

licences = repository.lister_licences()
if not licences:
    st.info("Aucun code généré pour l'instant.")
else:
    badges = {"disponible": "Disponible", "attribuee": "Attribuée", "revoquee": "Révoquée"}
    for licence in licences:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{licence['code']}** — {badges.get(licence['statut'], licence['statut'])}")
                if licence.get("note"):
                    st.caption(licence["note"])
                if licence.get("prenom_client"):
                    st.caption(f"Utilisé par : {licence['prenom_client']} (le {licence.get('activee_le', '?')})")
            with col2:
                if licence["statut"] == "revoquee":
                    if st.button("Réactiver", key=f"reactiver_{licence['code']}"):
                        repository.reactiver_licence(licence["code"])
                        st.rerun()
                else:
                    if st.button("Révoquer", key=f"revoquer_{licence['code']}"):
                        repository.revoquer_licence(licence["code"])
                        st.rerun()

"""Page d'administration : génération et gestion des codes de licence.

Réservée au vendeur (toi). Protégée par un mot de passe (ADMIN_PASSWORD dans
.streamlit/secrets.toml) — sans ce mot de passe, personne d'autre ne peut y accéder,
même en connaissant l'adresse de la page.
"""

from datetime import datetime

import streamlit as st

from core import repository
from core.db import init_db
from core.export_service import generer_excel_licences

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

tab_codes, tab_export = st.tabs(["Codes de licence", "Export Excel"])

DUREES_PREDEFINIES = {
    "1 mois (30 jours)": 30,
    "1 semestre (120 jours)": 120,
    "Personnalisé": None,
}

# --- Onglet Codes --------------------------------------------------------------

with tab_codes:
    st.subheader("Générer un nouveau code de licence")
    st.caption(
        "À faire après avoir reçu un paiement. Le compte à rebours ne démarre que "
        "lorsque le client utilise le code pour la première fois — pas dès sa génération."
    )

    choix_duree = st.selectbox("Durée d'accès", list(DUREES_PREDEFINIES.keys()))
    if DUREES_PREDEFINIES[choix_duree] is None:
        duree_jours = st.number_input("Nombre de jours", min_value=1, value=30, step=1)
    else:
        duree_jours = DUREES_PREDEFINIES[choix_duree]

    with st.form("nouveau_code_form", clear_on_submit=True):
        note = st.text_input("Note (pour toi seulement)", placeholder="Ex : Alice - contact WhatsApp")
        col_montant, col_devise = st.columns([2, 1])
        with col_montant:
            montant = st.number_input("Montant payé", min_value=0.0, value=5.0, step=0.5)
        with col_devise:
            devise = st.text_input("Devise", value="USD")
        generer = st.form_submit_button("Générer un code")
        if generer:
            nouveau_code = repository.generer_code_licence()
            repository.creer_licence(nouveau_code, note.strip(), int(duree_jours), montant, devise.strip() or "USD")
            st.session_state["dernier_code_genere"] = nouveau_code

    if st.session_state.get("dernier_code_genere"):
        st.success("Nouveau code généré — copie-le et envoie-le au client :")
        st.code(st.session_state["dernier_code_genere"], language=None)

    st.divider()
    st.subheader("Tous les codes")

    licences = repository.lister_licences()
    if not licences:
        st.info("Aucun code généré pour l'instant.")
    else:
        a_relancer = [l for l in licences if l.get("a_relancer") and l["statut"] != "revoquee"]
        if a_relancer:
            st.warning(f"{len(a_relancer)} client(s) à relancer pour un renouvellement (expiré ou bientôt expiré).")

        for licence in licences:
            expiree = bool(licence.get("expiree"))
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    statut_affiche = "Expirée" if expiree and licence["statut"] != "revoquee" else {
                        "disponible": "Disponible", "attribuee": "Attribuée", "revoquee": "Révoquée",
                    }.get(licence["statut"], licence["statut"])
                    titre = f"**{licence['code']}** — {statut_affiche}"
                    if licence.get("a_relancer") and licence["statut"] != "revoquee":
                        titre += " — à relancer"
                    st.markdown(titre)
                    st.caption(f"Durée : {licence['duree_jours']} jours" + (
                        f" · {licence['montant']} {licence['devise']}" if licence.get("montant") else ""
                    ))
                    if licence.get("note"):
                        st.caption(licence["note"])
                    if licence.get("prenom_client"):
                        st.caption(f"Utilisé par : {licence['prenom_client']} (activé le {licence.get('activee_le', '?')})")
                    if licence.get("expire_le"):
                        label = "Expiré le" if expiree else "Expire le"
                        jours_restants = licence.get("jours_restants")
                        suffixe = f" ({jours_restants} j restants)" if jours_restants is not None and not expiree else ""
                        st.caption(f"{label} : {licence['expire_le']}{suffixe}")
                with col2:
                    if licence["statut"] == "revoquee":
                        if st.button("Réactiver", key=f"reactiver_{licence['code']}"):
                            repository.reactiver_licence(licence["code"])
                            st.rerun()
                    else:
                        if st.button("Renouveler", key=f"renouveler_{licence['code']}"):
                            repository.prolonger_licence(licence["code"])
                            st.rerun()
                        if st.button("Révoquer", key=f"revoquer_{licence['code']}"):
                            repository.revoquer_licence(licence["code"])
                            st.rerun()

# --- Onglet Export -----------------------------------------------------------

with tab_export:
    st.subheader("Export Excel")
    st.caption(
        "Télécharge un fichier .xlsx avec tous les codes : client, montant, durée, "
        "dates, et qui doit être relancé pour repayer."
    )

    licences_export = repository.lister_licences()
    if not licences_export:
        st.info("Aucune donnée à exporter pour l'instant.")
    else:
        contenu_excel = generer_excel_licences()
        horodatage = datetime.now().strftime("%Y-%m-%d")
        st.download_button(
            "Télécharger le fichier Excel",
            data=contenu_excel,
            file_name=f"codes_licence_{horodatage}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.caption(f"{len(licences_export)} code(s) au total.")

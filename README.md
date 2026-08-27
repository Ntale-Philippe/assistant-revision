# 🧬 Mon assistant de révision

Une petite application qui lit tes notes de cours (PDF, images, texte), te fait une
fiche de synthèse, et te teste avec 3 quiz : un avant révision, le même après (pour
voir ta progression), et un examen blanc chronométré.

## 1. Récupérer ta clé Gemini gratuite (une seule fois)

1. Va sur https://aistudio.google.com/apikey
2. Connecte-toi avec ton compte Google
3. Clique sur **"Create API key"** → **"Create API key in new project"**
4. Copie la clé qui apparaît
5. Ouvre le fichier `.streamlit/secrets.toml` dans ce dossier et remplace
   `colle-ta-cle-ici` par ta vraie clé, entre guillemets. Exemple :
   ```toml
   GEMINI_API_KEY = "AIzaSyABCDEF1234567890"
   ```
6. Enregistre le fichier. C'est tout, tu ne referas ça qu'une seule fois.

⚠️ Ne partage jamais cette clé (ne l'envoie pas par mail, ne la mets pas sur internet).

## 2. Lancer l'application

Ouvre un terminal dans ce dossier et tape :

```bash
".venv/Scripts/python.exe" -m streamlit run app.py
```

Une page va s'ouvrir automatiquement dans ton navigateur. Pour arrêter l'application,
retourne dans le terminal et appuie sur `Ctrl + C`.

## 3. Utilisation

1. Crée un cours (ex: "Biochimie métabolique")
2. Dépose tes documents (PDF, captures d'écran, notes texte)
3. Génère la fiche de synthèse
4. Passe le quiz diagnostique (avant révision)
5. Révise avec ta fiche de synthèse
6. Repasse le même quiz (après révision) et regarde ta progression
7. Teste-toi en conditions réelles avec l'examen blanc chronométré

Toutes tes données (cours, documents, scores) restent uniquement sur ton ordinateur,
dans le dossier `data/`.

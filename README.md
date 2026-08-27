# Mon assistant de révision

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

Ne partage jamais cette clé (ne l'envoie pas par mail, ne la mets pas sur internet).

## 2. Lancer l'application

Ouvre un terminal dans ce dossier et tape :

```bash
".venv/Scripts/python.exe" -m streamlit run app.py
```

Une page va s'ouvrir automatiquement dans ton navigateur. Pour arrêter l'application,
retourne dans le terminal et appuie sur `Ctrl + C`.

## 3. Utilisation

1. Crée un cours (n'importe quelle matière : droit, économie, ingénierie, lettres...)
2. Dépose tes documents (PDF, captures d'écran, notes texte)
3. Génère la fiche de synthèse
4. Passe le quiz diagnostique (avant révision)
5. Révise avec ta fiche de synthèse
6. Repasse le même quiz (après révision) et regarde ta progression
7. Teste-toi en conditions réelles avec l'examen blanc chronométré

Toutes tes données (cours, documents, scores) restent uniquement sur ton ordinateur,
dans le dossier `data/`.

## 4. Mettre en ligne pour vendre ou partager (gratuit, sans que ton PC reste allumé)

L'appli sait fonctionner en **mode partagé** : plusieurs personnes peuvent l'utiliser
en même temps, chacune avec ses propres cours (invisibles pour les autres, y compris
pour toi) et sa propre clé Gemini gratuite. Pour ça, il faut la mettre en ligne gratuitement :

1. **Crée un compte GitHub gratuit** sur https://github.com (si tu n'en as pas déjà un).
2. **Crée un nouveau repository** (bouton vert "New") — tu peux le laisser privé ou public.
3. Connecte ce dossier au repository que tu viens de créer et envoie le code :
   ```bash
   git remote add origin https://github.com/TON-PSEUDO/NOM-DU-REPO.git
   git push -u origin master
   ```
   (Git te demandera de te connecter à ton compte GitHub la première fois — suis les
   instructions à l'écran, aucune clé/mot de passe ne passe par moi.)
4. **Crée un compte gratuit** sur https://share.streamlit.io (connecte-toi avec GitHub).
5. Clique sur **"New app"**, choisis ton repository, la branche `master`, et le fichier
   principal `app.py`. Clique sur **"Deploy"**.
6. Après quelques minutes, tu obtiens un lien du genre `https://tonapp.streamlit.app`
   — c'est CE lien que tu partages avec tes collègues.

Ne mets jamais ta clé API dans le code que tu envoies sur GitHub — le fichier
`.streamlit/secrets.toml` est volontairement exclu (voir `.gitignore`), c'est normal
et voulu : l'appli hébergée n'a besoin d'aucune clé "globale", chacun apporte la sienne.

Une fois en ligne, ajoute aussi un mot de passe administrateur dans les secrets de ton
appli sur share.streamlit.io (section "Secrets" des paramètres de l'appli) :
```toml
ADMIN_PASSWORD = "un mot de passe que toi seul connais"
```

## 5. Vendre l'accès (codes de licence)

Personne ne peut entrer dans l'appli en mode partagé sans un **code de licence**
généré par toi. C'est ta vraie barrière de paiement — sans elle, n'importe qui pourrait
utiliser le lien gratuitement avec sa propre clé Gemini.

1. Un client te contacte et te paie (par le moyen de ton choix, en dehors de l'appli).
2. Tu vas sur `https://tonapp.streamlit.app/Administration`, tu entres ton mot de passe
   administrateur.
3. Tu cliques sur **"Générer un code"** (avec une note pour te souvenir de qui c'est).
4. Tu envoies au client : le lien de l'appli + le code généré, et tu lui rappelles
   d'aller chercher sa propre clé Gemini gratuite (étape 1 de ce README).
5. Le client entre son prénom, le code que tu lui as donné, et sa clé — il est alors
   dans l'appli, avec son espace privé.

Si un code fuite ou est partagé sans ton accord, tu peux le **révoquer** à tout moment
depuis la page Administration : la personne sera bloquée dès sa prochaine visite.

Il n'y a pas de "code oublié" : si un client perd à la fois son lien personnel et son
code, il doit te recontacter pour qu'un nouveau code lui soit fourni. Préviens-en tes clients.

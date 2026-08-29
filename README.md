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
dans le dossier `data/`. Une page `/Demo` (accessible sans identification) montre un
exemple déjà prêt (cours de macroéconomie) — pratique pour montrer l'appli à quelqu'un
sans qu'il ait besoin de créer sa clé Gemini avant d'avoir vu ce que ça donne.

**État actuel : l'appli est gratuite pour tout le monde** (chacun apporte juste sa
propre clé Gemini gratuite). L'idée est de valider que ça aide vraiment les étudiants
avant d'introduire un jour un modèle payant.

## 4. Base de données permanente (Turso) — recommandé si tu la mets en ligne

En local, tes données vivent dans `data/app.db`, un simple fichier sur ton PC. Mais une
fois l'appli hébergée en ligne (étape 5), cet hébergement gratuit peut effacer ce
fichier à tout moment (mise à jour du code, redémarrage après une période d'inactivité).
Pour ne jamais perdre les codes de licence vendus ni les cours de tes clients, on
branche l'appli sur une vraie base de données qui, elle, ne s'efface jamais :

1. Crée un compte gratuit sur https://turso.tech
2. Crée une base de données (bouton "Create Database", garde les réglages par défaut).
3. Dans le tableau de bord de ta base, récupère :
   - l'**URL de connexion** (commence par `libsql://...`)
   - un **jeton d'authentification** (auth token) — génère-le depuis l'onglet dédié
4. Ajoute ces deux valeurs dans `.streamlit/secrets.toml`, exactement comme Turso te
   les donne (garde le préfixe `libsql://`, l'appli l'ajuste elle-même) :
   ```toml
   TURSO_DATABASE_URL = "libsql://ton-nom-de-base.turso.io"
   TURSO_AUTH_TOKEN = "ton-jeton-ici"
   ```
5. Relance l'appli : elle utilisera automatiquement Turso au lieu du fichier local dès
   que ces deux valeurs sont présentes. Sans elles, elle continue de fonctionner en
   local exactement comme avant (pratique pour tester sur ton PC).

Aucune installation supplémentaire n'est nécessaire : l'appli parle à Turso directement
par le web (rien à compiler, ça marche sur n'importe quelle machine).

## 5. Mettre en ligne pour partager (gratuit, sans que ton PC reste allumé)

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

Une fois en ligne, ajoute dans les secrets de ton appli sur share.streamlit.io (section
"Secrets" des paramètres de l'appli) les **mêmes valeurs** que dans ton
`.streamlit/secrets.toml` local — surtout `TURSO_DATABASE_URL` / `TURSO_AUTH_TOKEN` de
l'étape 4 (sans elles en ligne, l'appli hébergée repartirait sur un fichier local non
permanent) :
```toml
TURSO_DATABASE_URL = "libsql://ton-nom-de-base.turso.io"
TURSO_AUTH_TOKEN = "ton-jeton-ici"
```

⚠️ Ne mets **pas** `GEMINI_API_KEY` dans les secrets de l'appli en ligne : ça
donnerait à tout le monde un accès "solo" sans même passer par l'écran
d'identification. Chacun doit apporter sa propre clé.

## 6. Remettre un modèle payant plus tard

Le système de codes de licence (génération, expiration, renouvellement, export Excel
des ventes) a été retiré pour l'instant, le temps de valider que l'appli aide
vraiment les étudiants en la rendant gratuite. Il reste dans l'historique Git de ce
projet (page `Administration`, `core/export_service.py`, table `licences`) et pourra
être réintroduit quand l'envie de faire payer reviendra.

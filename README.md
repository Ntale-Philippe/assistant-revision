# Mon assistant de révision

Une petite application qui lit tes notes de cours (PDF, images, texte), te fait une
fiche de synthèse, et te teste avec 3 quiz : un avant révision, le même après (pour
voir ta progression), et un examen blanc chronométré.

**Personne d'autre que toi (le propriétaire de l'appli) n'a besoin de créer la moindre
clé.** Les étudiants qui utilisent l'appli n'ont qu'un prénom et un mot de passe
personnel à inventer — l'appli utilise en coulisses deux IA que tu configures une
fois pour toutes.

## Pourquoi deux IA différentes ?

- **Mistral** génère la synthèse, les quiz et répond dans le chat (l'essentiel de
  l'usage). Son plan gratuit est généreux (environ 1 milliard de mots par mois) et ne
  demande aucune carte bancaire.
- **Gemini** sert uniquement à lire les images et les PDF scannés (OCR) — un usage
  rare, donc son plan gratuit (limité) suffit largement pour ça seulement.

(Groq a été essayé pour remplacer Gemini côté texte, mais bloque le trafic venant de
serveurs cloud comme celui qui héberge l'appli une fois en ligne — abandonné, voir
l'historique Git si besoin de retenter un jour avec un contournement.)

## 1. Récupérer tes deux clés gratuites (une seule fois, pour toi)

**Clé Mistral :**
1. Va sur https://console.mistral.ai, crée un compte (email ou Google)
2. Va dans **"API Keys"**, clique sur **"Create new key"**, copie la clé

**Clé Gemini :**
1. Va sur https://aistudio.google.com/apikey
2. Connecte-toi avec ton compte Google
3. Clique sur **"Create API key"** → **"Create API key in new project"**
4. Copie la clé qui apparaît

**Puis**, ouvre le fichier `.streamlit/secrets.toml` dans ce dossier et colle tes deux
clés (chacune à deux endroits, voir pourquoi juste en dessous) :
```toml
MISTRAL_API_KEY = "ta-cle-mistral-ici"
SHARED_MISTRAL_API_KEY = "ta-cle-mistral-ici"

GEMINI_API_KEY = "ta-cle-gemini-ici"
SHARED_GEMINI_API_KEY = "ta-cle-gemini-ici"
```
Enregistre le fichier. C'est tout, tu ne referas ça qu'une seule fois.

Pourquoi deux lignes par clé ? La version sans `SHARED_` sert uniquement quand **toi**
tu lances l'appli sur ton PC (mode solo, aucune identification demandée). La version
`SHARED_` est celle utilisée par **tous les étudiants** une fois l'appli en ligne.
Elles peuvent être identiques (comme ici), ou différentes si tu veux séparer ton usage
perso de celui des étudiants.

Ne partage jamais ces clés (ne les envoie pas par mail, ne les mets pas sur internet).

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
3. (Facultatif) Dépose aussi d'anciens examens de ce cours si tu en as : l'IA s'en
   sert en priorité pour deviner les vraies notions probables et composer des quiz
   dans le style de ton professeur
4. Génère la fiche de synthèse
5. Passe le quiz diagnostique (avant révision)
6. Révise avec ta fiche de synthèse
7. Repasse le même quiz (après révision) et regarde ta progression
8. Teste-toi en conditions réelles avec l'examen blanc chronométré
9. Entraîne-toi aussi avec les questions à réponse écrite (rédigées, corrigées par
   l'IA) — un 4ᵉ mode d'entraînement, séparé des 3 quiz ci-dessus

Toutes tes données (cours, documents, scores) restent uniquement sur ton ordinateur,
dans le dossier `data/`. Une page `/Demo` (accessible sans identification) montre un
exemple déjà prêt (cours de macroéconomie) — pratique pour montrer l'appli à quelqu'un
et qu'il voie un résultat concret avant même de créer son espace personnel.

**État actuel : l'appli est gratuite pour tout le monde.** L'idée est de valider que
ça aide vraiment les étudiants avant d'introduire un jour un modèle payant.

## 4. Base de données permanente (Turso) — recommandé si tu la mets en ligne

En local, tes données vivent dans `data/app.db`, un simple fichier sur ton PC. Mais une
fois l'appli hébergée en ligne (étape 5), cet hébergement gratuit peut effacer ce
fichier à tout moment (mise à jour du code, redémarrage après une période d'inactivité).
Pour ne jamais perdre les cours et la progression des étudiants, on branche l'appli
sur une vraie base de données qui, elle, ne s'efface jamais :

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
pour toi). Pour ça, il faut la mettre en ligne gratuitement :

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
   — c'est CE lien que tu partages avec tes étudiants.

Ne mets jamais tes clés dans le code que tu envoies sur GitHub — le fichier
`.streamlit/secrets.toml` est volontairement exclu (voir `.gitignore`).

Une fois en ligne, ajoute dans les secrets de ton appli sur share.streamlit.io (section
"Secrets" des paramètres de l'appli) :
```toml
SHARED_MISTRAL_API_KEY = "ta-cle-mistral-ici"
SHARED_GEMINI_API_KEY = "ta-cle-gemini-ici"
TURSO_DATABASE_URL = "libsql://ton-nom-de-base.turso.io"
TURSO_AUTH_TOKEN = "ton-jeton-ici"
ADMIN_PASSWORD = "invente-un-mot-de-passe-perso"
```

`ADMIN_PASSWORD` débloque la section "Statistiques avancées" de la page Statistiques
(insights sur l'ensemble des étudiants : cours bloqués, échecs de lecture, scores par
type de quiz...) — invente un mot de passe rien qu'à toi, différent de ton prénom/mot
de passe habituel.

⚠️ Ne mets **jamais** `MISTRAL_API_KEY`/`GEMINI_API_KEY` (sans le préfixe SHARED_) dans
les secrets de l'appli en ligne : ça donnerait à n'importe quel visiteur anonyme un
accès "solo" instantané, sans passer par l'écran d'identification, et il verrait
potentiellement tes propres cours de test. Utilise bien les noms `SHARED_...` en ligne.

## 6. Remettre un modèle payant plus tard

Le système de codes de licence (génération, expiration, renouvellement, export Excel
des ventes) a été retiré pour l'instant, le temps de valider que l'appli aide
vraiment les étudiants en la rendant gratuite et très simple d'accès (juste un prénom
et un mot de passe, aucune clé technique à créer). Le code retiré reste dans
l'historique Git de ce projet (page `Administration`, `core/export_service.py`, table
`licences`) et pourra être réintroduit quand l'envie de faire payer reviendra.

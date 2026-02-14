# 🚀 Guide Setup Git & GitHub - Scraper-Pro

## ✅ Ce qui SERA commité (sûr)

### Code Source
- `scraper/` (tous les spiders, middlewares, pipelines)
- `dashboard/` (interface Streamlit)
- `db/migrations/` (schémas SQL)
- `config/` (templates de configuration)
- `scripts/` (scripts de déploiement)
- `tests/` (tests unitaires)

### Configuration
- `docker-compose*.yml` (toutes les configs Docker)
- `Dockerfile`, `Dockerfile.dashboard`
- `requirements.txt`
- `.env.example` ✅ (exemple SANS secrets)
- `.gitignore` ✅ (nouvellement sécurisé)

### Documentation
- `README.md`
- `docs/*.md` (tous les guides)
- Tous les `*.md` à la racine

### CI/CD
- `.github/workflows/` (GitHub Actions)

---

## ❌ Ce qui NE SERA PAS commité (protégé)

### Secrets
- `.env` ❌ (contient vos vrais mots de passe)
- `.env.production` ❌
- `.env.optimized` ❌
- `*-secrets-*.txt` ❌
- `secrets/` ❌

### Données
- `data/`, `output/`, `exports/` ❌
- `*.sql.gz`, `backups/` ❌
- `*.csv`, `*.jsonl` ❌

### Temporaires
- `__pycache__/`, `*.pyc` ❌
- `logs/` ❌
- `node_modules/` ❌
- `venv/` ❌

---

## 📋 Commandes à Exécuter (Pas-à-Pas)

### 1. Vérifier que .gitignore est bien configuré

```powershell
# Sur votre PC
cd C:\Users\willi\Documents\Projets\VS_CODE\scraper-pro

# Vérifier le .gitignore
cat .gitignore | Select-String -Pattern "\.env"
# Doit afficher : .env, .env.production, etc.
```

✅ **Si vous voyez `.env` dans les résultats, c'est bon !**

---

### 2. Vérifier quels fichiers SERONT ajoutés

```powershell
# Simulation (dry-run)
git add --dry-run .

# OU voir tous les fichiers non-trackés
git status --short

# Vérifier qu'aucun fichier .env ou secret n'apparaît
git status | Select-String -Pattern "\.env"
# Doit retourner RIEN (vide)
```

---

### 3. Créer le repo GitHub

1. **Aller sur** : https://github.com/new
2. **Nom du repo** : `scraper-pro`
3. **Visibilité** : `Private` ✅ (IMPORTANT)
4. **NE PAS** cocher "Initialize with README"
5. **Cliquer** : "Create repository"

**GitHub va afficher des commandes, IGNOREZ-LES** (on les fait ici) ✋

---

### 4. Connecter votre repo local à GitHub

```powershell
# Remplacer VOTRE-USERNAME par votre username GitHub
git remote add origin https://github.com/VOTRE-USERNAME/scraper-pro.git

# Vérifier
git remote -v
# Doit afficher :
# origin  https://github.com/VOTRE-USERNAME/scraper-pro.git (fetch)
# origin  https://github.com/VOTRE-USERNAME/scraper-pro.git (push)
```

---

### 5. Ajouter SEULEMENT les fichiers sûrs

```powershell
# Ajouter le .gitignore en premier
git add .gitignore

# Vérifier qu'il est bien ajouté
git status
# Doit afficher : "new file:   .gitignore"

# Ajouter tous les autres fichiers (le .gitignore protège les secrets)
git add .

# VÉRIFICATION CRITIQUE : Lister TOUS les fichiers qui vont être commités
git diff --cached --name-only

# Examinez la liste :
# ✅ OK : scraper/, dashboard/, docs/, *.md, docker-compose*.yml
# ❌ PAS OK : .env, .env.production, secrets/, *-secrets-*.txt
```

**⚠️ SI vous voyez `.env` ou `secrets/` dans la liste** :

```powershell
# Retirer les fichiers dangereux
git reset .env
git reset .env.production
git reset .env.optimized
git reset secrets/

# Re-vérifier
git diff --cached --name-only
```

---

### 6. Commit

```powershell
# Commit avec message descriptif
git commit -m "feat: initial commit - scraper-pro production-ready

- Spiders: Google Search/Maps, URLs, Blog Content
- Dashboard: Streamlit avec logs détaillés
- Dual-app support: Backlink Engine + Scraper-Pro
- Auto-deployment scripts
- Full documentation (FR)
- Docker Compose optimisé pour 2 vCPU / 4 GB RAM"

# Vérifier le commit
git log --oneline -1
```

---

### 7. Push vers GitHub

```powershell
# Créer la branche main et push
git branch -M main
git push -u origin main
```

**Si demande d'authentification** :
- **Username** : Votre username GitHub
- **Password** : Utilisez un **Personal Access Token** (PAS votre mot de passe GitHub)

**Créer un token** : https://github.com/settings/tokens/new
- Cochez : `repo` (full control)
- Générez et copiez le token
- Utilisez-le comme password

---

### 8. Vérifier sur GitHub

1. Aller sur : `https://github.com/VOTRE-USERNAME/scraper-pro`
2. Vérifier que les fichiers sont bien là
3. **CRITIQUE** : Vérifier qu'aucun `.env` n'est visible

**Comment vérifier** :
- Cherchez `.env` dans les fichiers sur GitHub
- Si vous le voyez → **PROBLÈME** → Voir section "Urgence" ci-dessous

---

## 🚨 URGENCE : Si .env a été commité par erreur

```powershell
# 1. Retirer .env de l'historique Git
git rm --cached .env .env.production .env.optimized

# 2. Commit la suppression
git commit -m "security: remove sensitive .env files from Git"

# 3. Force push (écrase l'historique GitHub)
git push origin main --force

# 4. Vérifier sur GitHub que .env n'est plus visible
```

**Ensuite** : Changez TOUS vos mots de passe (PostgreSQL, Redis, API, etc.) car ils étaient publics pendant quelques minutes.

---

## ✅ Checklist Finale

- [ ] `.gitignore` contient `.env`, `.env.*`, `secrets/`
- [ ] `git status` ne montre AUCUN fichier `.env`
- [ ] `git diff --cached --name-only` ne contient pas de secrets
- [ ] Repo GitHub créé en **Private**
- [ ] Remote configuré : `git remote -v`
- [ ] Commit effectué
- [ ] Push réussi : `git push -u origin main`
- [ ] Vérifié sur GitHub : aucun `.env` visible
- [ ] `.env.example` est bien présent (sans secrets)

---

## 🚀 Déploiement sur le Serveur (après push GitHub)

```bash
# SSH sur le serveur
ssh root@89.167.26.169

# Clone depuis GitHub
cd /opt
git clone https://github.com/VOTRE-USERNAME/scraper-pro.git
cd scraper-pro

# Lancer le déploiement
chmod +x scripts/deploy-add-to-existing.sh
./scripts/deploy-add-to-existing.sh
```

---

## 📝 Futurs Updates (super facile après setup)

**Sur votre PC** :
```powershell
# Modifier des fichiers
# ...

# Commit
git add .
git commit -m "fix: improve scraping performance"
git push
```

**Sur le serveur** :
```bash
cd /opt/scraper-pro
git pull
docker compose -f docker-compose.add-to-existing.yml restart
```

---

**Voilà ! Setup Git sécurisé terminé ! 🎉**

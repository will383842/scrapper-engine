# 📘 Guide Utilisateur SCRAPER-PRO

## 📋 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Accès au Dashboard](#accès-au-dashboard)
3. [Créer un job de scraping](#créer-un-job-de-scraping)
4. [Gérer vos jobs](#gérer-vos-jobs)
5. [Contacts validés](#contacts-validés)
6. [Synchronisation MailWizz](#synchronisation-mailwizz)
7. [Statistiques & Analytics](#statistiques--analytics)
8. [FAQ](#faq)

---

## 🎯 Vue d'ensemble

SCRAPER-PRO est un système automatisé de scraping multi-sources qui :

1. **Scrape** des contacts depuis 9 sources (Google, LinkedIn, Facebook, etc.)
2. **Valide** automatiquement les emails (DNS MX check)
3. **Catégorise** les contacts (avocat, blogueur, etc.)
4. **Route** vers le bon MailWizz (SOS-Expat ou Ulixai)
5. **Injecte** automatiquement dans les listes MailWizz
6. **Suit** toute la chaîne de traitement en temps réel

### Workflow automatique

```
📡 SCRAPING
   ↓
✅ VALIDATION (cron toutes les heures)
   ↓
🎯 CATÉGORISATION & ROUTING
   ↓
📧 INJECTION MAILWIZZ (cron toutes les heures)
   ↓
📬 CAMPAGNES EMAIL
```

---

## 🔐 Accès au Dashboard

### URL

```
http://VOTRE_IP_VPS:8501
```

Ou avec reverse proxy :
```
https://scraper.votredomaine.com
```

### Connexion

1. Ouvrir l'URL dans votre navigateur
2. Entrer le **mot de passe dashboard** (défini dans `.env`)
3. Cliquer "🔓 Connexion"

**Mot de passe oublié ?**
- Connectez-vous au VPS : `ssh scraper@VOTRE_IP`
- Voir le mot de passe : `cat ~/projets/scraper-pro/.env | grep DASHBOARD_PASSWORD`

---

## 📝 Créer un job de scraping

### 1. Accéder à l'onglet "Créer Job"

Dans la sidebar, cliquer sur **"📝 Créer Job"**

### 2. Choisir le type de source

**9 sources disponibles** :

| Source | Description | Mode requis | Coût |
|--------|-------------|-------------|------|
| 🌐 **URLs personnalisées** | Liste d'URLs à scraper | MODE 1 ou 2 | ✅ Gratuit |
| 🔍 **Google Search** | Recherche Google | MODE 1 | Proxies |
| 📍 **Google Maps** | Établissements locaux | MODE 1 | Proxies |
| 💼 **LinkedIn** | Profils professionnels | MODE 1 | Proxies + Residential |
| 📘 **Facebook** | Pages business | MODE 1 | Proxies + Residential |
| 💬 **Forums** | Expat.com, InternationsOrg | MODE 1 ou 2 | ✅ Gratuit |
| 📱 **Instagram** | Influenceurs, blogueurs | MODE 1 | Proxies + Residential |
| 🎥 **YouTube** | Chaînes voyage | MODE 1 ou 2 | ✅ Gratuit |

**💡 Recommandation** : Commencez par **URLs personnalisées** (plus simple et gratuit).

---

### 3. Exemple : Scraper 50 cabinets d'avocats

#### Configuration

1. **Source** : `🌐 URLs personnalisées`

2. **Méthode d'ajout** : `✍️ Coller URLs manuellement`

3. **Liste d'URLs** (une par ligne) :
   ```
   https://bangkoklawyers.com
   https://avocats-thailande.fr
   https://lexasia.com
   https://dfdl.com
   https://tilleke.com
   ... (45 autres URLs)
   ```

   Ou **upload fichier CSV/TXT** avec vos 50 URLs.

4. **Profondeur scraping** : `2`
   - 1 = Page accueil uniquement
   - 2 = Page accueil + pages liées (Contact, About, Team)
   - 3 = 2 niveaux de profondeur (plus long)

5. **Suivre liens externes** : `❌ Non` (recommandé)

6. **Catégorie** : `avocat`

7. **Plateforme destination** : `SOS-Expat`

8. **Pays** : `TH` (Thaïlande)

9. **Tags personnalisés** : `bangkok, scraping_fev_2026`

10. **Injection automatique MailWizz** : `✅ Oui`

#### Lancer le scraping

1. Cliquer **"🚀 Lancer le Scraping"**
2. Confirmer la création du job
3. ➡️ Redirection automatique vers "📊 Jobs Actifs"

---

### 4. Exemple : Recherche Google "lawyer bangkok"

#### Configuration

1. **Source** : `🔍 Google Search`

2. **Requête de recherche** : `lawyer bangkok`

3. **Nombre de résultats max** : `100`

4. **Profondeur scraping par site** : `2`

5. **Catégorie** : `avocat`

6. **Platform** : `SOS-Expat`

7. **Pays** : `TH`

8. **Tags** : `google_search, bangkok, 2026-02`

9. **Auto-injection MailWizz** : `✅ Oui`

10. **Lancer le Scraping** : `🚀`

**Note** : Requiert MODE 1 avec proxies et SerpAPI configuré.

---

### 5. Exemple : Blogueurs Instagram voyage

#### Configuration

1. **Source** : `📱 Instagram`

2. **Recherche par hashtag** : `#travelblogger` (ou liste de usernames)

3. **Nombre max de profils** : `100`

4. **Followers minimum** : `5000`

5. **Catégorie** : `influenceur`

6. **Platform** : `Ulixai`

7. **Pays** : `FR`

8. **Tags** : `instagram, travel, influencer`

9. **Auto-injection MailWizz** : `✅ Oui`

10. **Lancer** : `🚀`

**Note** : Requiert MODE 1 avec proxies résidentiels.

---

## 📊 Gérer vos jobs

### Onglet "Jobs Actifs"

Voir tous vos jobs en cours :

| Colonne | Description |
|---------|-------------|
| **ID** | Numéro unique du job |
| **Nom** | Nom auto-généré ou personnalisé |
| **Status** | `pending`, `running`, `completed`, `failed`, `paused` |
| **Progression** | % d'avancement (0-100%) |
| **Pages scrapées** | Nombre de pages visitées |
| **Contacts extraits** | Nombre de contacts trouvés |
| **Créé le** | Date de création |

#### Actions disponibles

**Boutons** :
- ▶️ **Resume** : Reprendre un job pausé ou échoué (checkpoint)
- ⏸️ **Pause** : Mettre en pause
- 🗑️ **Delete** : Supprimer le job (garde les contacts déjà extraits)

**États des jobs** :

| Badge | Signification |
|-------|---------------|
| 🟢 **Running** | En cours d'exécution |
| 🔵 **Pending** | En attente de démarrage |
| ⏸️ **Paused** | En pause |
| ✅ **Completed** | Terminé avec succès |
| ❌ **Failed** | Échec (erreur ou limite atteinte) |

---

### Fonction Resume (Reprise checkpoint)

**Cas d'usage** :
- Job interrompu (panne VPS, erreur réseau)
- Job pausé volontairement
- Job échoué à mi-parcours

**Comment utiliser** :

1. Cliquer **▶️ Resume** sur le job
2. Le job reprend exactement où il s'était arrêté
3. **Pas de doublons** : Les URLs/pages déjà scrapées sont ignorées

**Exemple** :
```
Job #42 : 500 URLs à scraper
- Scrapé : 250/500 URLs
- Échec réseau à l'URL 251
→ Cliquer Resume → Reprend à l'URL 251
```

---

## 📇 Contacts validés

### Onglet "Contacts Validés"

Voir tous vos contacts après validation :

#### Filtres

- **Platform** : SOS-Expat / Ulixai / Tous
- **Catégorie** : avocat, blogueur, influenceur, etc.
- **Status** : ready_for_mailwizz, sent_to_mailwizz, failed
- **Recherche** : Par email ou nom

#### Tableau contacts

| Colonne | Description |
|---------|-------------|
| **Email** | Email validé (DNS MX check OK) |
| **Nom** | Nom extrait du site |
| **Catégorie** | Catégorie auto-détectée |
| **Platform** | SOS-Expat ou Ulixai |
| **Liste MailWizz** | ID de la liste de destination |
| **Status** | État de synchronisation |
| **Date création** | Date d'extraction |

#### Export CSV

1. Appliquer vos filtres
2. Cliquer **📥 Export CSV**
3. Télécharger le fichier `contacts_export_YYYYMMDD_HHMMSS.csv`

**Format CSV** :
```csv
email,name,category,platform,mailwizz_list_id,status,created_at
avocat@example.com,Jean Dupont,avocat,sos-expat,1,sent_to_mailwizz,2026-02-14
```

---

## 📧 Synchronisation MailWizz

### Pipeline automatique

```
VALIDATION (cron hourly)
    ↓
validated_contacts (status: ready_for_mailwizz)
    ↓
SYNC MAILWIZZ (cron hourly, offset +30min)
    ↓
MailWizz Lists (SOS-Expat ou Ulixai)
```

### Onglet "MailWizz Sync"

#### Statistiques temps réel

- **Contacts prêts** : Nombre en attente d'envoi
- **Envoyés aujourd'hui** : Nombre synchronisés ce jour
- **Taux de succès** : % de réussite
- **Dernière sync** : Horodatage dernière exécution

#### Log de synchronisation

| Colonne | Description |
|---------|-------------|
| **Contact** | Email synchronisé |
| **Platform** | SOS-Expat ou Ulixai |
| **Liste** | ID liste MailWizz |
| **Status** | success / failed |
| **Date** | Date de tentative |
| **Erreur** | Message d'erreur (si échec) |

#### Retry automatique

- **Max retries** : 3 tentatives
- **Intervalle** : 1 heure entre chaque retry
- **Après 3 échecs** : Status passe à `failed` (vérifier logs)

#### Re-envoyer contacts failed

Si vous avez corrigé un problème (ex: clé API MailWizz invalide) :

1. Corriger `.env` avec la bonne clé
2. Redémarrer services : `docker-compose restart`
3. Dans le dashboard, onglet "MailWizz Sync"
4. Cliquer **🔄 Re-envoyer contacts failed**
5. Tous les contacts `failed` repassent en `ready_for_mailwizz`
6. Synchronisation au prochain cron (ou forcer manuellement)

---

## 📈 Statistiques & Analytics

### Onglet "📊 Statistiques"

#### Vue d'ensemble

- **Contacts scrapés (total)** : Depuis le début
- **Contacts validés (total)** : Emails valides
- **Taux de validation** : % emails valides sur total
- **Contacts envoyés MailWizz** : Déjà synchronisés
- **Jobs actifs** : En cours d'exécution

#### Graphiques

**1. Contacts par jour (30 derniers jours)**
- Courbe : Contacts scrapés par jour
- Tendance : Croissance ou décroissance

**2. Répartition par catégorie**
- Pie chart : % avocat, blogueur, influenceur, etc.
- Top 5 catégories

**3. Répartition par plateforme**
- Bar chart : SOS-Expat vs Ulixai
- Volumes comparés

**4. Taux de succès MailWizz**
- Donut chart : success vs failed
- % de réussite

**5. Performance par source**
- Table : Contacts extraits par type de source
- Google Search, LinkedIn, URLs custom, etc.

#### Export données analytics

1. Cliquer **📥 Export Analytics (PDF)**
2. Télécharger rapport complet avec graphiques

---

## ❓ FAQ

### Q1 : Combien de temps prend un job ?

**Ça dépend de** :
- **Nombre d'URLs/résultats** : 50 URLs = ~30-60 min
- **Profondeur** : Profondeur 2 = 2-3x plus long que profondeur 1
- **Source** : LinkedIn/Facebook plus lent (proxies, anti-bot)
- **Proxies** : Rotation peut ralentir (cooldown)

**Estimation** :
- **50 URLs (profondeur 2)** : 30-60 min
- **100 résultats Google** : 45-90 min
- **100 profils LinkedIn** : 1-2 heures
- **100 comptes Instagram** : 1.5-2.5 heures

### Q2 : Puis-je scraper plusieurs jobs en parallèle ?

**Oui** ! Le système gère plusieurs jobs simultanés.

**Limites** :
- **MODE 1** : Max 5 jobs parallèles (limite proxies)
- **MODE 2** : Max 3 jobs parallèles (limite CPU/IP)

**Recommandation** : Lancer 2-3 jobs max en parallèle pour performances optimales.

### Q3 : Comment éviter les doublons ?

**Triple protection anti-doublons** :

1. **URL normalization** : URLs identiques détectées
2. **Email unique** : Chaque email n'est injecté qu'une fois dans `validated_contacts`
3. **Cache Redis** : Hash du contenu, TTL 1h

**Résultat** : Pas de doublons dans MailWizz.

### Q4 : Que faire si un job échoue ?

**Diagnostiquer** :

1. Voir logs : Onglet "Jobs Actifs" → Colonne "Erreurs"
2. Consulter logs techniques :
   ```bash
   docker-compose logs scraper
   ```

**Erreurs courantes** :

| Erreur | Cause | Solution |
|--------|-------|----------|
| `Proxy blocked` | IP proxy bloquée | Attendre cooldown ou changer proxy |
| `DNS resolution failed` | Site inaccessible | Vérifier URL, retry plus tard |
| `Timeout` | Site trop lent | Augmenter timeout (settings) |
| `403 Forbidden` | Anti-bot détecté | Utiliser proxies résidentiels |
| `Rate limit exceeded` | Trop de requêtes | Réduire concurrence ou ajouter délai |

**Reprendre un job échoué** :

1. Corriger la cause (si possible)
2. Cliquer **▶️ Resume** sur le job
3. Le job reprend où il s'est arrêté

### Q5 : Puis-je personnaliser les catégories ?

**Oui**, éditez `config/categorizer.py` :

```python
CATEGORY_RULES = {
    "ma_categorie_custom": {
        "keywords": ["mot1", "mot2", "mot3"],
        "sources": ["google_search", "custom_urls"]
    }
}
```

**Puis** ajoutez la catégorie dans `config/mailwizz_routing.json` :

```json
{
  "platforms": {
    "sos-expat": {
      "lists": {
        "ma_categorie_custom": {
          "list_id": 20,
          "list_name": "Ma Nouvelle Catégorie",
          "auto_tags": ["custom", "test"],
          "template_default": "template_custom"
        }
      }
    }
  }
}
```

**Redémarrer** :
```bash
docker-compose restart scraper
```

### Q6 : Comment ajouter plus de proxies (MODE 1) ?

**1. Acheter proxies** :
- Oxylabs : https://oxylabs.io
- SmartProxy : https://smartproxy.com
- BrightData : https://brightdata.com

**2. Éditer `.env`** :
```bash
OXYLABS_USER=nouveau_user
OXYLABS_PASS=nouveau_pass
```

**3. Redémarrer** :
```bash
docker-compose restart
```

Les nouveaux proxies seront automatiquement utilisés.

### Q7 : Les contacts sont validés mais pas envoyés à MailWizz ?

**Vérifier** :

1. **Clés API MailWizz** valides :
   ```bash
   cat .env | grep MAILWIZZ
   ```

2. **Listes MailWizz** existent :
   - Connectez-vous à MailWizz
   - Vérifiez que les IDs de listes correspondent à `config/mailwizz_routing.json`

3. **Cron job actif** :
   ```bash
   docker exec scraper_app crontab -l
   ```
   Doit afficher :
   ```
   30 * * * * cd /app && python -m scraper.jobs.sync_to_mailwizz
   ```

4. **Forcer sync manuelle** :
   ```bash
   docker exec scraper_app python -m scraper.jobs.sync_to_mailwizz
   ```

5. **Voir logs** :
   ```bash
   docker-compose logs scraper | grep mailwizz
   ```

### Q8 : Puis-je scraper des sites en dehors de la France/Thaïlande ?

**Absolument** ! Le système est international.

**Configurez** :
- **Pays** : Code ISO 2 lettres (US, ES, DE, IT, MX, etc.)
- **Langue** : Mots-clés dans la langue cible
- **Proxies** : Choisir proxies du pays cible (si MODE 1)

**Exemple : Scraper avocats en Espagne** :
- Source : Google Search
- Query : `abogado madrid`
- Pays : `ES`
- Catégorie : avocat
- Platform : SOS-Expat

### Q9 : Comment changer le mot de passe dashboard ?

**1. Éditer `.env`** :
```bash
nano .env
```

Modifier :
```bash
DASHBOARD_PASSWORD=NouveauMotDePasse123!
```

**2. Redémarrer dashboard** :
```bash
docker-compose restart dashboard
```

**3. Reconnexion** avec le nouveau mot de passe.

### Q10 : Le système peut-il gérer 100,000 contacts ?

**Oui** ! SCRAPER-PRO est conçu pour la scalabilité :

- **PostgreSQL** : Optimisé pour millions de lignes
- **Index** : Requêtes rapides même avec 1M+ contacts
- **Pagination** : Dashboard charge par batch de 100
- **Backup** : Script inclus pour sauvegardes régulières

**Performance** :
- 10K contacts : ⚡ Instantané
- 100K contacts : ⚡ Rapide (< 1 sec requêtes)
- 1M+ contacts : 🚀 Performant avec tuning PostgreSQL

**Recommandations pour gros volumes** :
1. Augmenter RAM VPS (16 GB+)
2. Activer autovacuum PostgreSQL
3. Partitionner tables par mois (si 10M+ lignes)

---

## 📞 Support

**Problèmes techniques** :
- 📧 Email : support@sos-expat.com
- 📝 GitHub Issues : https://github.com/votre-repo/scraper-pro/issues

**Documentation** :
- 🚀 Déploiement : `DEPLOYMENT.md`
- 🔧 API Docs : `http://VOTRE_IP:8000/docs`

---

**Version** : 1.0.0
**Date** : Février 2026
**Auteur** : Williams - SOS-Expat.com / Ulixai.com

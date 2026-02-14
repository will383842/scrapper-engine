# 🚨 GAPS DE PRODUCTION - Scraper-Pro

## ❌ CE QUI MANQUE POUR ÊTRE VRAIMENT PRODUCTION-READY

---

## 1️⃣ INFRASTRUCTURE À ACHETER (OBLIGATOIRE)

### A. Serveur VPS/VDS (CRITIQUE - 0% fait)

**Statut** : ❌ **NON ACHETÉ - BLOQUANT**

**Pourquoi obligatoire ?**
- Le système tourne actuellement uniquement en LOCAL
- Docker nécessite un serveur 24/7 pour tourner en continu
- Impossible de faire du scraping continu sans serveur dédié

**Ce qu'il faut acheter :**

| Provider | Plan | Prix/mois | Specs | Recommandation |
|----------|------|-----------|-------|----------------|
| **Hetzner** | CPX31 | ~12€ | 4 vCPU, 8GB RAM, 160GB SSD | ⭐ **MEILLEUR RAPPORT QUALITÉ/PRIX** |
| **Contabo** | VPS M | ~8€ | 4 vCPU, 8GB RAM, 200GB SSD | ✅ Économique |
| **DigitalOcean** | CPU-Optimized 8GB | ~48$ | 4 vCPU, 8GB RAM, 100GB SSD | ✅ Fiable mais cher |
| **OVH** | VPS Elite | ~14€ | 4 vCPU, 8GB RAM, 160GB NVMe | ✅ Bon support |
| **AWS Lightsail** | 8GB | ~40$ | 2 vCPU, 8GB RAM, 160GB SSD | ⚠️ Cher |

**Recommandation finale** : **Hetzner CPX31** (12€/mois)
- Excellent réseau (1 Gbit/s)
- 20 TB de trafic inclus
- Datacenter Allemagne (proche de la France)
- Fiabilité excellente
- Snapshots gratuits

**Actions requises :**
```bash
# 1. Acheter le VPS
# 2. Configurer SSH
# 3. Installer Docker + Docker Compose
# 4. Cloner le repo
# 5. Configurer .env
# 6. Déployer : docker-compose up -d
```

**Coût annuel** : ~150€/an

---

### B. Proxies Rotatifs (CRITIQUE - 0% actifs)

**Statut** : ❌ **NON ACHETÉS - BLOQUANT POUR GOOGLE**

**Pourquoi OBLIGATOIRES ?**
- Google/Maps bloquent les IPs après 10-50 requêtes
- Sans proxies, blacklist garantie en 5 minutes
- Les proxies résidentiels imitent de vrais utilisateurs

**Le code est prêt, mais AUCUN proxy actif !**

**Providers recommandés :**

#### Option 1 : **Oxylabs** (Premium - Recommandé)
- **Plan** : Residential Proxies Starter
- **Prix** : ~300€/mois (50GB trafic)
- **Pool** : 100M+ IPs résidentielles
- **Rotation** : Automatique par requête
- **Success rate** : 99.9%
- **Support** : 24/7
- ⭐ **MEILLEUR POUR GOOGLE**
- 🔗 Code déjà intégré dans `config/proxy_config.json`

#### Option 2 : **Bright Data** (Ex-Luminati)
- **Plan** : Pay-as-you-go
- **Prix** : ~500€/mois (40GB trafic)
- **Pool** : 72M+ IPs
- **Qualité** : Excellente
- ⚠️ Plus cher mais très fiable

#### Option 3 : **SmartProxy** (Budget)
- **Plan** : Residential 8GB
- **Prix** : ~75€/mois
- **Pool** : 40M+ IPs
- **Qualité** : Correcte pour du scraping léger
- ⚠️ Success rate ~95% (moins bon que Oxylabs)

#### Option 4 : **Proxies GRATUITS** (⚠️ NON RECOMMANDÉ)
- **Prix** : 0€
- **Qualité** : 💩 TRÈS MAUVAISE
- **Problèmes** :
  - 90% ne marchent pas
  - Blacklistés par Google
  - Lents (>10s par requête)
  - Risque de fuite d'IP
- ❌ **NE PAS UTILISER EN PRODUCTION**

**Recommandation finale** : **Oxylabs Residential Proxies**
- 300€/mois pour 50GB
- OU 1500€/an (économie de 15%)
- Inclus : rotation auto, sticky sessions, geo-targeting

**Coût annuel** : ~3600€/an (ou 1500€ si paiement annuel)

**Configuration requise :**
```bash
# Dans .env
PROXY_PROVIDER=oxylabs
PROXY_USER=customer-YOUR_USERNAME
PROXY_PASS=YOUR_PASSWORD

# Test de connexion
curl -x pr.oxylabs.io:7777 -U "customer-YOUR_USERNAME:YOUR_PASSWORD" https://ip-api.com/json
```

**Alternative économique** :
- Commencer avec SmartProxy 8GB (75€/mois)
- Upgrader vers Oxylabs quand le volume augmente

---

### C. SerpAPI (Optionnel mais recommandé)

**Statut** : ⚠️ **NON ACHETÉ - FORTEMENT RECOMMANDÉ**

**Pourquoi utile ?**
- Fallback quand Google détecte un CAPTCHA
- API officielle de Google Search
- Pas de risque de blacklist
- Parsing déjà fait

**Plan recommandé** : **SerpAPI Starter**
- **Prix** : ~50$/mois (5000 recherches)
- **Inclus** : Google Search, Google Maps, Shopping, News
- **Rate limit** : 1 req/s
- 🔗 Code déjà intégré dans `scraper/integrations/serpapi_client.py`

**Configuration :**
```bash
# Dans .env
SERPAPI_KEY=your_serpapi_key_here
```

**Coût annuel** : ~600$/an

---

## 2️⃣ FONCTIONNALITÉS MANQUANTES (CODE À ÉCRIRE)

### A. Détection de Blacklist (CRITIQUE - 0% implémenté)

**Statut** : ❌ **NON IMPLÉMENTÉ - CRITIQUE**

**Problème actuel :**
- Le système ne détecte PAS si une IP/proxy est blacklisté
- Continue à envoyer des requêtes même si bloqué
- Gaspille des crédits proxy
- Pas d'alerte quand blacklisté

**Ce qui doit être implémenté :**

```python
# scraper/utils/blacklist_detector.py (À CRÉER)

class BlacklistDetector:
    """Détecte si on est blacklisté par Google/sites."""

    BLACKLIST_INDICATORS = [
        "captcha",
        "unusual traffic",
        "automated queries",
        "robot",
        "403 forbidden",
        "429 too many requests",
        "sorry, but your computer",
        "unusual activity",
        "recaptcha",
    ]

    def is_blacklisted(self, response: Response) -> bool:
        """Vérifie si la réponse indique un blacklist."""
        # Status codes suspects
        if response.status_code in [403, 429, 503]:
            return True

        # Mots-clés dans le HTML
        html_lower = response.text.lower()
        for indicator in self.BLACKLIST_INDICATORS:
            if indicator in html_lower:
                logger.warning(f"Blacklist detected: {indicator}")
                return True

        # Redirection vers CAPTCHA
        if "google.com/sorry" in response.url:
            return True

        return False

    def trigger_fallback(self, proxy_url: str):
        """Actions quand blacklist détectée."""
        # 1. Marquer le proxy comme blacklisté
        self.mark_proxy_blacklisted(proxy_url)

        # 2. Passer au proxy suivant
        self.rotate_proxy()

        # 3. Fallback sur SerpAPI si disponible
        if os.getenv("SERPAPI_KEY"):
            self.use_serpapi_fallback()

        # 4. Alerte admin
        self.send_alert("Blacklist detected, switched to fallback")
```

**Intégration dans les spiders :**
```python
# Dans parse_search_results()

detector = BlacklistDetector()

if detector.is_blacklisted(response):
    logger.error("🚨 BLACKLISTED! Switching to fallback...")
    detector.trigger_fallback(response.meta.get('proxy'))
    # Relancer la requête avec nouveau proxy
    yield scrapy.Request(
        response.url,
        callback=self.parse_search_results,
        dont_filter=True,
        meta={'retry': True}
    )
    return
```

**Effort** : 4-6 heures de dev + tests

---

### B. Dashboard de Santé des Proxies (MANQUANT - 0% implémenté)

**Statut** : ❌ **NON IMPLÉMENTÉ - IMPORTANT**

**Problème actuel :**
- Aucune visibilité sur la santé des proxies
- Pas de stats de success rate par proxy
- Impossible de savoir quel proxy est blacklisté

**Ce qui doit être créé :**

**1. Table de tracking des proxies**
```sql
-- Déjà existe dans db/init.sql : proxy_stats
-- Mais pas utilisée !

SELECT proxy_url, success_rate, consecutive_failures, status
FROM proxy_stats
WHERE status = 'active'
ORDER BY success_rate DESC;
```

**2. Middleware de tracking**
```python
# scraper/utils/middlewares.py (À AMÉLIORER)

class ProxyMiddleware:
    def process_response(self, request, response, spider):
        proxy = request.meta.get('proxy')

        # Enregistrer la statistique
        if response.status_code == 200:
            self.record_proxy_success(proxy)
        else:
            self.record_proxy_failure(proxy)

        # Auto-blacklist si trop d'échecs
        if self.get_failure_rate(proxy) > 0.5:
            self.blacklist_proxy(proxy)
            logger.warning(f"Proxy auto-blacklisted: {proxy}")
```

**3. Onglet Dashboard Streamlit**
```python
# dashboard/app.py - Nouvel onglet "Proxies"

with tab_proxies:
    st.header("Proxy Health Monitor")

    proxies = query_df("""
        SELECT proxy_url, proxy_type, provider,
               total_requests, successful_requests, failed_requests,
               success_rate, avg_response_ms, status, last_used_at
        FROM proxy_stats
        ORDER BY success_rate DESC
    """)

    # Métriques clés
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active Proxies", len([p for p in proxies if p['status'] == 'active']))
    col2.metric("Blacklisted", len([p for p in proxies if p['status'] == 'blacklisted']))
    col3.metric("Avg Success Rate", f"{proxies['success_rate'].mean():.1f}%")
    col4.metric("Avg Response", f"{proxies['avg_response_ms'].mean():.0f}ms")

    # Table
    st.dataframe(proxies)
```

**Effort** : 6-8 heures de dev

---

### C. Scraping d'Annuaires (MANQUANT - 0% implémenté)

**Statut** : ❌ **NON IMPLÉMENTÉ - FONCTIONNALITÉ MANQUANTE**

**Problème actuel :**
- Le système scrappe seulement :
  - ✅ Google Search
  - ✅ Google Maps
  - ✅ URLs personnalisées
  - ✅ Blogs
- **MAIS PAS d'annuaires professionnels !**

**Annuaires importants à ajouter :**

1. **Pages Jaunes** (pagesjaunes.fr)
2. **118712** (annuaire inversé)
3. **Yelp France**
4. **TripAdvisor** (restaurants, hôtels)
5. **Justacote** (professionnels)
6. **LinkedIn** (⚠️ difficile, nécessite authentification)

**Ce qui doit être créé :**

```python
# scraper/spiders/pagesjaunes_spider.py (À CRÉER)

class PagesJaunesSpider(scrapy.Spider):
    name = "pagesjaunes"

    def __init__(self, query="avocat", location="paris", max_results=100, **kwargs):
        super().__init__(**kwargs)
        self.query = query
        self.location = location
        self.max_results = int(max_results)

    def start_requests(self):
        # URL Pages Jaunes
        url = f"https://www.pagesjaunes.fr/annuaire/chercherlespros?quoiqui={self.query}&ou={self.location}&proximite=0"
        yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        # Extraire les fiches
        for fiche in response.css('.bi-bloc'):
            item = ContactItem()
            item['name'] = fiche.css('.denomination-links::text').get()
            item['phone'] = fiche.css('.numero::text').get()
            item['address'] = fiche.css('.adresse::text').get()
            item['website'] = fiche.css('.bi-lien-site::attr(href)').get()
            item['source_type'] = 'pagesjaunes'
            item['source_url'] = response.url
            yield item

        # Pagination
        next_page = response.css('.pagination-next::attr(href)').get()
        if next_page and self.results_count < self.max_results:
            yield response.follow(next_page, callback=self.parse)
```

**Effort par annuaire** : 4-6 heures
**Total pour 5 annuaires** : 20-30 heures

---

### D. Auto-Throttling Intelligent (BASIQUE - 30% implémenté)

**Statut** : ⚠️ **PARTIELLEMENT IMPLÉMENTÉ - À AMÉLIORER**

**Ce qui existe déjà :**
```python
# settings.py
DOWNLOAD_DELAY = 2.0  # Délai fixe entre requêtes
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
```

**Problème :**
- Le throttling est **STATIQUE**
- Pas d'adaptation selon le taux d'erreur
- Pas de ralentissement automatique si blacklist détectée

**Ce qui doit être ajouté :**

```python
# scraper/utils/smart_throttle.py (À CRÉER)

class SmartThrottleExtension:
    """Auto-ajuste la vitesse selon le taux d'erreur."""

    def __init__(self):
        self.error_rate_window = deque(maxlen=100)  # 100 dernières requêtes
        self.current_delay = 2.0  # Début à 2s

    def adjust_delay(self):
        """Ajuste le délai selon le taux d'erreur."""
        error_rate = sum(self.error_rate_window) / len(self.error_rate_window)

        if error_rate > 0.3:  # >30% d'erreurs
            # RALENTIR agressivement
            self.current_delay *= 2
            logger.warning(f"⚠️ High error rate ({error_rate:.0%}), slowing down to {self.current_delay}s")

        elif error_rate > 0.1:  # >10% d'erreurs
            # RALENTIR modérément
            self.current_delay *= 1.5
            logger.info(f"Moderate errors ({error_rate:.0%}), delay → {self.current_delay}s")

        elif error_rate < 0.05:  # <5% d'erreurs
            # ACCÉLÉRER progressivement
            self.current_delay = max(1.0, self.current_delay * 0.9)
            logger.info(f"Low errors ({error_rate:.0%}), speeding up to {self.current_delay}s")

        # Limites
        self.current_delay = max(1.0, min(60.0, self.current_delay))

        return self.current_delay
```

**Intégration dans Scrapy :**
```python
# settings.py
EXTENSIONS = {
    'scraper.utils.smart_throttle.SmartThrottleExtension': 500,
}
```

**Effort** : 3-4 heures

---

### E. Vérification du Système de Checkpoint (EXISTE - À TESTER)

**Statut** : ✅ **CODE EXISTE mais NON TESTÉ EN PRODUCTION**

**Ce qui existe :**
```python
# scraper/utils/checkpoint.py
def save_checkpoint(job_id: int, data: dict):
    """Sauvegarde un checkpoint dans scraping_jobs.checkpoint_data."""

def load_checkpoint(job_id: int) -> dict:
    """Charge le checkpoint d'un job."""

# scraper/spiders/google_search_spider.py
def start_requests(self):
    start_offset = 0
    if self.resume and self.job_id:
        checkpoint = load_checkpoint(int(self.job_id))
        if checkpoint:
            start_offset = checkpoint.get("last_page", 0)
            logger.info(f"Resuming from page {start_offset}")
```

**Test à faire :**
```bash
# 1. Lancer un job Google Search (max 100 résultats)
curl -X POST http://localhost:8000/api/v1/scraping/jobs \
  -H "Content-Type: application/json" \
  -d '{"source_type":"google_search","name":"Test Checkpoint","config":{"query":"avocat paris","max_results":100}}'

# 2. Attendre qu'il scrape 50 résultats
# 3. Arrêter manuellement : docker-compose stop scraper
# 4. Vérifier le checkpoint dans la DB
docker-compose exec postgres psql -U scraper_admin -d scraper_db -c "SELECT id, checkpoint_data FROM scraping_jobs WHERE id = 1;"

# 5. Reprendre le job
curl -X POST http://localhost:8000/api/v1/scraping/jobs/1/resume

# 6. Vérifier qu'il reprend à partir de la page 50 (pas de 0)
```

**Si le test échoue** : Corriger le code de checkpoint

**Effort** : 2 heures de tests

---

## 3️⃣ SYSTÈME EN CONTINU (PARTIELLEMENT FAIT - 60%)

### A. Cron Jobs Automatiques (✅ IMPLÉMENTÉ)

**Statut** : ✅ **CODE EXISTE - MAIS INACTIF SANS VPS**

**Ce qui existe :**
```bash
# crontab (dans le container scraper)
0 * * * * cd /app && python -m scraper.jobs.process_contacts  # Validation toutes les heures
30 * * * * cd /app && python -m scraper.jobs.sync_to_mailwizz  # Sync MailWizz +30min
```

**Problème :**
- ❌ Ces crons tournent uniquement SI le serveur VPS tourne 24/7
- ❌ Actuellement INACTIFS (pas de serveur)

**Solution :**
- Déployer sur VPS → crons s'activent automatiquement

---

### B. Contrôle de Cadence (⚠️ BASIQUE - À AMÉLIORER)

**Statut** : ⚠️ **PARTIELLEMENT IMPLÉMENTÉ**

**Ce qui existe :**
```python
# settings.py
DOWNLOAD_DELAY = 2.0  # 2 secondes entre requêtes
CONCURRENT_REQUESTS = 8  # 8 requêtes simultanées max
CONCURRENT_REQUESTS_PER_DOMAIN = 2  # 2 requêtes/domaine
AUTOTHROTTLE_ENABLED = True
```

**Ce qui manque :**
- ❌ Pas d'ajustement dynamique selon les erreurs
- ❌ Pas de "mode ralenti" automatique si blacklist détectée
- ❌ Pas de limites par heure/jour

**À implémenter :**
```python
# Nouvelle table : scraping_quotas
CREATE TABLE scraping_quotas (
    id SERIAL PRIMARY KEY,
    source_type VARCHAR(50),
    requests_per_hour INTEGER DEFAULT 500,
    requests_today INTEGER DEFAULT 0,
    last_reset TIMESTAMPTZ DEFAULT NOW(),
    throttle_mode VARCHAR(20) DEFAULT 'normal'  -- normal, slow, paused
);

# Middleware de contrôle
class QuotaMiddleware:
    def process_request(self, request, spider):
        quota = get_daily_quota(spider.source_type)

        if quota.requests_today >= quota.requests_per_hour * 24:
            raise IgnoreRequest("Daily quota exceeded")

        if quota.throttle_mode == 'slow':
            time.sleep(5)  # Ralentir à 5s entre requêtes
        elif quota.throttle_mode == 'paused':
            raise IgnoreRequest("Scraping paused")
```

**Effort** : 4-6 heures

---

## 4️⃣ RÉCAPITULATIF DES GAPS

### Bloquants (CRITIQUE - système non fonctionnel)

| Gap | Statut | Impact | Coût | Effort | Priorité |
|-----|--------|--------|------|--------|----------|
| **VPS/VDS** | ❌ 0% | 🔴 BLOQUANT | 12€/mois | 2h setup | P0 |
| **Proxies** | ❌ 0% | 🔴 BLOQUANT (Google) | 300€/mois | 1h config | P0 |
| **Détection Blacklist** | ❌ 0% | 🔴 CRITIQUE | 0€ | 6h dev | P0 |

### Importants (système fonctionne mais incomplet)

| Gap | Statut | Impact | Coût | Effort | Priorité |
|-----|--------|--------|------|--------|----------|
| **SerpAPI** | ❌ 0% | 🟠 IMPORTANT | 50$/mois | 0h (déjà intégré) | P1 |
| **Dashboard Proxies** | ❌ 0% | 🟠 IMPORTANT | 0€ | 8h dev | P1 |
| **Auto-Throttling** | ⚠️ 30% | 🟠 IMPORTANT | 0€ | 4h dev | P1 |
| **Annuaires** | ❌ 0% | 🟡 SOUHAITABLE | 0€ | 30h dev | P2 |
| **Test Checkpoints** | ⚠️ 80% | 🟡 SOUHAITABLE | 0€ | 2h tests | P2 |

---

## 💰 BUDGET TOTAL NÉCESSAIRE

### Coûts d'Infrastructure (OBLIGATOIRES)

| Item | Provider | Prix/mois | Prix/an | Note |
|------|----------|-----------|---------|------|
| **VPS** | Hetzner CPX31 | 12€ | 144€ | OBLIGATOIRE |
| **Proxies** | Oxylabs Residential | 300€ | 3600€ | CRITIQUE pour Google |
| **SerpAPI** | Starter Plan | ~50€ | 600€ | Fallback recommandé |
| **Domaine + SSL** | Namecheap + Let's Encrypt | 1€ | 12€ | Let's Encrypt gratuit |
| **Backups S3** | AWS S3 Standard-IA | ~5€ | 60€ | Optionnel (backup local OK) |
| **TOTAL** | | **~368€/mois** | **~4416€/an** | |

### Alternative Budget Réduit

| Item | Provider | Prix/mois | Prix/an | Note |
|------|----------|-----------|---------|------|
| **VPS** | Contabo VPS M | 8€ | 96€ | Moins cher |
| **Proxies** | SmartProxy 8GB | 75€ | 900€ | Budget mais moins fiable |
| **SerpAPI** | - | 0€ | 0€ | Skipper au début |
| **Domaine** | Namecheap | 1€ | 12€ | |
| **TOTAL** | | **~84€/mois** | **~1008€/an** | |

---

## ⏱️ TEMPS DE DÉVELOPPEMENT MANQUANT

| Tâche | Effort | Priorité |
|-------|--------|----------|
| Détection Blacklist | 6h | P0 |
| Dashboard Proxies | 8h | P1 |
| Auto-Throttling | 4h | P1 |
| Test Checkpoints | 2h | P2 |
| 5 Annuaires | 30h | P2 |
| **TOTAL P0-P1** | **20h** | |
| **TOTAL P0-P2** | **50h** | |

---

## 🚀 PLAN D'ACTION RECOMMANDÉ

### Phase 1 : Infrastructure (Semaine 1)

```bash
# Jour 1 : Acheter infrastructure
- Acheter VPS Hetzner CPX31 (12€/mois)
- Acheter compte Oxylabs (300€/mois)
- Optionnel : SerpAPI Starter (50$/mois)

# Jour 2-3 : Setup VPS
- Configurer serveur (Docker, SSL)
- Déployer scraper-pro
- Configurer proxies dans .env

# Jour 4-5 : Tests infrastructure
- Test scraping Google avec proxies
- Test rotation des proxies
- Test checkpoint/resume

Coût : ~368€ (premier mois)
Temps : 16h
```

### Phase 2 : Code Critique (Semaine 2)

```bash
# Jour 1-2 : Détection Blacklist (6h)
- Implémenter BlacklistDetector
- Intégrer dans spiders
- Tests avec vraies requêtes Google

# Jour 3-4 : Dashboard Proxies (8h)
- Créer onglet Proxies dans dashboard
- Tracking stats par proxy
- Auto-blacklist si failure rate > 50%

# Jour 5 : Auto-Throttling (4h)
- Implémenter SmartThrottleExtension
- Tests de ralentissement automatique

# Jour 6 : Tests Checkpoints (2h)
- Test resume après crash
- Vérifier que ça ne recommence PAS de 0

Coût : 0€ (développement)
Temps : 20h
```

### Phase 3 : Fonctionnalités (Semaines 3-4)

```bash
# Optionnel : Annuaires
- Spider Pages Jaunes (6h)
- Spider Yelp (6h)
- Spider 118712 (6h)
- Spider Justacote (6h)
- Spider TripAdvisor (6h)

Coût : 0€
Temps : 30h
```

---

## ✅ CHECKLIST FINALE PRODUCTION-READY

### Infrastructure (CRITIQUE)
- [ ] VPS/VDS acheté et configuré
- [ ] Proxies résidentiels actifs (Oxylabs/SmartProxy)
- [ ] DNS configuré (scraper.votre-domaine.com)
- [ ] SSL/TLS actif (Let's Encrypt)
- [ ] Backup automatique configuré

### Code Critique
- [ ] Détection blacklist implémentée
- [ ] Dashboard proxies fonctionnel
- [ ] Auto-throttling intelligent actif
- [ ] Checkpoints testés et validés
- [ ] SerpAPI fallback configuré (optionnel)

### Monitoring
- [x] Prometheus + Grafana configurés
- [x] Alertes blacklist configurées
- [ ] Dashboard proxies avec alertes
- [x] Logs centralisés (Loki)

### Tests End-to-End
- [ ] Test scraping Google (100 résultats) avec proxies
- [ ] Test rotation automatique des proxies
- [ ] Test détection + récupération blacklist
- [ ] Test checkpoint/resume après crash
- [ ] Test cron jobs automatiques

---

## 💡 RECOMMANDATION FINALE

**Pour être VRAIMENT production-ready :**

1. **ACHETER (obligatoire)** :
   - ✅ VPS Hetzner CPX31 (12€/mois)
   - ✅ Oxylabs Residential Proxies (300€/mois)
   - ⚠️ SerpAPI (optionnel, 50$/mois)

2. **DÉVELOPPER (20h critiques)** :
   - ✅ Détection blacklist (6h)
   - ✅ Dashboard proxies (8h)
   - ✅ Auto-throttling (4h)
   - ✅ Tests checkpoints (2h)

3. **BUDGET TOTAL** :
   - **Minimum** : 84€/mois (VPS + SmartProxy)
   - **Recommandé** : 368€/mois (VPS + Oxylabs + SerpAPI)
   - **Annuel** : 1000€-4400€/an

**Sans VPS + Proxies = système NON FONCTIONNEL en production** ❌

---

Voulez-vous que je vous aide à implémenter ces fonctionnalités manquantes ?

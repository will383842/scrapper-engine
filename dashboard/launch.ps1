# ═══════════════════════════════════════════════════════════
# Scraper-Pro Dashboard - Launcher Script (PowerShell)
# ═══════════════════════════════════════════════════════════
#
# Usage:
#   .\dashboard\launch.ps1
#
# Options:
#   -Port 8502        # Custom port (default: 8501)
#   -Dev              # Development mode (auto-reload)
#   -Test             # Run tests before launch
#   -Production       # Production mode (no debug)
#
# ═══════════════════════════════════════════════════════════

param(
    [int]$Port = 8501,
    [switch]$Dev = $false,
    [switch]$Test = $false,
    [switch]$Production = $false
)

# ─── Colors ───
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Error { Write-Host $args -ForegroundColor Red }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Info { Write-Host $args -ForegroundColor Cyan }

# ─── Header ───
Clear-Host
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                        ║" -ForegroundColor Cyan
Write-Host "║   🚀 SCRAPER-PRO DASHBOARD LAUNCHER                   ║" -ForegroundColor Cyan
Write-Host "║                                                        ║" -ForegroundColor Cyan
Write-Host "║   Version: 2.0.0 FINAL                                ║" -ForegroundColor Cyan
Write-Host "║   File: app_final.py                                  ║" -ForegroundColor Cyan
Write-Host "║                                                        ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ─── Check Python ───
Write-Info "🔍 Vérification de Python..."
try {
    $pythonVersion = python --version 2>&1
    Write-Success "✅ Python trouvé: $pythonVersion"
} catch {
    Write-Error "❌ Python n'est pas installé ou n'est pas dans le PATH"
    Write-Error "   Téléchargez Python depuis: https://www.python.org/downloads/"
    exit 1
}

# ─── Check Virtual Environment ───
Write-Info "🔍 Vérification de l'environnement virtuel..."
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Success "✅ Virtual environment trouvé"
    Write-Info "🔄 Activation de l'environnement virtuel..."
    & "venv\Scripts\Activate.ps1"
} else {
    Write-Warning "⚠️  Pas d'environnement virtuel détecté"
    Write-Info "📦 Création d'un nouvel environnement virtuel..."
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Erreur lors de la création de l'environnement virtuel"
        exit 1
    }
    Write-Success "✅ Environnement virtuel créé"
    Write-Info "🔄 Activation de l'environnement virtuel..."
    & "venv\Scripts\Activate.ps1"
}

# ─── Check Dependencies ───
Write-Info "🔍 Vérification des dépendances..."
$packagesInstalled = $true

$requiredPackages = @("streamlit", "sqlalchemy", "requests", "psycopg2-binary", "python-dotenv")
foreach ($package in $requiredPackages) {
    $installed = pip show $package 2>$null
    if ($null -eq $installed) {
        Write-Warning "⚠️  Package manquant: $package"
        $packagesInstalled = $false
    }
}

if (-not $packagesInstalled) {
    Write-Info "📦 Installation des dépendances..."
    pip install -r dashboard\requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Erreur lors de l'installation des dépendances"
        exit 1
    }
    Write-Success "✅ Dépendances installées"
} else {
    Write-Success "✅ Toutes les dépendances sont installées"
}

# ─── Check .env File ───
Write-Info "🔍 Vérification du fichier .env..."
if (Test-Path ".env") {
    Write-Success "✅ Fichier .env trouvé"

    # Check critical variables
    $envContent = Get-Content .env -Raw
    $criticalVars = @("DASHBOARD_PASSWORD", "API_HMAC_SECRET", "POSTGRES_PASSWORD")
    $missingVars = @()

    foreach ($var in $criticalVars) {
        if ($envContent -notmatch "$var=") {
            $missingVars += $var
        }
    }

    if ($missingVars.Count -gt 0) {
        Write-Warning "⚠️  Variables critiques manquantes dans .env:"
        foreach ($var in $missingVars) {
            Write-Warning "   - $var"
        }
        Write-Info "   Consultez le fichier QUICKSTART.md pour la configuration"
    } else {
        Write-Success "✅ Toutes les variables critiques sont définies"
    }
} else {
    Write-Warning "⚠️  Fichier .env non trouvé"
    Write-Info "📝 Création d'un fichier .env template..."

    $envTemplate = @"
# ═══ OBLIGATOIRES ═══
DASHBOARD_PASSWORD=changeme
API_HMAC_SECRET=changeme_generate_with_openssl_rand_hex_32

# ═══ DATABASE ═══
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=scraper_db
POSTGRES_USER=scraper_admin
POSTGRES_PASSWORD=changeme

# ═══ API ═══
SCRAPER_API_URL=http://localhost:8000

# ═══ REDIS ═══
REDIS_HOST=localhost
REDIS_PORT=6379

# ═══ MODE ═══
SCRAPING_MODE=urls_only
"@

    $envTemplate | Out-File -FilePath ".env" -Encoding UTF8
    Write-Success "✅ Fichier .env créé"
    Write-Warning "⚠️  IMPORTANT: Éditez .env avec vos vraies valeurs avant de continuer!"
    Write-Info "   Appuyez sur Entrée pour ouvrir .env dans le bloc-notes..."
    Read-Host
    notepad .env
    Write-Info "   Sauvegardez et fermez le bloc-notes, puis relancez ce script"
    exit 0
}

# ─── Check Dashboard File ───
Write-Info "🔍 Vérification du fichier dashboard..."
if (Test-Path "dashboard\app_final.py") {
    Write-Success "✅ dashboard\app_final.py trouvé"
} else {
    Write-Error "❌ dashboard\app_final.py non trouvé!"
    Write-Error "   Assurez-vous d'être dans le répertoire racine du projet"
    exit 1
}

# ─── Run Tests ───
if ($Test) {
    Write-Info "🧪 Exécution des tests..."
    Write-Host ""
    python dashboard\test_dashboard.py
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Les tests ont échoué"
        Write-Warning "   Corrigez les erreurs avant de lancer le dashboard"
        exit 1
    }
    Write-Success "✅ Tous les tests sont passés"
    Write-Host ""
}

# ─── Launch Dashboard ───
Write-Info "🚀 Lancement du dashboard..."
Write-Host ""
Write-Success "═══════════════════════════════════════════════════════"
Write-Success "  Dashboard disponible sur:"
Write-Success "  http://localhost:$Port"
Write-Success "═══════════════════════════════════════════════════════"
Write-Host ""
Write-Info "  Mode: $(if ($Production) { 'Production' } elseif ($Dev) { 'Development' } else { 'Standard' })"
Write-Info "  Port: $Port"
Write-Host ""
Write-Warning "  Appuyez sur Ctrl+C pour arrêter le dashboard"
Write-Host ""

# Build Streamlit command
$streamlitCmd = "streamlit run dashboard\app_final.py --server.port=$Port --server.address=0.0.0.0"

if ($Production) {
    $streamlitCmd += " --server.headless=true"
}

if ($Dev) {
    $streamlitCmd += " --server.runOnSave=true"
}

# Launch
try {
    Invoke-Expression $streamlitCmd
} catch {
    Write-Error "❌ Erreur lors du lancement du dashboard: $_"
    exit 1
}

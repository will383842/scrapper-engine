#!/bin/bash

# ═══════════════════════════════════════════════════════════
# Scraper-Pro Dashboard - Launcher Script (Bash)
# ═══════════════════════════════════════════════════════════
#
# Usage:
#   ./dashboard/launch.sh
#
# Options:
#   --port 8502       # Custom port (default: 8501)
#   --dev             # Development mode (auto-reload)
#   --test            # Run tests before launch
#   --production      # Production mode (no debug)
#
# ═══════════════════════════════════════════════════════════

# ─── Default Options ───
PORT=8501
DEV_MODE=false
TEST_MODE=false
PRODUCTION_MODE=false

# ─── Parse Arguments ───
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --dev)
            DEV_MODE=true
            shift
            ;;
        --test)
            TEST_MODE=true
            shift
            ;;
        --production)
            PRODUCTION_MODE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--port 8502] [--dev] [--test] [--production]"
            exit 1
            ;;
    esac
done

# ─── Colors ───
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

function print_success() {
    echo -e "${GREEN}$1${NC}"
}

function print_error() {
    echo -e "${RED}$1${NC}"
}

function print_warning() {
    echo -e "${YELLOW}$1${NC}"
}

function print_info() {
    echo -e "${CYAN}$1${NC}"
}

# ─── Header ───
clear
echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                        ║${NC}"
echo -e "${CYAN}║   🚀 SCRAPER-PRO DASHBOARD LAUNCHER                   ║${NC}"
echo -e "${CYAN}║                                                        ║${NC}"
echo -e "${CYAN}║   Version: 2.0.0 FINAL                                ║${NC}"
echo -e "${CYAN}║   File: app_final.py                                  ║${NC}"
echo -e "${CYAN}║                                                        ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# ─── Check Python ───
print_info "🔍 Vérification de Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_success "✅ Python trouvé: $PYTHON_VERSION"
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version)
    print_success "✅ Python trouvé: $PYTHON_VERSION"
    PYTHON_CMD="python"
else
    print_error "❌ Python n'est pas installé ou n'est pas dans le PATH"
    print_error "   Installez Python depuis: https://www.python.org/downloads/"
    exit 1
fi

# ─── Check Virtual Environment ───
print_info "🔍 Vérification de l'environnement virtuel..."
if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
    print_success "✅ Virtual environment trouvé"
    print_info "🔄 Activation de l'environnement virtuel..."
    source venv/bin/activate
elif [ -d ".venv" ] && [ -f ".venv/bin/activate" ]; then
    print_success "✅ Virtual environment trouvé (.venv)"
    print_info "🔄 Activation de l'environnement virtuel..."
    source .venv/bin/activate
else
    print_warning "⚠️  Pas d'environnement virtuel détecté"
    print_info "📦 Création d'un nouvel environnement virtuel..."
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ]; then
        print_error "❌ Erreur lors de la création de l'environnement virtuel"
        exit 1
    fi
    print_success "✅ Environnement virtuel créé"
    print_info "🔄 Activation de l'environnement virtuel..."
    source venv/bin/activate
fi

# ─── Check Dependencies ───
print_info "🔍 Vérification des dépendances..."
PACKAGES_INSTALLED=true

REQUIRED_PACKAGES=("streamlit" "sqlalchemy" "requests" "psycopg2-binary" "python-dotenv")
for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! pip show "$package" &> /dev/null; then
        print_warning "⚠️  Package manquant: $package"
        PACKAGES_INSTALLED=false
    fi
done

if [ "$PACKAGES_INSTALLED" = false ]; then
    print_info "📦 Installation des dépendances..."
    pip install -r dashboard/requirements.txt
    if [ $? -ne 0 ]; then
        print_error "❌ Erreur lors de l'installation des dépendances"
        exit 1
    fi
    print_success "✅ Dépendances installées"
else
    print_success "✅ Toutes les dépendances sont installées"
fi

# ─── Check .env File ───
print_info "🔍 Vérification du fichier .env..."
if [ -f ".env" ]; then
    print_success "✅ Fichier .env trouvé"

    # Check critical variables
    CRITICAL_VARS=("DASHBOARD_PASSWORD" "API_HMAC_SECRET" "POSTGRES_PASSWORD")
    MISSING_VARS=()

    for var in "${CRITICAL_VARS[@]}"; do
        if ! grep -q "^$var=" .env; then
            MISSING_VARS+=("$var")
        fi
    done

    if [ ${#MISSING_VARS[@]} -gt 0 ]; then
        print_warning "⚠️  Variables critiques manquantes dans .env:"
        for var in "${MISSING_VARS[@]}"; do
            print_warning "   - $var"
        done
        print_info "   Consultez le fichier QUICKSTART.md pour la configuration"
    else
        print_success "✅ Toutes les variables critiques sont définies"
    fi
else
    print_warning "⚠️  Fichier .env non trouvé"
    print_info "📝 Création d'un fichier .env template..."

    cat > .env << 'EOF'
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
EOF

    print_success "✅ Fichier .env créé"
    print_warning "⚠️  IMPORTANT: Éditez .env avec vos vraies valeurs avant de continuer!"
    print_info "   Utilisez: nano .env  ou  vim .env"
    print_info "   Puis relancez ce script"
    exit 0
fi

# ─── Check Dashboard File ───
print_info "🔍 Vérification du fichier dashboard..."
if [ -f "dashboard/app_final.py" ]; then
    print_success "✅ dashboard/app_final.py trouvé"
else
    print_error "❌ dashboard/app_final.py non trouvé!"
    print_error "   Assurez-vous d'être dans le répertoire racine du projet"
    exit 1
fi

# ─── Run Tests ───
if [ "$TEST_MODE" = true ]; then
    print_info "🧪 Exécution des tests..."
    echo ""
    $PYTHON_CMD dashboard/test_dashboard.py
    if [ $? -ne 0 ]; then
        print_error "❌ Les tests ont échoué"
        print_warning "   Corrigez les erreurs avant de lancer le dashboard"
        exit 1
    fi
    print_success "✅ Tous les tests sont passés"
    echo ""
fi

# ─── Launch Dashboard ───
print_info "🚀 Lancement du dashboard..."
echo ""
print_success "═══════════════════════════════════════════════════════"
print_success "  Dashboard disponible sur:"
print_success "  http://localhost:$PORT"
print_success "═══════════════════════════════════════════════════════"
echo ""

if [ "$PRODUCTION_MODE" = true ]; then
    MODE="Production"
elif [ "$DEV_MODE" = true ]; then
    MODE="Development"
else
    MODE="Standard"
fi

print_info "  Mode: $MODE"
print_info "  Port: $PORT"
echo ""
print_warning "  Appuyez sur Ctrl+C pour arrêter le dashboard"
echo ""

# Build Streamlit command
STREAMLIT_CMD="streamlit run dashboard/app_final.py --server.port=$PORT --server.address=0.0.0.0"

if [ "$PRODUCTION_MODE" = true ]; then
    STREAMLIT_CMD="$STREAMLIT_CMD --server.headless=true"
fi

if [ "$DEV_MODE" = true ]; then
    STREAMLIT_CMD="$STREAMLIT_CMD --server.runOnSave=true"
fi

# Launch
eval $STREAMLIT_CMD

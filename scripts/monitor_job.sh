#!/bin/bash
# ============================================================
# Monitor Scraping Job - Surveillance temps réel
# ============================================================
# Usage: ./monitor_job.sh <job_id> [interval_seconds]
#
# Exemple:
#   ./monitor_job.sh 123
#   ./monitor_job.sh 123 5  # Rafraîchir toutes les 5 secondes
# ============================================================

set -e

JOB_ID=$1
INTERVAL=${2:-10}  # Défaut: 10 secondes

if [ -z "$JOB_ID" ]; then
  echo "❌ Erreur: job_id manquant"
  echo ""
  echo "Usage: $0 <job_id> [interval_seconds]"
  echo ""
  echo "Exemples:"
  echo "  $0 123           # Surveiller le job #123 (rafraîchir toutes les 10s)"
  echo "  $0 123 5         # Surveiller avec interval de 5s"
  echo ""
  exit 1
fi

API_URL="${API_URL:-http://localhost:8000}"
STATUS_ENDPOINT="$API_URL/api/v1/scraping/jobs/$JOB_ID/status"
LOGS_ENDPOINT="$API_URL/api/v1/scraping/jobs/$JOB_ID/logs"

# Vérifier que jq est installé
if ! command -v jq &> /dev/null; then
  echo "⚠️  Attention: jq n'est pas installé (affichage limité)"
  USE_JQ=false
else
  USE_JQ=true
fi

# Vérifier que le job existe
echo "🔍 Vérification du job #$JOB_ID..."
if [ "$USE_JQ" = true ]; then
  JOB_NAME=$(curl -s "$STATUS_ENDPOINT" | jq -r '.name // "N/A"')
  if [ "$JOB_NAME" = "N/A" ]; then
    echo "❌ Job #$JOB_ID introuvable"
    exit 1
  fi
  echo "✅ Job trouvé: $JOB_NAME"
else
  curl -s "$STATUS_ENDPOINT" > /dev/null || {
    echo "❌ Job #$JOB_ID introuvable"
    exit 1
  }
  echo "✅ Job trouvé"
fi

echo ""
echo "📊 Surveillance du job #$JOB_ID (Ctrl+C pour arrêter)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ITERATION=0

while true; do
  ITERATION=$((ITERATION + 1))
  TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

  if [ "$USE_JQ" = true ]; then
    # Avec jq (affichage enrichi)
    RESPONSE=$(curl -s "$STATUS_ENDPOINT")

    STATUS=$(echo "$RESPONSE" | jq -r '.status // "N/A"')
    PROGRESS=$(echo "$RESPONSE" | jq -r '.progress // 0')
    PAGES=$(echo "$RESPONSE" | jq -r '.pages_scraped // 0')
    CONTACTS=$(echo "$RESPONSE" | jq -r '.contacts_extracted // 0')
    ERRORS=$(echo "$RESPONSE" | jq -r '.errors_count // 0')
    SOURCE_TYPE=$(echo "$RESPONSE" | jq -r '.source_type // "N/A"')

    # Couleurs selon le status
    case $STATUS in
      "running")
        STATUS_COLOR="\033[0;33m"  # Jaune
        STATUS_EMOJI="⚙️"
        ;;
      "completed")
        STATUS_COLOR="\033[0;32m"  # Vert
        STATUS_EMOJI="✅"
        ;;
      "failed")
        STATUS_COLOR="\033[0;31m"  # Rouge
        STATUS_EMOJI="❌"
        ;;
      "pending")
        STATUS_COLOR="\033[0;36m"  # Cyan
        STATUS_EMOJI="⏳"
        ;;
      *)
        STATUS_COLOR="\033[0m"     # Normal
        STATUS_EMOJI="❓"
        ;;
    esac
    RESET_COLOR="\033[0m"

    # Barre de progression
    PROGRESS_INT=${PROGRESS%.*}  # Convertir en entier
    PROGRESS_BAR=""
    PROGRESS_FILLED=$((PROGRESS_INT / 5))  # 20 caractères max
    for i in $(seq 1 20); do
      if [ $i -le $PROGRESS_FILLED ]; then
        PROGRESS_BAR="${PROGRESS_BAR}█"
      else
        PROGRESS_BAR="${PROGRESS_BAR}░"
      fi
    done

    echo -e "[$TIMESTAMP] Rafraîchissement #$ITERATION"
    echo -e "  Status      : ${STATUS_COLOR}${STATUS_EMOJI} ${STATUS}${RESET_COLOR}"
    echo -e "  Progress    : [$PROGRESS_BAR] ${PROGRESS}%"
    echo -e "  Type        : $SOURCE_TYPE"
    echo -e "  Pages       : $PAGES"
    echo -e "  Contacts    : $CONTACTS"
    echo -e "  Errors      : $ERRORS"

    # Si erreurs, afficher un warning
    if [ "$ERRORS" -gt 0 ]; then
      echo -e "  ⚠️  Logs     : $LOGS_ENDPOINT"
    fi

    echo ""

  else
    # Sans jq (affichage basique)
    curl -s "$STATUS_ENDPOINT"
    echo ""
  fi

  # Vérifier si le job est terminé
  if [ "$USE_JQ" = true ]; then
    if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ] || [ "$STATUS" = "cancelled" ]; then
      echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
      echo ""
      echo "🏁 Job terminé avec status: $STATUS"

      if [ "$STATUS" = "completed" ]; then
        echo ""
        echo "📊 Résumé final:"
        echo "  • Pages scrapées    : $PAGES"
        echo "  • Contacts extraits : $CONTACTS"
        echo "  • Erreurs           : $ERRORS"

        if [ "$ERRORS" -gt 0 ]; then
          echo ""
          echo "⚠️  Des erreurs ont été détectées. Consultez les logs:"
          echo "   curl $LOGS_ENDPOINT"
        fi
      elif [ "$STATUS" = "failed" ]; then
        echo ""
        echo "❌ Le job a échoué. Consultez les logs pour diagnostiquer:"
        echo "   curl $LOGS_ENDPOINT | jq '.logs[]'"
      fi

      echo ""
      exit 0
    fi
  fi

  sleep $INTERVAL
done

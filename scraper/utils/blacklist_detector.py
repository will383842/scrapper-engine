"""Détection automatique de blacklist et gestion des fallbacks."""

import logging
import os
from typing import Optional
from scrapy.http import Response

logger = logging.getLogger(__name__)


class BlacklistDetector:
    """
    Détecte si une IP/proxy est blacklisté par Google ou d'autres sites.
    Gère les fallbacks automatiques (rotation proxy, SerpAPI).
    """

    # Indicateurs de blacklist dans le HTML/headers
    BLACKLIST_INDICATORS = [
        "captcha",
        "unusual traffic",
        "automated queries",
        "automated requests",
        "robot",
        "sorry, but your computer",
        "unusual activity",
        "recaptcha",
        "verify you're not a robot",
        "access denied",
        "blocked",
        "too many requests",
    ]

    # URLs de redirection suspectes
    BLACKLIST_URLS = [
        "google.com/sorry",
        "google.com/recaptcha",
        "ipban",
        "captcha-delivery",
    ]

    def __init__(self):
        self.consecutive_blacklists = 0
        self.max_consecutive_blacklists = 3

    def is_blacklisted(self, response: Response) -> tuple[bool, Optional[str]]:
        """
        Vérifie si la réponse indique un blacklist.

        Returns:
            tuple: (is_blacklisted: bool, reason: str)
        """
        # 1. Status codes suspects
        if response.status in [403, 429, 503]:
            reason = f"HTTP {response.status}"
            logger.warning(f"🚨 Blacklist detected: {reason}")
            return True, reason

        # 2. Redirection vers page CAPTCHA
        url_lower = response.url.lower()
        for suspect_url in self.BLACKLIST_URLS:
            if suspect_url in url_lower:
                reason = f"Redirect to {suspect_url}"
                logger.warning(f"🚨 Blacklist detected: {reason}")
                return True, reason

        # 3. Contenu HTML suspect
        try:
            html_lower = response.text.lower()

            for indicator in self.BLACKLIST_INDICATORS:
                if indicator in html_lower:
                    reason = f"Keyword: {indicator}"
                    logger.warning(f"🚨 Blacklist detected: {reason}")
                    return True, reason

        except Exception as e:
            logger.debug(f"Could not analyze HTML: {e}")

        # 4. Réponse vide ou trop petite (souvent signe de block)
        if len(response.body) < 500:
            reason = f"Response too small ({len(response.body)} bytes)"
            logger.warning(f"⚠️ Suspicious response: {reason}")
            return True, reason

        # Pas de blacklist détecté
        return False, None

    def trigger_fallback(
        self,
        spider,
        response: Response,
        reason: str
    ) -> dict:
        """
        Actions automatiques quand blacklist détectée.

        Returns:
            dict: Configuration du fallback
        """
        self.consecutive_blacklists += 1

        logger.error(
            f"🚨 BLACKLIST #{self.consecutive_blacklists}: {reason} | "
            f"URL: {response.url} | Proxy: {response.meta.get('proxy', 'N/A')}"
        )

        # Sauvegarder l'événement dans la DB
        self._log_blacklist_event(spider, response, reason)

        # Stratégie de fallback selon le nombre consécutif
        if self.consecutive_blacklists == 1:
            # Premier blacklist : juste changer de proxy
            logger.info("📍 Fallback strategy: Rotate proxy")
            return {
                "action": "rotate_proxy",
                "delay": 5,  # Attendre 5s avant de relancer
            }

        elif self.consecutive_blacklists == 2:
            # Deuxième blacklist : ralentir + changer proxy
            logger.warning("📍 Fallback strategy: Rotate proxy + slow down")
            return {
                "action": "rotate_proxy_slow",
                "delay": 10,  # Attendre 10s
                "new_download_delay": 5.0,  # Ralentir à 5s entre requêtes
            }

        elif self.consecutive_blacklists >= 3:
            # Troisième+ blacklist : fallback SerpAPI si disponible
            if os.getenv("SERPAPI_KEY"):
                logger.warning("📍 Fallback strategy: Switch to SerpAPI")
                return {
                    "action": "use_serpapi",
                    "delay": 15,
                }
            else:
                # Pas de SerpAPI : pause longue
                logger.error("📍 Fallback strategy: Long pause (no SerpAPI)")
                return {
                    "action": "long_pause",
                    "delay": 60,  # 1 minute de pause
                    "new_download_delay": 10.0,
                }

    def reset_counter(self):
        """Réinitialise le compteur après un succès."""
        if self.consecutive_blacklists > 0:
            logger.info(
                f"✅ Blacklist counter reset (was {self.consecutive_blacklists})"
            )
            self.consecutive_blacklists = 0

    def _log_blacklist_event(self, spider, response: Response, reason: str):
        """Enregistre l'événement de blacklist dans la DB."""
        try:
            from scraper.database import get_db_session
            from sqlalchemy import text

            proxy_url = response.meta.get("proxy", "unknown")

            with get_db_session() as session:
                # Log dans error_logs
                session.execute(
                    text("""
                        INSERT INTO error_logs
                            (job_id, error_type, error_message, url, proxy_used)
                        VALUES
                            (:job_id, 'blacklist', :reason, :url, :proxy)
                    """),
                    {
                        "job_id": getattr(spider, "job_id", None),
                        "reason": reason,
                        "url": response.url,
                        "proxy": proxy_url,
                    },
                )

                # Marquer le proxy comme suspect
                if proxy_url != "unknown":
                    session.execute(
                        text("""
                            UPDATE proxy_stats
                            SET consecutive_failures = consecutive_failures + 1,
                                updated_at = NOW()
                            WHERE proxy_url = :proxy
                        """),
                        {"proxy": proxy_url},
                    )

                logger.debug(f"Blacklist event logged to database")

        except Exception as e:
            logger.error(f"Failed to log blacklist event: {e}")

    def should_use_serpapi_fallback(self, spider) -> bool:
        """
        Détermine si on doit utiliser SerpAPI comme fallback.

        Returns:
            bool: True si SerpAPI disponible et recommandé
        """
        # Vérifier que SerpAPI est configuré
        if not os.getenv("SERPAPI_KEY"):
            return False

        # Vérifier que c'est un spider Google
        if spider.name not in ["google_search", "google_maps"]:
            return False

        # Si trop de blacklists consécutifs, utiliser SerpAPI
        if self.consecutive_blacklists >= 3:
            return True

        return False


# Singleton global
_detector = None


def get_blacklist_detector() -> BlacklistDetector:
    """Retourne l'instance singleton du détecteur."""
    global _detector
    if _detector is None:
        _detector = BlacklistDetector()
    return _detector

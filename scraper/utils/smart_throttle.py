"""Auto-throttling intelligent basé sur le taux d'erreur."""

import logging
from collections import deque
from scrapy import signals
from scrapy.exceptions import NotConfigured

logger = logging.getLogger(__name__)


class SmartThrottleExtension:
    """
    Extension Scrapy qui ajuste automatiquement la vitesse de scraping
    selon le taux d'erreur détecté.

    Stratégie:
    - Taux d'erreur > 30% → RALENTIR x2
    - Taux d'erreur > 10% → RALENTIR x1.5
    - Taux d'erreur < 5% → ACCÉLÉRER x0.9
    """

    def __init__(self, stats):
        self.stats = stats
        self.error_rate_window = deque(maxlen=100)  # 100 dernières requêtes
        self.current_delay = 2.0  # Délai initial (settings.DOWNLOAD_DELAY)
        self.min_delay = 1.0
        self.max_delay = 60.0
        self.adjustment_interval = 50  # Ajuster tous les 50 requêtes

        self.request_count = 0
        self.last_adjustment_count = 0

    @classmethod
    def from_crawler(cls, crawler):
        """Factory method pour créer l'extension."""
        if not crawler.settings.getbool("AUTOTHROTTLE_ENABLED"):
            raise NotConfigured("AUTOTHROTTLE_ENABLED must be True")

        ext = cls(crawler.stats)

        # Récupérer le délai initial depuis settings
        ext.current_delay = crawler.settings.getfloat("DOWNLOAD_DELAY", 2.0)
        ext.min_delay = crawler.settings.getfloat("SMART_THROTTLE_MIN_DELAY", 1.0)
        ext.max_delay = crawler.settings.getfloat("SMART_THROTTLE_MAX_DELAY", 60.0)

        # Connecter aux signaux Scrapy
        crawler.signals.connect(ext.response_received, signal=signals.response_received)
        crawler.signals.connect(ext.request_failed, signal=signals.request_dropped)
        crawler.signals.connect(ext.request_failed, signal=signals.response_download_failed)

        logger.info(f"SmartThrottleExtension initialized (delay={ext.current_delay}s)")

        return ext

    def response_received(self, response, request, spider):
        """Appelé quand une réponse est reçue avec succès."""
        self.request_count += 1

        # Marquer comme succès (0) ou échec (1)
        if response.status >= 400:
            self.error_rate_window.append(1)  # Échec
        else:
            self.error_rate_window.append(0)  # Succès

        self._maybe_adjust_delay(spider)

    def request_failed(self, reason, request, spider):
        """Appelé quand une requête échoue."""
        self.request_count += 1
        self.error_rate_window.append(1)  # Échec

        self._maybe_adjust_delay(spider)

    def _maybe_adjust_delay(self, spider):
        """Ajuste le délai si on a atteint l'intervalle."""
        # Attendre d'avoir assez de données
        if len(self.error_rate_window) < 20:
            return

        # Ajuster seulement tous les N requêtes
        if self.request_count - self.last_adjustment_count < self.adjustment_interval:
            return

        self.last_adjustment_count = self.request_count

        # Calculer le taux d'erreur
        error_rate = sum(self.error_rate_window) / len(self.error_rate_window)

        old_delay = self.current_delay

        # Ajuster le délai selon le taux d'erreur
        if error_rate > 0.3:  # > 30% d'erreurs
            # RALENTIR AGRESSIVEMENT
            self.current_delay *= 2.0
            logger.warning(
                f"⚠️ HIGH ERROR RATE ({error_rate:.0%}) → "
                f"Slowing down: {old_delay:.1f}s → {self.current_delay:.1f}s"
            )

        elif error_rate > 0.1:  # > 10% d'erreurs
            # RALENTIR MODÉRÉMENT
            self.current_delay *= 1.5
            logger.info(
                f"⚠️ Moderate error rate ({error_rate:.0%}) → "
                f"Slowing down: {old_delay:.1f}s → {self.current_delay:.1f}s"
            )

        elif error_rate < 0.05:  # < 5% d'erreurs
            # ACCÉLÉRER PROGRESSIVEMENT
            self.current_delay *= 0.9
            logger.info(
                f"✅ Low error rate ({error_rate:.0%}) → "
                f"Speeding up: {old_delay:.1f}s → {self.current_delay:.1f}s"
            )

        # Appliquer les limites
        self.current_delay = max(self.min_delay, min(self.max_delay, self.current_delay))

        # Mettre à jour le setting Scrapy
        if hasattr(spider, "download_delay"):
            spider.download_delay = self.current_delay
        if hasattr(spider, "crawler"):
            spider.crawler.engine.downloader.slots.update_delay(self.current_delay)

        # Enregistrer dans les stats
        self.stats.set_value("smart_throttle/current_delay", self.current_delay)
        self.stats.set_value("smart_throttle/error_rate", error_rate)

    def get_current_delay(self) -> float:
        """Retourne le délai actuel."""
        return self.current_delay

    def get_error_rate(self) -> float:
        """Retourne le taux d'erreur actuel."""
        if len(self.error_rate_window) == 0:
            return 0.0
        return sum(self.error_rate_window) / len(self.error_rate_window)

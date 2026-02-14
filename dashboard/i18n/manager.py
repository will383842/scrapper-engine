"""Gestionnaire d'internationalisation pour Streamlit."""
import streamlit as st
from typing import Dict, Any
import json
from pathlib import Path


class I18nManager:
    """Gestionnaire de traductions pour le dashboard Scraper-Pro."""

    def __init__(self, locales_dir: Path = None, default_lang: str = 'fr'):
        """
        Initialise le gestionnaire i18n.

        Args:
            locales_dir: Répertoire contenant les fichiers JSON de traduction
            default_lang: Langue par défaut ('fr' ou 'en')
        """
        self.default_lang = default_lang
        self.locales_dir = locales_dir or Path(__file__).parent / 'locales'
        self._translations: Dict[str, Dict] = {}
        self._load_translations()

    def _load_translations(self):
        """Charge les fichiers JSON de traductions depuis le répertoire locales."""
        if not self.locales_dir.exists():
            return

        for json_file in self.locales_dir.glob('*.json'):
            lang = json_file.stem
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    self._translations[lang] = json.load(f)
            except Exception as e:
                st.warning(f"Erreur chargement {json_file}: {e}")

    def get_current_lang(self) -> str:
        """
        Retourne la langue courante depuis session state + URL params.

        Returns:
            Code langue ('fr' ou 'en')
        """
        # Initialiser depuis URL params si pas encore en session
        if 'app_lang' not in st.session_state:
            query_params = st.query_params
            url_lang = query_params.get('lang', self.default_lang)

            # Valider la langue
            if url_lang in self._translations:
                st.session_state.app_lang = url_lang
            else:
                st.session_state.app_lang = self.default_lang

        return st.session_state.app_lang

    def set_language(self, lang: str):
        """
        Change la langue de l'interface.

        Args:
            lang: Code langue ('fr' ou 'en')
        """
        if lang in self._translations:
            st.session_state.app_lang = lang
            # Persister dans URL params
            st.query_params['lang'] = lang
        else:
            st.warning(f"Langue '{lang}' non disponible")

    def t(self, key: str, **kwargs) -> str:
        """
        Traduit une clé avec support de variables et clés imbriquées.

        Args:
            key: Clé de traduction (ex: 'jobs.header' ou 'msg.error')
            **kwargs: Variables à interpoler (ex: error='test')

        Returns:
            Texte traduit

        Examples:
            >>> i18n.t('jobs.header')
            'Gestion des Jobs'
            >>> i18n.t('msg.error', error='Connection failed')
            'Erreur: Connection failed'
        """
        lang = self.get_current_lang()
        translations = self._translations.get(lang, self._translations.get(self.default_lang, {}))

        # Résoudre les clés imbriquées (ex: 'jobs.metrics.total')
        value = translations
        for k in key.split('.'):
            if isinstance(value, dict):
                value = value.get(k, key)
            else:
                # Clé invalide, retourner la clé elle-même
                return key

        # Interpolation des variables
        if kwargs and isinstance(value, str):
            try:
                value = value.format(**kwargs)
            except KeyError as e:
                st.warning(f"Variable manquante dans traduction '{key}': {e}")

        return value if isinstance(value, str) else key

    def render_language_switcher(self):
        """Affiche un toggle FR/EN en pills style (Backlink Engine)."""
        current_lang = self.get_current_lang()
        langs = {'fr': '🇫🇷 FR', 'en': '🇬🇧 EN'}

        # Pills selector (modern toggle)
        selected = st.pills(
            "Language",
            options=list(langs.keys()),
            format_func=lambda x: langs[x],
            default=current_lang,
            label_visibility="collapsed",
            key="lang_switcher"
        )

        # Changer la langue si sélection différente
        if selected and selected != current_lang:
            self.set_language(selected)
            st.rerun()

    def get_available_languages(self) -> list[str]:
        """Retourne la liste des langues disponibles."""
        return list(self._translations.keys())

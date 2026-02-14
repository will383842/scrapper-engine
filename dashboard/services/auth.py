"""Authentication service for Scraper-Pro dashboard."""
import hmac
import os
import streamlit as st
from i18n.manager import I18nManager


def check_authentication(i18n: I18nManager) -> bool:
    """
    Vérifie l'authentification de l'utilisateur.

    Affiche un formulaire de login si non authentifié.

    Args:
        i18n: Gestionnaire de traductions

    Returns:
        True si authentifié, False sinon
    """
    # Initialiser session state
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    # Si déjà authentifié, retourner True
    if st.session_state.authenticated:
        return True

    # Afficher formulaire de login
    st.title(i18n.t('auth.title'))

    password = st.text_input(
        i18n.t('auth.password'),
        type="password",
        key="auth_password"
    )

    if st.button(i18n.t('auth.login'), type="primary"):
        dashboard_pw = os.getenv("DASHBOARD_PASSWORD", "")

        if not dashboard_pw:
            st.error(i18n.t('auth.notConfigured'))
        elif hmac.compare_digest(password.encode(), dashboard_pw.encode()):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error(i18n.t('auth.invalidPassword'))

    return False

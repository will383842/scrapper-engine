"""Page Config - Configuration système."""
import os
import streamlit as st
from services.api import api_request, SCRAPER_API_URL, API_HMAC_SECRET
from services.db import query_df
from i18n.manager import I18nManager


def render_config_page(i18n: I18nManager):
    """
    Page de configuration système.

    Args:
        i18n: Gestionnaire de traductions
    """
    st.header(i18n.t('config.header'))

    # System Health
    st.subheader(i18n.t('config.systemHealth.title'))
    try:
        health = api_request("GET", "/health")
        col1, col2, col3 = st.columns(3)
        api_ok = health.get("status") == "ok"
        col1.metric(
            i18n.t('config.systemHealth.api'),
            i18n.t('config.systemHealth.ok') if api_ok else i18n.t('config.systemHealth.degraded')
        )
        col2.metric(
            i18n.t('config.systemHealth.postgres'),
            i18n.t('config.systemHealth.ok') if health.get("postgres") else i18n.t('config.systemHealth.down')
        )
        col3.metric(
            i18n.t('config.systemHealth.redis'),
            i18n.t('config.systemHealth.ok') if health.get("redis") else i18n.t('config.systemHealth.down')
        )
    except Exception:
        st.warning(i18n.t('config.systemHealth.unreachable'))

    # Active Configuration
    st.subheader(i18n.t('config.activeConfig.title'))
    st.markdown(f"**{i18n.t('config.activeConfig.proxyProvider')}**")
    st.code(os.getenv("PROXY_PROVIDER", i18n.t('config.activeConfig.notSet')))

    # MailWizz routing
    st.markdown(f"**{i18n.t('config.activeConfig.mailwizzRouting')}**")
    try:
        routing = query_df("""
            SELECT 'sos-expat' as platform, 'configured' as status
            WHERE EXISTS (SELECT 1 FROM validated_contacts WHERE platform = 'sos-expat' LIMIT 1)
            UNION ALL
            SELECT 'ulixai' as platform, 'configured' as status
            WHERE EXISTS (SELECT 1 FROM validated_contacts WHERE platform = 'ulixai' LIMIT 1)
        """)
        if routing:
            st.dataframe(routing, use_container_width=True)
        else:
            st.info(i18n.t('config.activeConfig.noPlatforms'))
    except Exception:
        pass

    # Environment
    st.subheader(i18n.t('config.environment.title'))
    env_info = {
        "SCRAPER_API_URL": SCRAPER_API_URL,
        "POSTGRES_HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "POSTGRES_DB": os.getenv("POSTGRES_DB", "scraper_db"),
        "API_HMAC_SECRET": i18n.t('config.environment.configured') if API_HMAC_SECRET else i18n.t('config.environment.notSet'),
        "DASHBOARD_PASSWORD": i18n.t('config.environment.configured') if os.getenv("DASHBOARD_PASSWORD") else i18n.t('config.environment.notSet'),
    }
    st.json(env_info)

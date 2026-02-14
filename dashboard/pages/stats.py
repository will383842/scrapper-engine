"""Page Stats - Statistiques du pipeline."""
import streamlit as st
from services.db import query_df
from i18n.manager import I18nManager


def render_stats_page(i18n: I18nManager):
    """
    Page de statistiques du pipeline.

    Args:
        i18n: Gestionnaire de traductions
    """
    st.header(i18n.t('stats.header'))

    try:
        # Daily Scraping Volume
        st.subheader(i18n.t('stats.dailyScraping'))
        daily_scraped = query_df("""
            SELECT DATE(scraped_at) as date, COUNT(*) as count
            FROM scraped_contacts
            WHERE scraped_at > NOW() - INTERVAL '30 days'
            GROUP BY DATE(scraped_at)
            ORDER BY date
        """)
        if daily_scraped:
            st.bar_chart(
                {row["date"].isoformat(): row["count"] for row in daily_scraped}
            )
        else:
            st.info(i18n.t('messages.noData'))

        # Daily MailWizz Sync
        st.subheader(i18n.t('stats.dailyMailwizz'))
        daily_sync = query_df("""
            SELECT DATE(synced_at) as date, status, COUNT(*) as count
            FROM mailwizz_sync_log
            WHERE synced_at > NOW() - INTERVAL '30 days'
            GROUP BY DATE(synced_at), status
            ORDER BY date
        """)
        if daily_sync:
            st.dataframe(daily_sync, use_container_width=True)
        else:
            st.info(i18n.t('messages.noData'))

        # Domain Blacklist
        st.subheader(i18n.t('stats.domainBlacklist'))
        blacklist = query_df("""
            SELECT domain, bounce_count, total_sent, bounce_rate
            FROM email_domain_blacklist
            ORDER BY bounce_count DESC
            LIMIT 20
        """)
        if blacklist:
            st.dataframe(blacklist, use_container_width=True)
        else:
            st.info(i18n.t('stats.noBlacklist'))

        # WHOIS Intelligence
        st.subheader(i18n.t('stats.whoisIntelligence'))
        whois_stats = query_df("""
            SELECT
                COUNT(*) as total_lookups,
                SUM(CASE WHEN whois_private THEN 1 ELSE 0 END) as private_whois,
                SUM(CASE WHEN cloudflare_protected THEN 1 ELSE 0 END) as cloudflare,
                COUNT(DISTINCT registrar) as unique_registrars
            FROM whois_cache
            WHERE lookup_status = 'success'
        """)
        if whois_stats:
            ws = whois_stats[0]
            col1, col2, col3, col4 = st.columns(4)
            col1.metric(i18n.t('stats.whoisMetrics.totalLookups'), ws["total_lookups"])
            col2.metric(i18n.t('stats.whoisMetrics.privateWhois'), ws["private_whois"])
            col3.metric(i18n.t('stats.whoisMetrics.cloudflare'), ws["cloudflare"])
            col4.metric(i18n.t('stats.whoisMetrics.registrars'), ws["unique_registrars"])

    except Exception as e:
        st.error(i18n.t('messages.dbError', error=str(e)))

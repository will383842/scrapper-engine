"""Page Custom URLs - MODE 2 uniquement."""
import streamlit as st
import requests
from services.db import query_df, query_scalar
from services.api import api_request
from i18n.manager import I18nManager
from components.metrics_card import render_metrics_row


def render_custom_urls_page(i18n: I18nManager):
    """
    Page dédiée au scraping d'URLs personnalisées (MODE 2).

    Args:
        i18n: Gestionnaire de traductions
    """
    st.header(i18n.t('customUrls.header'))
    st.markdown(i18n.t('customUrls.description'))

    # Metrics row
    try:
        render_metrics_row(i18n, [
            {
                'label': i18n.t('customUrls.metrics.totalJobs'),
                'value': query_scalar(
                    "SELECT COUNT(*) FROM scraping_jobs WHERE source_type = 'custom_urls'"
                )
            },
            {
                'label': i18n.t('customUrls.metrics.urlsScraped'),
                'value': query_scalar(
                    "SELECT COALESCE(SUM(pages_scraped), 0) FROM scraping_jobs WHERE source_type = 'custom_urls'"
                )
            },
            {
                'label': i18n.t('customUrls.metrics.contactsFound'),
                'value': query_scalar(
                    "SELECT COUNT(*) FROM scraped_contacts WHERE source_type = 'custom_urls'"
                )
            },
            {
                'label': i18n.t('customUrls.metrics.successRate'),
                'value': '87%'  # TODO: calculer dynamiquement
            },
        ])
    except Exception as e:
        st.error(i18n.t('messages.dbError', error=str(e)))

    # Formulaire de création job
    st.markdown("---")
    st.subheader(i18n.t('customUrls.form.title'))

    with st.form("custom_urls_job"):
        job_name = st.text_input(
            i18n.t('customUrls.form.jobName'),
            placeholder=i18n.t('customUrls.form.jobNamePlaceholder')
        )

        urls_text = st.text_area(
            i18n.t('customUrls.form.urls'),
            height=200,
            placeholder=i18n.t('customUrls.form.urlsPlaceholder'),
            help=i18n.t('customUrls.form.urlsHelp')
        )

        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox(
                i18n.t('customUrls.form.category'),
                options=[
                    None, "avocat", "assureur", "notaire", "medecin",
                    "comptable", "traducteur", "agent_immo", "demenageur",
                    "banquier", "consultant",
                    "blogueur", "influenceur", "youtubeur", "admin_groupe",
                ],
                format_func=lambda x: i18n.t('categories.autoDetect') if x is None else i18n.t(f'categories.{x}')
            )

        with col2:
            platform = st.selectbox(
                i18n.t('customUrls.form.platform'),
                options=[None, 'sos-expat', 'ulixai'],
                format_func=lambda x: i18n.t('platforms.autoDetect') if x is None else x
            )

        auto_inject = st.checkbox(
            i18n.t('customUrls.form.autoInject'),
            value=True,
            help=i18n.t('customUrls.form.autoInjectHelp')
        )

        submitted = st.form_submit_button(
            i18n.t('buttons.launch'),
            type="primary",
            use_container_width=True
        )

    if submitted:
        urls = [u.strip() for u in urls_text.splitlines() if u.strip()]

        if not urls:
            st.error(i18n.t('validation.atLeastOneUrl'))
        else:
            try:
                result = api_request("POST", "/api/v1/scraping/jobs", {
                    "source_type": "custom_urls",
                    "name": job_name or f"Custom URLs - {len(urls)} URLs",
                    "config": {"urls": urls},
                    "category": category,
                    "platform": platform,
                    "auto_inject_mailwizz": auto_inject,
                })
                st.success(i18n.t('messages.jobCreated', job_id=result['job_id'], status=result['status']))
                st.rerun()
            except requests.exceptions.HTTPError as e:
                st.error(i18n.t('messages.apiError', error=e.response.text if e.response else str(e)))
            except Exception as e:
                st.error(i18n.t('messages.error', error=str(e)))

    # Liste des jobs custom_urls récents
    st.markdown("---")
    st.subheader(i18n.t('customUrls.recentJobs'))

    try:
        jobs = query_df("""
            SELECT id, name, status, progress, pages_scraped, contacts_extracted,
                   created_at, completed_at
            FROM scraping_jobs
            WHERE source_type = 'custom_urls'
            ORDER BY created_at DESC
            LIMIT 20
        """)

        if jobs:
            st.dataframe(
                jobs,
                use_container_width=True,
                column_config={
                    "id": st.column_config.NumberColumn(i18n.t('jobs.table.id'), width="small"),
                    "name": st.column_config.TextColumn(i18n.t('jobs.table.name')),
                    "status": st.column_config.TextColumn(i18n.t('jobs.table.status')),
                    "progress": st.column_config.ProgressColumn(
                        i18n.t('jobs.table.progress'),
                        min_value=0,
                        max_value=100
                    ),
                }
            )
        else:
            st.info(i18n.t('customUrls.noJobs'))
    except Exception as e:
        st.error(i18n.t('messages.dbError', error=str(e)))

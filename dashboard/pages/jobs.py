"""Page Jobs - Liste et actions sur les jobs de scraping."""
import streamlit as st
import requests
from services.db import query_df
from services.api import api_request
from i18n.manager import I18nManager
from components.metrics_card import render_metrics_row


def render_jobs_page(i18n: I18nManager):
    """
    Page de gestion des jobs de scraping.

    Args:
        i18n: Gestionnaire de traductions
    """
    st.header(i18n.t('jobs.header'))

    # Liste des jobs
    try:
        jobs = query_df("""
            SELECT id, name, source_type, status, progress,
                   pages_scraped, contacts_extracted, errors_count,
                   created_at, started_at, completed_at
            FROM scraping_jobs
            ORDER BY created_at DESC
            LIMIT 50
        """)

        if jobs:
            # Metrics
            render_metrics_row(i18n, [
                {'label': i18n.t('jobs.metrics.total'), 'value': len(jobs)},
                {'label': i18n.t('jobs.metrics.running'), 'value': sum(1 for j in jobs if j["status"] == "running")},
                {'label': i18n.t('jobs.metrics.completed'), 'value': sum(1 for j in jobs if j["status"] == "completed")},
                {'label': i18n.t('jobs.metrics.failed'), 'value': sum(1 for j in jobs if j["status"] == "failed")},
            ])

            # Table
            st.dataframe(
                jobs,
                use_container_width=True,
                column_config={
                    "id": st.column_config.NumberColumn(i18n.t('jobs.table.id'), width="small"),
                    "progress": st.column_config.ProgressColumn(
                        i18n.t('jobs.table.progress'), min_value=0, max_value=100
                    ),
                },
            )

            # Job Control Actions
            st.markdown("---")
            st.subheader(i18n.t('jobs.actions.title'))

            ctrl_col1, ctrl_col2 = st.columns(2)
            with ctrl_col1:
                action_job_id = st.number_input(
                    i18n.t('jobs.actions.jobId'), min_value=1, step=1, key="action_job_id"
                )
            with ctrl_col2:
                action = st.selectbox(
                    i18n.t('jobs.actions.action'),
                    options=["resume", "pause", "cancel"],
                    format_func=lambda x: i18n.t(f'jobs.actions.{x}'),
                    key="action_type",
                )

            if st.button(i18n.t('jobs.actions.execute'), type="secondary", key="exec_action"):
                try:
                    result = api_request("POST", f"/api/v1/scraping/jobs/{action_job_id}/{action}")
                    st.success(i18n.t('messages.jobActionSuccess', job_id=action_job_id, status=result.get('status', 'done')))
                    st.rerun()
                except requests.exceptions.HTTPError as e:
                    st.error(i18n.t('messages.apiError', error=e.response.text if e.response else str(e)))
                except Exception as e:
                    st.error(i18n.t('messages.error', error=str(e)))

        else:
            st.info(i18n.t('jobs.noJobs'))
    except Exception as e:
        st.error(i18n.t('messages.dbError', error=str(e)))

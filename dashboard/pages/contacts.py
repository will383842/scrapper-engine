"""Page Contacts - Pipeline de contacts scrapés et validés."""
import csv
import io
import streamlit as st
from services.db import query_df, query_scalar
from i18n.manager import I18nManager
from components.metrics_card import render_metrics_row


def render_contacts_page(i18n: I18nManager):
    """
    Page du pipeline de contacts.

    Args:
        i18n: Gestionnaire de traductions
    """
    st.header(i18n.t('contacts.header'))

    try:
        # Metrics
        render_metrics_row(i18n, [
            {'label': i18n.t('contacts.metrics.scraped'), 'value': query_scalar("SELECT COUNT(*) FROM scraped_contacts")},
            {'label': i18n.t('contacts.metrics.validated'), 'value': query_scalar("SELECT COUNT(*) FROM validated_contacts")},
            {
                'label': i18n.t('contacts.metrics.sentToMailwizz'),
                'value': query_scalar("SELECT COUNT(*) FROM validated_contacts WHERE status = 'sent_to_mailwizz'")
            },
            {
                'label': i18n.t('contacts.metrics.bounced'),
                'value': query_scalar("SELECT COUNT(*) FROM validated_contacts WHERE status = 'bounced'")
            },
        ])

        # By Platform
        st.subheader(i18n.t('contacts.byPlatform'))
        by_platform = query_df("""
            SELECT platform, category, COUNT(*) as count
            FROM validated_contacts
            GROUP BY platform, category
            ORDER BY platform, count DESC
        """)
        if by_platform:
            st.dataframe(by_platform, use_container_width=True)
        else:
            st.info(i18n.t('contacts.noValidated'))

        # Export CSV
        st.markdown("---")
        st.subheader(i18n.t('contacts.export.title'))

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            export_status = st.selectbox(
                i18n.t('contacts.export.statusFilter'),
                options=["all", "validated", "sent_to_mailwizz", "bounced"],
            )
        with col_f2:
            export_platform = st.selectbox(
                i18n.t('contacts.export.platformFilter'),
                options=["all", "sos-expat", "ulixai"],
            )
        with col_f3:
            export_category = st.selectbox(
                i18n.t('contacts.export.categoryFilter'),
                options=[
                    "all", "avocat", "assureur", "notaire", "medecin",
                    "comptable", "traducteur", "agent_immo", "demenageur",
                    "banquier", "consultant",
                    "blogueur", "influenceur", "youtubeur", "admin_groupe",
                ],
            )

        if st.button(i18n.t('buttons.generate')):
            try:
                where_clauses = []
                params = {}

                if export_status != "all":
                    where_clauses.append("status = :status")
                    params["status"] = export_status
                if export_platform != "all":
                    where_clauses.append("platform = :platform")
                    params["platform"] = export_platform
                if export_category != "all":
                    where_clauses.append("category = :category")
                    params["category"] = export_category

                where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

                contacts = query_df(
                    f"""
                    SELECT email, name, website, phone,
                           category, platform, country, status,
                           mailwizz_list_id, last_validated_at
                    FROM validated_contacts
                    {where_sql}
                    ORDER BY last_validated_at DESC
                    """,
                    params,
                )

                if not contacts:
                    st.warning(i18n.t('contacts.export.noContacts'))
                else:
                    buf = io.StringIO()
                    buf.write("\ufeff")  # BOM for Excel UTF-8
                    writer = csv.DictWriter(buf, fieldnames=contacts[0].keys())
                    writer.writeheader()
                    writer.writerows(contacts)

                    st.download_button(
                        label=i18n.t('contacts.export.download', count=len(contacts)),
                        data=buf.getvalue().encode("utf-8"),
                        file_name="contacts_export.csv",
                        mime="text/csv",
                    )
            except Exception as e:
                st.error(i18n.t('messages.exportError', error=str(e)))

    except Exception as e:
        st.error(i18n.t('messages.dbError', error=str(e)))

"""Page Blog Content - MODE 2 uniquement."""
import streamlit as st
import requests
from services.db import query_df, query_scalar
from services.api import api_request
from i18n.manager import I18nManager
from components.metrics_card import render_metrics_row


def render_blog_content_page(i18n: I18nManager):
    """
    Page dédiée au scraping de contenu de blogs (MODE 2).

    Args:
        i18n: Gestionnaire de traductions
    """
    st.header(i18n.t('blogContent.header'))
    st.markdown(i18n.t('blogContent.description'))

    # Metrics spécifiques blogs
    try:
        render_metrics_row(i18n, [
            {
                'label': i18n.t('blogContent.metrics.articlesScraped'),
                'value': query_scalar("SELECT COUNT(*) FROM scraped_articles")
            },
            {
                'label': i18n.t('blogContent.metrics.uniqueBlogs'),
                'value': query_scalar("SELECT COUNT(DISTINCT domain) FROM scraped_articles")
            },
            {
                'label': i18n.t('blogContent.metrics.avgWords'),
                'value': query_scalar("SELECT COALESCE(ROUND(AVG(word_count)), 0) FROM scraped_articles")
            },
            {
                'label': i18n.t('blogContent.metrics.thisWeek'),
                'value': query_scalar(
                    "SELECT COUNT(*) FROM scraped_articles WHERE scraped_at > NOW() - INTERVAL '7 days'"
                )
            },
        ])
    except Exception as e:
        st.error(i18n.t('messages.dbError', error=str(e)))

    # Formulaire création job blog
    st.markdown("---")
    st.subheader(i18n.t('blogContent.form.title'))

    with st.form("blog_job"):
        job_name = st.text_input(
            i18n.t('blogContent.form.jobName'),
            placeholder=i18n.t('customUrls.form.jobNamePlaceholder')
        )

        blog_url = st.text_input(
            i18n.t('blogContent.form.blogUrl'),
            placeholder="https://www.example-blog.com/articles/"
        )

        col1, col2 = st.columns(2)
        with col1:
            max_articles = st.number_input(
                i18n.t('blogContent.form.maxArticles'),
                min_value=10, max_value=100000, value=100
            )
        with col2:
            scrape_depth = st.number_input(
                i18n.t('blogContent.form.scrapeDepth'),
                min_value=1, max_value=10, value=2,
                help=i18n.t('blogContent.form.scrapeDepthHelp')
            )

        submitted = st.form_submit_button(
            i18n.t('buttons.launch'),
            type="primary",
            use_container_width=True
        )

    if submitted:
        if not blog_url or '.' not in blog_url:
            st.error(i18n.t('validation.invalidUrl'))
        else:
            try:
                result = api_request("POST", "/api/v1/scraping/jobs", {
                    "source_type": "blog_content",
                    "name": job_name or f"Blog - {blog_url}",
                    "config": {
                        "start_url": blog_url,
                        "max_articles": max_articles,
                        "scrape_depth": scrape_depth
                    }
                })
                st.success(i18n.t('messages.jobCreated', job_id=result['job_id'], status=result['status']))
                st.rerun()
            except requests.exceptions.HTTPError as e:
                st.error(i18n.t('messages.apiError', error=e.response.text if e.response else str(e)))
            except Exception as e:
                st.error(i18n.t('messages.error', error=str(e)))

    # Articles récents
    st.markdown("---")
    st.subheader(i18n.t('articles.header'))

    try:
        articles = query_df("""
            SELECT id, title, domain, language, word_count, author,
                   date_published, scraped_at, url
            FROM scraped_articles
            ORDER BY scraped_at DESC
            LIMIT 20
        """)

        if articles:
            st.dataframe(
                articles,
                use_container_width=True,
                column_config={
                    "id": st.column_config.NumberColumn(i18n.t('articles.table.id'), width="small"),
                    "title": st.column_config.TextColumn(i18n.t('articles.table.title')),
                    "url": st.column_config.LinkColumn(i18n.t('articles.table.url'), width="medium"),
                    "word_count": st.column_config.NumberColumn(i18n.t('articles.table.wordCount')),
                }
            )
        else:
            st.info(i18n.t('articles.noArticles'))
    except Exception as e:
        st.error(i18n.t('messages.dbError', error=str(e)))

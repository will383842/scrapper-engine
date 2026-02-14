"""Scraper-Pro Dashboard - MODE 2 (Simple) avec i18n FR/EN."""
import streamlit as st
from pathlib import Path

# Services
from services.auth import check_authentication

# i18n
from i18n.manager import I18nManager

# Components
from components.layout import render_sidebar, render_header

# Pages
from pages.custom_urls import render_custom_urls_page
from pages.blog_content import render_blog_content_page
from pages.jobs import render_jobs_page
from pages.contacts import render_contacts_page
from pages.stats import render_stats_page
from pages.config import render_config_page


# ===== Configuration Streamlit =====
st.set_page_config(
    page_title="Scraper-Pro Admin - MODE 2",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ===== Charger Custom CSS =====
def load_custom_css():
    """Charge le fichier CSS custom."""
    css_file = Path(__file__).parent / "assets" / "custom.css"
    if css_file.exists():
        with open(css_file, 'r', encoding='utf-8') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


load_custom_css()


# ===== Initialisation i18n =====
if 'i18n' not in st.session_state:
    st.session_state.i18n = I18nManager(
        locales_dir=Path(__file__).parent / 'i18n' / 'locales',
        default_lang='fr'
    )

i18n = st.session_state.i18n


# ===== Authentication =====
if not check_authentication(i18n):
    st.stop()


# ===== Current Page State =====
if 'current_page' not in st.session_state:
    # Default page: Custom URLs (MODE 2 focus)
    st.session_state.current_page = 'custom_urls'


# ===== Sidebar Navigation =====
selected_page = render_sidebar(i18n, st.session_state.current_page)
if selected_page != st.session_state.current_page:
    st.session_state.current_page = selected_page
    st.rerun()


# ===== Page Routing =====
PAGES = {
    'custom_urls': {
        'title': i18n.t('pages.customUrls.title'),
        'render': render_custom_urls_page
    },
    'blog_content': {
        'title': i18n.t('pages.blogContent.title'),
        'render': render_blog_content_page
    },
    'jobs': {
        'title': i18n.t('pages.jobs.title'),
        'render': render_jobs_page
    },
    'contacts': {
        'title': i18n.t('pages.contacts.title'),
        'render': render_contacts_page
    },
    'stats': {
        'title': i18n.t('pages.stats.title'),
        'render': render_stats_page
    },
    'config': {
        'title': i18n.t('pages.config.title'),
        'render': render_config_page
    },
}

# Get current page config
current_page_config = PAGES.get(st.session_state.current_page, PAGES['custom_urls'])


# ===== Header =====
render_header(i18n, current_page_config['title'])


# ===== Render Current Page =====
try:
    current_page_config['render'](i18n)
except Exception as e:
    st.error(f"Error rendering page: {e}")
    import traceback
    with st.expander("Debug Info"):
        st.code(traceback.format_exc())

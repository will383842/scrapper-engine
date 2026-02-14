"""Layout components: Sidebar + Header pour Scraper-Pro Dashboard."""
import streamlit as st
from i18n.manager import I18nManager


def render_sidebar(i18n: I18nManager, current_page: str) -> str:
    """
    Affiche la sidebar de navigation MODE 2 avec style sombre.

    Args:
        i18n: Gestionnaire de traductions
        current_page: Page actuellement active

    Returns:
        Page sélectionnée par l'utilisateur
    """
    # Custom CSS pour sidebar sombre (Backlink Engine style)
    st.markdown("""
    <style>
    /* Sidebar dark theme - Backlink Engine inspired */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #020617 100%);
    }

    [data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Sidebar logo/title */
    [data-testid="stSidebar"] h1 {
        color: #f8fafc !important;
        font-size: 24px;
        font-weight: 700;
        margin-bottom: 10px;
    }

    /* Radio buttons (navigation) styling */
    [data-testid="stSidebar"] .stRadio > div {
        gap: 8px;
    }

    [data-testid="stSidebar"] .stRadio label {
        background-color: transparent;
        padding: 12px 16px;
        border-radius: 8px;
        transition: all 0.2s ease;
        cursor: pointer;
        font-size: 15px;
        font-weight: 500;
    }

    [data-testid="stSidebar"] .stRadio label:hover {
        background-color: rgba(255, 255, 255, 0.1);
    }

    [data-testid="stSidebar"] .stRadio input:checked + label {
        background-color: #1b6ff5;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(27, 111, 245, 0.3);
    }

    /* MODE badge */
    .mode-badge {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
        padding: 10px 16px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 12px;
        text-align: center;
        margin-top: 24px;
        margin-bottom: 24px;
        box-shadow: 0 2px 8px rgba(245, 158, 11, 0.3);
    }

    .mode-badge small {
        display: block;
        margin-top: 4px;
        font-size: 10px;
        font-weight: 400;
        opacity: 0.9;
    }

    /* Sidebar footer */
    [data-testid="stSidebar"] .element-container:last-child p {
        text-align: center;
        font-size: 11px;
        opacity: 0.6;
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        # Logo + Titre
        st.markdown("# 🔍 Scraper-Pro")
        st.markdown("---")

        # Navigation pages MODE 2 uniquement (pas Google Search/Maps)
        pages = {
            'custom_urls': {'icon': '🔗', 'label': i18n.t('sidebar.customUrls')},
            'blog_content': {'icon': '📝', 'label': i18n.t('sidebar.blogContent')},
            'jobs': {'icon': '📋', 'label': i18n.t('sidebar.jobs')},
            'contacts': {'icon': '👥', 'label': i18n.t('sidebar.contacts')},
            'stats': {'icon': '📊', 'label': i18n.t('sidebar.stats')},
            'config': {'icon': '⚙️', 'label': i18n.t('sidebar.config')},
        }

        selected_page = st.radio(
            "Navigation",
            options=list(pages.keys()),
            format_func=lambda x: f"{pages[x]['icon']}  {pages[x]['label']}",
            index=list(pages.keys()).index(current_page) if current_page in pages else 0,
            label_visibility="collapsed",
            key="sidebar_navigation"
        )

        st.markdown("---")

        # Badge MODE 2
        st.markdown(f"""
        <div class="mode-badge">
            🎯 MODE 2 - SIMPLE<br/>
            <small>{i18n.t('sidebar.modeDescription')}</small>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # System info
        st.caption(f"v1.1.0 | {i18n.t('sidebar.footer')}")

        return selected_page


def render_header(i18n: I18nManager, page_title: str):
    """
    Affiche le header avec titre + language toggle.

    Args:
        i18n: Gestionnaire de traductions
        page_title: Titre de la page actuelle
    """
    # Custom CSS pour le header
    st.markdown("""
    <style>
    /* Header styling */
    .main .block-container {
        padding-top: 2rem;
    }

    /* Title styling */
    h1 {
        color: #1e293b;
        font-weight: 700;
    }

    /* Language pills styling */
    .stPills {
        background: rgba(15, 23, 42, 0.05);
        padding: 6px;
        border-radius: 10px;
    }

    .stPills button {
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 14px;
        transition: all 0.2s ease;
    }

    .stPills button[data-baseweb="tab"]:hover {
        background-color: rgba(27, 111, 245, 0.1);
    }

    .stPills button[aria-selected="true"] {
        background: linear-gradient(135deg, #1b6ff5 0%, #59b2ff 100%);
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])

    with col1:
        st.title(page_title)

    with col2:
        i18n.render_language_switcher()

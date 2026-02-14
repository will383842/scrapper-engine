"""Metrics cards component for dashboard."""
import streamlit as st
from typing import List, Dict, Any


def render_metrics_row(i18n, metrics: List[Dict[str, Any]]):
    """
    Affiche une ligne de métriques avec style moderne.

    Args:
        i18n: Gestionnaire de traductions (pour futurs labels)
        metrics: Liste de dicts avec keys: label, value, delta (optionnel)

    Example:
        >>> render_metrics_row(i18n, [
        ...     {'label': 'Total Jobs', 'value': 42},
        ...     {'label': 'Running', 'value': 5, 'delta': '+2'},
        ... ])
    """
    # Custom CSS pour les metrics cards
    st.markdown("""
    <style>
    /* Metrics cards styling */
    [data-testid="stMetric"] {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #1b6ff5;
        transition: all 0.2s ease;
    }

    [data-testid="stMetric"]:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        transform: translateY(-2px);
    }

    [data-testid="stMetric"] label {
        color: #64748b;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #1e293b;
        font-size: 28px;
        font-weight: 700;
    }
    </style>
    """, unsafe_allow_html=True)

    # Créer les colonnes
    cols = st.columns(len(metrics))

    for i, metric in enumerate(metrics):
        with cols[i]:
            st.metric(
                label=metric.get('label', ''),
                value=metric.get('value', 0),
                delta=metric.get('delta')
            )

"""Streamlit dashboard for scraper-pro."""

import os

import streamlit as st

st.set_page_config(
    page_title="Scraper-Pro Dashboard",
    page_icon="🔍",
    layout="wide",
)

# Simple auth
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("Scraper-Pro Dashboard")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if password == os.getenv("DASHBOARD_PASSWORD", "admin"):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Invalid password")
    st.stop()

# Main dashboard
st.title("Scraper-Pro Dashboard")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["Jobs", "Contacts", "Stats"])

with tab1:
    st.header("Scraping Jobs")
    st.info("Job management interface - connect to PostgreSQL to display data")

with tab2:
    st.header("Contacts Pipeline")
    st.info("Contact validation and sync status - connect to PostgreSQL to display data")

with tab3:
    st.header("Statistics")
    st.info("Pipeline statistics - connect to PostgreSQL to display data")

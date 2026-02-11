"""Streamlit admin dashboard for scraper-pro."""

import csv
import hashlib
import hmac
import io
import json
import os
import time
from urllib.parse import quote_plus

import requests
import streamlit as st
from sqlalchemy import create_engine, text

st.set_page_config(
    page_title="Scraper-Pro Admin",
    page_icon="🔍",
    layout="wide",
)

# ─── Database helpers ─────────────────────────────────


def get_db_url() -> str:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "scraper_db")
    user = os.getenv("POSTGRES_USER", "scraper_admin")
    password = os.getenv("POSTGRES_PASSWORD", "")
    return f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{db}"


@st.cache_resource
def get_engine():
    return create_engine(get_db_url(), pool_pre_ping=True)


def query_df(sql: str, params: dict | None = None):
    """Execute SQL and return list of dicts."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        return [dict(row._mapping) for row in result]


def query_scalar(sql: str, params: dict | None = None):
    """Execute SQL and return single scalar value."""
    engine = get_engine()
    with engine.connect() as conn:
        return conn.execute(text(sql), params or {}).scalar() or 0


# ─── API helpers ──────────────────────────────────────

SCRAPER_API_URL = os.getenv("SCRAPER_API_URL", "http://scraper:8000")
API_HMAC_SECRET = os.getenv("API_HMAC_SECRET", "")


def api_request(method: str, path: str, json_data: dict | None = None) -> dict:
    """HMAC-signed request to scraper API."""
    url = f"{SCRAPER_API_URL}{path}"
    ts = str(int(time.time()))
    body_str = json.dumps(json_data) if json_data else ""

    sig = hmac.new(
        API_HMAC_SECRET.encode(), f"{ts}.{body_str}".encode(), hashlib.sha256
    ).hexdigest()

    headers = {
        "X-Signature": sig,
        "X-Timestamp": ts,
        "Content-Type": "application/json",
    }

    resp = requests.request(method, url, headers=headers, json=json_data, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ─── Auth ─────────────────────────────────────────────

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("Scraper-Pro Admin")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        dashboard_pw = os.getenv("DASHBOARD_PASSWORD", "")
        if not dashboard_pw:
            st.error("DASHBOARD_PASSWORD not configured")
        elif hmac.compare_digest(password.encode(), dashboard_pw.encode()):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Invalid password")
    st.stop()

# ─── Main Dashboard ──────────────────────────────────

st.title("Scraper-Pro Admin")
st.markdown("---")

tab_jobs, tab_contacts, tab_articles, tab_stats, tab_whois, tab_config = st.tabs(
    ["Jobs", "Contacts", "Articles", "Stats", "WHOIS Lookup", "Configuration"]
)

# ─── Tab 1: Jobs ─────────────────────────────────────

with tab_jobs:
    st.header("Scraping Jobs")

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
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Jobs", len(jobs))
            col2.metric("Running", sum(1 for j in jobs if j["status"] == "running"))
            col3.metric("Completed", sum(1 for j in jobs if j["status"] == "completed"))
            col4.metric("Failed", sum(1 for j in jobs if j["status"] == "failed"))

            st.dataframe(
                jobs,
                use_container_width=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", width="small"),
                    "progress": st.column_config.ProgressColumn(
                        "Progress", min_value=0, max_value=100
                    ),
                },
            )

            # ── Job Control Actions ──
            st.markdown("---")
            st.subheader("Job Actions")

            ctrl_col1, ctrl_col2 = st.columns(2)
            with ctrl_col1:
                action_job_id = st.number_input(
                    "Job ID", min_value=1, step=1, key="action_job_id"
                )
            with ctrl_col2:
                action = st.selectbox(
                    "Action",
                    options=["resume", "pause", "cancel"],
                    format_func=lambda x: {
                        "resume": "Resume (from checkpoint)",
                        "pause": "Pause (running only)",
                        "cancel": "Cancel (stop permanently)",
                    }.get(x, x),
                    key="action_type",
                )

            if st.button("Execute Action", type="secondary", key="exec_action"):
                try:
                    result = api_request("POST", f"/api/v1/scraping/jobs/{action_job_id}/{action}")
                    st.success(f"Job #{action_job_id}: {result.get('status', 'done')}")
                    st.rerun()
                except requests.exceptions.HTTPError as e:
                    st.error(f"API error: {e.response.text if e.response else e}")
                except Exception as e:
                    st.error(f"Error: {e}")

        else:
            st.info("No scraping jobs yet.")
    except Exception as e:
        st.error(f"Database error: {e}")

    # ── New Job Form ──
    st.markdown("---")
    st.subheader("Launch New Job")

    with st.form("new_job_form"):
        job_name = st.text_input("Job name", value="Dashboard Job")

        source_type = st.selectbox(
            "Source type",
            options=["google_search", "google_maps", "custom_urls", "blog_content"],
            format_func=lambda x: {
                "google_search": "Google Search",
                "google_maps": "Google Maps",
                "custom_urls": "Custom URLs",
                "blog_content": "Blog Content",
            }.get(x, x),
        )

        # Dynamic fields per source type
        config = {}
        if source_type == "google_search":
            config["query"] = st.text_input("Search query", placeholder="avocats expatries France")
            config["max_results"] = st.number_input("Max results", min_value=10, max_value=500, value=100)
            gs_col1, gs_col2 = st.columns(2)
            with gs_col1:
                config["country"] = st.selectbox(
                    "Country",
                    options=["fr", "us", "uk", "de", "es", "be", "ch", "ca", "ma", "sn", "pt", "it", "nl", "br"],
                    key="gs_country",
                )
            with gs_col2:
                lang = st.selectbox(
                    "Language",
                    options=[None, "fr", "en", "es", "de", "pt", "it", "nl", "ar", "ru", "zh"],
                    format_func=lambda x: "Auto-detect" if x is None else {
                        "fr": "Francais", "en": "English", "es": "Espanol",
                        "de": "Deutsch", "pt": "Portugues", "it": "Italiano",
                        "nl": "Nederlands", "ar": "Arabic", "ru": "Russian", "zh": "Chinese",
                    }.get(x, x),
                    key="gs_lang",
                )
                if lang:
                    config["language"] = lang
        elif source_type == "google_maps":
            config["query"] = st.text_input("Maps query", placeholder="avocat international Paris")
            config["location"] = st.text_input("Location", placeholder="Paris, France")
            config["max_results"] = st.number_input("Max results", min_value=10, max_value=200, value=50)
            gm_lang = st.selectbox(
                "Language",
                options=[None, "fr", "en", "es", "de", "pt", "it"],
                format_func=lambda x: "Auto-detect" if x is None else x.upper(),
                key="gm_lang",
            )
            if gm_lang:
                config["language"] = gm_lang
        elif source_type == "blog_content":
            config["start_url"] = st.text_input("Blog URL", placeholder="https://www.expat.com/blog/")
            config["max_articles"] = st.number_input("Max articles", min_value=10, max_value=1000, value=100)
            config["scrape_depth"] = st.number_input("Scrape depth", min_value=1, max_value=5, value=2)
        else:  # custom_urls
            urls_text = st.text_area("URLs (one per line)", height=150)
            config["urls"] = [u.strip() for u in urls_text.splitlines() if u.strip()]

        col_cat, col_plat = st.columns(2)
        with col_cat:
            category = st.selectbox(
                "Category",
                options=[
                    None, "avocat", "assureur", "notaire", "medecin",
                    "comptable", "traducteur", "agent_immo", "demenageur",
                    "banquier", "consultant",
                    "blogueur", "influenceur", "youtubeur", "admin_groupe",
                ],
                format_func=lambda x: "Auto-detect" if x is None else {
                    "agent_immo": "Agent Immobilier",
                    "admin_groupe": "Admin Groupe",
                }.get(x, x.capitalize()),
            )
        with col_plat:
            platform = st.selectbox(
                "Platform",
                options=[None, "sos-expat", "ulixai"],
                format_func=lambda x: "Auto-detect" if x is None else x,
            )

        auto_inject = st.checkbox("Auto-inject to MailWizz", value=True)

        submitted = st.form_submit_button("Launch Job", type="primary")

    if submitted:
        if source_type in ("google_search", "google_maps") and not config.get("query"):
            st.error("Search query is required.")
        elif source_type == "custom_urls" and not config.get("urls"):
            st.error("At least one URL is required.")
        elif source_type == "blog_content" and not config.get("start_url"):
            st.error("Blog URL is required.")
        else:
            try:
                result = api_request("POST", "/api/v1/scraping/jobs", {
                    "source_type": source_type,
                    "name": job_name,
                    "config": config,
                    "category": category,
                    "platform": platform,
                    "tags": [],
                    "auto_inject_mailwizz": auto_inject,
                })
                st.success(f"Job created! ID: {result['job_id']} - Status: {result['status']}")
                st.rerun()
            except requests.exceptions.HTTPError as e:
                st.error(f"API error: {e.response.text if e.response else e}")
            except Exception as e:
                st.error(f"Error: {e}")


# ─── Tab 2: Contacts ────────────────────────────────

with tab_contacts:
    st.header("Contacts Pipeline")

    try:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Scraped", query_scalar("SELECT COUNT(*) FROM scraped_contacts"))
        col2.metric("Validated", query_scalar("SELECT COUNT(*) FROM validated_contacts"))
        col3.metric(
            "Sent to MailWizz",
            query_scalar("SELECT COUNT(*) FROM validated_contacts WHERE status = 'sent_to_mailwizz'"),
        )
        col4.metric(
            "Bounced",
            query_scalar("SELECT COUNT(*) FROM validated_contacts WHERE status = 'bounced'"),
        )

        st.subheader("By Platform")
        by_platform = query_df("""
            SELECT platform, category, COUNT(*) as count
            FROM validated_contacts
            GROUP BY platform, category
            ORDER BY platform, count DESC
        """)
        if by_platform:
            st.dataframe(by_platform, use_container_width=True)
        else:
            st.info("No validated contacts yet.")

        st.subheader("Pending Validation")
        pending = query_scalar(
            "SELECT COUNT(*) FROM scraped_contacts WHERE status = 'pending_validation'"
        )
        st.metric("Pending", pending)

    except Exception as e:
        st.error(f"Database error: {e}")

    # ── Contact Search ──
    st.markdown("---")
    st.subheader("Search Contacts")

    search_col1, search_col2, search_col3, search_col4 = st.columns(4)
    with search_col1:
        search_email = st.text_input("Email contains", placeholder="@example.com", key="search_email")
    with search_col2:
        search_name = st.text_input("Name contains", placeholder="dupont", key="search_name")
    with search_col3:
        search_category = st.selectbox(
            "Category",
            options=[
                "all", "avocat", "assureur", "notaire", "medecin",
                "comptable", "traducteur", "agent_immo", "demenageur",
                "banquier", "consultant",
                "blogueur", "influenceur", "youtubeur", "admin_groupe",
            ],
            key="search_cat",
        )
    with search_col4:
        search_status = st.selectbox(
            "Status",
            options=["all", "ready_for_mailwizz", "sent_to_mailwizz", "bounced", "failed"],
            key="search_status",
        )

    if st.button("Search", type="primary", key="search_btn"):
        try:
            where_parts = []
            s_params = {}

            if search_email:
                where_parts.append("email ILIKE :email")
                s_params["email"] = f"%{search_email}%"
            if search_name:
                where_parts.append("name ILIKE :name")
                s_params["name"] = f"%{search_name}%"
            if search_category != "all":
                where_parts.append("category = :category")
                s_params["category"] = search_category
            if search_status != "all":
                where_parts.append("status = :status")
                s_params["status"] = search_status

            where_sql = "WHERE " + " AND ".join(where_parts) if where_parts else ""

            results = query_df(
                f"""
                SELECT id, email, name, phone, website, category, platform,
                       country, status, tags, mailwizz_list_id,
                       created_at, sent_to_mailwizz_at
                FROM validated_contacts
                {where_sql}
                ORDER BY created_at DESC
                LIMIT 100
                """,
                s_params,
            )

            if results:
                st.success(f"{len(results)} contacts found (showing max 100)")
                st.dataframe(
                    results,
                    use_container_width=True,
                    column_config={
                        "id": st.column_config.NumberColumn("ID", width="small"),
                        "website": st.column_config.LinkColumn("Website", width="medium"),
                    },
                )

                # Contact detail
                st.markdown("---")
                st.subheader("Contact Detail")
                contact_ids = [r["id"] for r in results]
                selected_cid = st.selectbox("Select contact ID", options=contact_ids, key="contact_detail")

                if selected_cid:
                    detail = query_df(
                        """
                        SELECT email, name, phone, website, address,
                               social_media, category, platform, country,
                               tags, email_valid, phone_valid,
                               mailwizz_list_id, mailwizz_subscriber_id,
                               status, retry_count, last_error,
                               created_at, last_validated_at, sent_to_mailwizz_at
                        FROM validated_contacts WHERE id = :id
                        """,
                        {"id": selected_cid},
                    )
                    if detail:
                        d = detail[0]
                        dc1, dc2 = st.columns(2)
                        with dc1:
                            st.markdown(f"**Email:** {d.get('email', 'N/A')}")
                            st.markdown(f"**Name:** {d.get('name', 'N/A')}")
                            st.markdown(f"**Phone:** {d.get('phone', 'N/A')} {'(valid)' if d.get('phone_valid') else '(not validated)'}")
                            st.markdown(f"**Website:** {d.get('website', 'N/A')}")
                            st.markdown(f"**Address:** {d.get('address', 'N/A')}")
                            st.markdown(f"**Country:** {d.get('country', 'N/A')}")
                        with dc2:
                            st.markdown(f"**Category:** {d.get('category', 'N/A')}")
                            st.markdown(f"**Platform:** {d.get('platform', 'N/A')}")
                            st.markdown(f"**Status:** {d.get('status', 'N/A')}")
                            st.markdown(f"**MailWizz List:** #{d.get('mailwizz_list_id', 'N/A')}")
                            st.markdown(f"**MailWizz UID:** {d.get('mailwizz_subscriber_id', 'N/A')}")
                            st.markdown(f"**Tags:** {d.get('tags', '[]')}")

                        social = d.get("social_media", "{}")
                        if social and social != "{}":
                            if isinstance(social, str):
                                try:
                                    social = json.loads(social)
                                except (json.JSONDecodeError, TypeError):
                                    social = {}
                            if social:
                                st.markdown("**Social Media:**")
                                for platform_name, url in social.items():
                                    st.markdown(f"- {platform_name}: [{url}]({url})")

                        if d.get("last_error"):
                            st.error(f"Last error: {d['last_error']}")
            else:
                st.warning("No contacts match these filters.")
        except Exception as e:
            st.error(f"Search error: {e}")

    # ── CSV Export ──
    st.markdown("---")
    st.subheader("Export Contacts CSV")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        export_status = st.selectbox(
            "Status filter",
            options=["all", "validated", "sent_to_mailwizz", "bounced"],
        )
    with col_f2:
        export_platform = st.selectbox(
            "Platform filter",
            options=["all", "sos-expat", "ulixai"],
        )
    with col_f3:
        export_category = st.selectbox(
            "Category filter",
            options=[
                "all", "avocat", "assureur", "notaire", "medecin",
                "comptable", "traducteur", "agent_immo", "demenageur",
                "banquier", "consultant",
                "blogueur", "influenceur", "youtubeur", "admin_groupe",
            ],
        )

    if st.button("Generate CSV"):
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
                st.warning("No contacts match these filters.")
            else:
                buf = io.StringIO()
                buf.write("\ufeff")  # BOM for Excel UTF-8
                writer = csv.DictWriter(buf, fieldnames=contacts[0].keys())
                writer.writeheader()
                writer.writerows(contacts)

                st.download_button(
                    label=f"Download ({len(contacts)} contacts)",
                    data=buf.getvalue().encode("utf-8"),
                    file_name="contacts_export.csv",
                    mime="text/csv",
                )
        except Exception as e:
            st.error(f"Export error: {e}")


# ─── Tab 3: Articles ─────────────────────────────────

with tab_articles:
    st.header("Scraped Articles")

    try:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Articles", query_scalar("SELECT COUNT(*) FROM scraped_articles"))
        col2.metric(
            "Unique Domains",
            query_scalar("SELECT COUNT(DISTINCT domain) FROM scraped_articles"),
        )
        col3.metric(
            "Avg Words",
            query_scalar("SELECT COALESCE(ROUND(AVG(word_count)), 0) FROM scraped_articles"),
        )
        col4.metric(
            "This Week",
            query_scalar(
                "SELECT COUNT(*) FROM scraped_articles WHERE scraped_at > NOW() - INTERVAL '7 days'"
            ),
        )

        # Filters
        st.markdown("---")
        col_f1, col_f2, col_f3 = st.columns(3)

        with col_f1:
            domains = query_df(
                "SELECT DISTINCT domain FROM scraped_articles ORDER BY domain"
            )
            domain_options = ["all"] + [d["domain"] for d in domains]
            art_domain = st.selectbox("Domain", options=domain_options, key="art_domain")

        with col_f2:
            languages = query_df(
                "SELECT DISTINCT language FROM scraped_articles WHERE language IS NOT NULL ORDER BY language"
            )
            lang_options = ["all"] + [l["language"] for l in languages]
            art_lang = st.selectbox("Language", options=lang_options, key="art_lang")

        with col_f3:
            art_sort = st.selectbox(
                "Sort by",
                options=["scraped_at DESC", "word_count DESC", "title ASC", "date_published DESC"],
                format_func=lambda x: {
                    "scraped_at DESC": "Newest scraped",
                    "word_count DESC": "Most words",
                    "title ASC": "Title A-Z",
                    "date_published DESC": "Newest published",
                }.get(x, x),
                key="art_sort",
            )

        # Build query
        where_clauses = []
        params = {}
        if art_domain != "all":
            where_clauses.append("domain = :domain")
            params["domain"] = art_domain
        if art_lang != "all":
            where_clauses.append("language = :language")
            params["language"] = art_lang

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        articles = query_df(
            f"""
            SELECT id, title, domain, language, word_count, author,
                   date_published, scraped_at, url
            FROM scraped_articles
            {where_sql}
            ORDER BY {art_sort}
            LIMIT 100
            """,
            params,
        )

        if articles:
            st.dataframe(
                articles,
                use_container_width=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", width="small"),
                    "url": st.column_config.LinkColumn("URL", width="medium"),
                    "word_count": st.column_config.NumberColumn("Words"),
                },
            )

            # Article detail expander
            st.markdown("---")
            st.subheader("Article Detail")
            article_ids = [a["id"] for a in articles]
            selected_id = st.selectbox("Select article ID", options=article_ids, key="art_detail")

            if selected_id:
                detail = query_df(
                    """
                    SELECT title, url, content_text, author, date_published,
                           language, word_count, meta_description,
                           external_links, categories, tags
                    FROM scraped_articles WHERE id = :id
                    """,
                    {"id": selected_id},
                )
                if detail:
                    d = detail[0]
                    st.markdown(f"### {d.get('title', 'Untitled')}")
                    st.caption(
                        f"By {d.get('author', 'Unknown')} | "
                        f"{d.get('date_published', 'N/A')} | "
                        f"{d.get('word_count', 0)} words | "
                        f"{d.get('language', 'N/A')}"
                    )
                    if d.get("meta_description"):
                        st.info(d["meta_description"])

                    with st.expander("Full content", expanded=False):
                        st.text(d.get("content_text", "")[:5000])
                        if len(d.get("content_text", "")) > 5000:
                            st.caption("... (truncated at 5000 chars)")

                    ext_links = d.get("external_links", [])
                    if isinstance(ext_links, str):
                        try:
                            ext_links = json.loads(ext_links)
                        except (json.JSONDecodeError, TypeError):
                            ext_links = []
                    if ext_links:
                        with st.expander(f"External links ({len(ext_links)})"):
                            for link in ext_links[:20]:
                                url = link.get("url", link) if isinstance(link, dict) else link
                                st.markdown(f"- [{url}]({url})")
        else:
            st.info("No articles scraped yet.")

    except Exception as e:
        st.error(f"Database error: {e}")

    # ── Export ──
    st.markdown("---")
    st.subheader("Export Articles")

    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        if st.button("Export CSV", key="art_csv"):
            try:
                all_articles = query_df(
                    f"""
                    SELECT url, title, domain, language, word_count, author,
                           date_published, meta_description, scraped_at
                    FROM scraped_articles
                    {where_sql}
                    ORDER BY {art_sort}
                    """,
                    params,
                )
                if not all_articles:
                    st.warning("No articles to export.")
                else:
                    buf = io.StringIO()
                    buf.write("\ufeff")  # BOM for Excel UTF-8
                    writer = csv.DictWriter(buf, fieldnames=all_articles[0].keys())
                    writer.writeheader()
                    writer.writerows(all_articles)
                    st.download_button(
                        label=f"Download CSV ({len(all_articles)} articles)",
                        data=buf.getvalue().encode("utf-8"),
                        file_name="articles_export.csv",
                        mime="text/csv",
                        key="art_csv_dl",
                    )
            except Exception as e:
                st.error(f"Export error: {e}")

    with col_exp2:
        if st.button("Export JSON", key="art_json"):
            try:
                all_articles = query_df(
                    f"""
                    SELECT url, title, content_text, domain, language, word_count,
                           author, date_published, meta_description, external_links,
                           internal_links, categories, tags, scraped_at
                    FROM scraped_articles
                    {where_sql}
                    ORDER BY {art_sort}
                    """,
                    params,
                )
                if not all_articles:
                    st.warning("No articles to export.")
                else:
                    # Convert datetime objects to strings for JSON
                    for a in all_articles:
                        for k, v in a.items():
                            if hasattr(v, "isoformat"):
                                a[k] = v.isoformat()
                    json_str = json.dumps(all_articles, ensure_ascii=False, indent=2)
                    st.download_button(
                        label=f"Download JSON ({len(all_articles)} articles)",
                        data=json_str.encode("utf-8"),
                        file_name="articles_export.json",
                        mime="application/json",
                        key="art_json_dl",
                    )
            except Exception as e:
                st.error(f"Export error: {e}")


# ─── Tab 4: Stats ────────────────────────────────────

with tab_stats:
    st.header("Pipeline Statistics")

    try:
        st.subheader("Daily Scraping Volume (last 30 days)")
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

        st.subheader("Daily MailWizz Sync (last 30 days)")
        daily_sync = query_df("""
            SELECT DATE(synced_at) as date, status, COUNT(*) as count
            FROM mailwizz_sync_log
            WHERE synced_at > NOW() - INTERVAL '30 days'
            GROUP BY DATE(synced_at), status
            ORDER BY date
        """)
        if daily_sync:
            st.dataframe(daily_sync, use_container_width=True)

        st.subheader("Domain Blacklist (top bouncing domains)")
        blacklist = query_df("""
            SELECT domain, bounce_count, total_sent, bounce_rate
            FROM email_domain_blacklist
            ORDER BY bounce_count DESC
            LIMIT 20
        """)
        if blacklist:
            st.dataframe(blacklist, use_container_width=True)
        else:
            st.info("No blacklisted domains yet.")

        st.subheader("WHOIS Intelligence")
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
            col1.metric("Total Lookups", ws["total_lookups"])
            col2.metric("Private WHOIS", ws["private_whois"])
            col3.metric("Cloudflare", ws["cloudflare"])
            col4.metric("Registrars", ws["unique_registrars"])

        top_registrars = query_df("""
            SELECT registrar, COUNT(*) as count
            FROM whois_cache
            WHERE registrar IS NOT NULL AND registrar != ''
            GROUP BY registrar
            ORDER BY count DESC
            LIMIT 10
        """)
        if top_registrars:
            st.subheader("Top Registrars")
            st.dataframe(top_registrars, use_container_width=True)

    except Exception as e:
        st.error(f"Database error: {e}")


# ─── Tab 5: WHOIS Lookup ─────────────────────────────

with tab_whois:
    st.header("WHOIS Domain Lookup")

    domain_input = st.text_input("Domain", placeholder="example.com")

    if st.button("Lookup", type="primary"):
        if not domain_input or "." not in domain_input:
            st.error("Enter a valid domain (e.g. example.com)")
        else:
            with st.spinner("Looking up WHOIS..."):
                try:
                    result = api_request("POST", "/api/v1/whois/lookup", {
                        "domain": domain_input.strip().lower(),
                    })

                    if result.get("lookup_status") == "failed":
                        st.warning(f"WHOIS lookup failed for {result.get('domain')}")
                    else:
                        # Header with badges
                        badges = []
                        if result.get("whois_private"):
                            badges.append(":red[Private WHOIS]")
                        if result.get("cloudflare_protected"):
                            badges.append(":orange[Cloudflare]")
                        badge_str = "  ".join(badges) if badges else ":green[Public WHOIS]"

                        st.markdown(f"### {result.get('domain')}  {badge_str}")

                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Registrar**")
                            st.write(result.get("registrar", "N/A"))
                            st.markdown("**Creation Date**")
                            st.write(result.get("creation_date", "N/A"))
                            st.markdown("**Expiration Date**")
                            st.write(result.get("expiration_date", "N/A"))

                        with col2:
                            if not result.get("whois_private"):
                                st.markdown("**Registrant**")
                                name = result.get("registrant_name", "")
                                org = result.get("registrant_org", "")
                                st.write(f"{name} - {org}" if name or org else "N/A")
                                st.markdown("**Email**")
                                st.write(result.get("registrant_email", "N/A"))
                            st.markdown("**Country**")
                            st.write(result.get("registrant_country", "N/A"))

                        ns = result.get("name_servers", [])
                        if ns:
                            if isinstance(ns, str):
                                try:
                                    ns = json.loads(ns)
                                except (json.JSONDecodeError, TypeError):
                                    ns = [ns]
                            st.markdown("**Name Servers**")
                            st.write(", ".join(ns))

                except requests.exceptions.HTTPError as e:
                    st.error(f"API error: {e.response.text if e.response else e}")
                except Exception as e:
                    st.error(f"Error: {e}")

    # ── Recent lookups ──
    st.markdown("---")
    st.subheader("Recent Lookups")
    try:
        lookups = query_df("""
            SELECT domain, registrar, whois_private, cloudflare_protected,
                   lookup_status, looked_up_at
            FROM whois_cache
            ORDER BY looked_up_at DESC
            LIMIT 20
        """)
        if lookups:
            st.dataframe(lookups, use_container_width=True)
        else:
            st.info("No WHOIS lookups yet.")
    except Exception as e:
        st.error(f"Database error: {e}")


# ─── Tab 6: Configuration ────────────────────────────

with tab_config:
    st.header("System Configuration")

    # Health check
    st.subheader("System Health")
    try:
        health = api_request("GET", "/health")
        col1, col2, col3 = st.columns(3)
        api_ok = health.get("status") == "ok"
        col1.metric("API", "OK" if api_ok else "Degraded")
        col2.metric("PostgreSQL", "OK" if health.get("postgres") else "DOWN")
        col3.metric("Redis", "OK" if health.get("redis") else "DOWN")
    except Exception:
        st.warning("Cannot reach scraper API")

    # Proxy config
    st.subheader("Active Configuration")
    st.markdown("**Proxy Provider**")
    st.code(os.getenv("PROXY_PROVIDER", "not set"))

    # MailWizz routing
    st.markdown("**MailWizz Routing**")
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
            st.info("No platforms configured yet.")
    except Exception:
        pass

    # Environment info
    st.subheader("Environment")
    env_info = {
        "SCRAPER_API_URL": SCRAPER_API_URL,
        "POSTGRES_HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "POSTGRES_DB": os.getenv("POSTGRES_DB", "scraper_db"),
        "API_HMAC_SECRET": "configured" if API_HMAC_SECRET else "NOT SET",
        "DASHBOARD_PASSWORD": "configured" if os.getenv("DASHBOARD_PASSWORD") else "NOT SET",
    }
    st.json(env_info)

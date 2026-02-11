"""WHOIS domain intelligence module.

Looks up domain registration info: registrar, privacy status,
Cloudflare protection, registrant contact details.
"""

import logging
import re
from datetime import datetime

from scraper.database import get_db_session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Known privacy/proxy registrant patterns
PRIVACY_INDICATORS = [
    "whoisguard", "privacy", "protected", "redacted",
    "withheld", "data protected", "contact privacy",
    "domains by proxy", "whois privacy", "perfect privacy",
    "identity protect", "registrant not identified",
]

# Cloudflare registrar identifiers
CLOUDFLARE_INDICATORS = [
    "cloudflare", "cloudflare, inc.",
]

# Common registrars
KNOWN_REGISTRARS = {
    "cloudflare": "Cloudflare, Inc.",
    "godaddy": "GoDaddy.com, LLC",
    "namecheap": "NameCheap, Inc.",
    "ovh": "OVH SAS",
    "gandi": "Gandi SAS",
    "google": "Google Domains",
    "name.com": "Name.com, Inc.",
    "1and1": "1&1 IONOS SE",
    "register.com": "Register.com, Inc.",
    "enom": "eNom, LLC",
    "tucows": "Tucows Domains Inc.",
    "key-systems": "Key-Systems GmbH",
}


def lookup_whois(domain: str) -> dict:
    """
    Perform WHOIS lookup for a domain.
    Uses python-whois library, caches results in DB.

    Returns dict with:
        registrar, whois_private, cloudflare_protected,
        registrant_name, registrant_org, registrant_email,
        registrant_country, creation_date, expiration_date
    """
    # Check cache first
    cached = _get_cached(domain)
    if cached:
        return cached

    try:
        import whois
        w = whois.whois(domain)
    except Exception as e:
        logger.warning(f"WHOIS lookup failed for {domain}: {e}")
        result = {"domain": domain, "lookup_status": "failed"}
        _cache_result(domain, result)
        return result

    registrar = w.registrar or ""
    registrant_name = ""
    registrant_org = ""
    registrant_email = ""
    registrant_country = ""

    # Extract registrant info
    if hasattr(w, "name") and w.name:
        registrant_name = w.name if isinstance(w.name, str) else w.name[0]
    if hasattr(w, "org") and w.org:
        registrant_org = w.org if isinstance(w.org, str) else w.org[0]
    if hasattr(w, "emails") and w.emails:
        emails = w.emails if isinstance(w.emails, list) else [w.emails]
        registrant_email = emails[0] if emails else ""
    if hasattr(w, "country") and w.country:
        registrant_country = w.country if isinstance(w.country, str) else w.country[0]

    # Detect privacy protection
    whois_private = _detect_privacy(w, registrant_name, registrant_org, registrant_email)

    # Detect Cloudflare
    cloudflare_protected = _detect_cloudflare(registrar, w)

    # Parse dates
    creation_date = _parse_date(w.creation_date)
    expiration_date = _parse_date(w.expiration_date)

    # Name servers
    name_servers = []
    if hasattr(w, "name_servers") and w.name_servers:
        ns = w.name_servers
        if isinstance(ns, list):
            name_servers = [str(n).lower() for n in ns]
        else:
            name_servers = [str(ns).lower()]

    result = {
        "domain": domain,
        "registrar": registrar,
        "whois_private": whois_private,
        "cloudflare_protected": cloudflare_protected,
        "registrant_name": registrant_name if not whois_private else "",
        "registrant_org": registrant_org if not whois_private else "",
        "registrant_email": registrant_email if not whois_private else "",
        "registrant_country": registrant_country,
        "creation_date": creation_date,
        "expiration_date": expiration_date,
        "name_servers": name_servers,
        "lookup_status": "success",
    }

    _cache_result(domain, result)
    return result


def _detect_privacy(whois_data, name: str, org: str, email: str) -> bool:
    """Detect if WHOIS privacy protection is active."""
    combined = f"{name} {org} {email}".lower()
    raw = str(getattr(whois_data, "text", "")).lower()

    for indicator in PRIVACY_INDICATORS:
        if indicator in combined or indicator in raw:
            return True

    # REDACTED FOR PRIVACY pattern (GDPR)
    if "redacted" in combined or "not disclosed" in combined:
        return True

    return False


def _detect_cloudflare(registrar: str, whois_data) -> bool:
    """Detect if domain uses Cloudflare (registrar or nameservers)."""
    if any(cf in registrar.lower() for cf in CLOUDFLARE_INDICATORS):
        return True

    # Check nameservers
    ns = getattr(whois_data, "name_servers", None)
    if ns:
        ns_list = ns if isinstance(ns, list) else [ns]
        for n in ns_list:
            if "cloudflare" in str(n).lower():
                return True

    return False


def _parse_date(date_val) -> str | None:
    """Parse WHOIS date which can be str, datetime, or list."""
    if not date_val:
        return None
    if isinstance(date_val, list):
        date_val = date_val[0]
    if isinstance(date_val, datetime):
        return date_val.isoformat()
    return str(date_val)


def _get_cached(domain: str) -> dict | None:
    """Get cached WHOIS result from DB (max 30 days old)."""
    try:
        with get_db_session() as session:
            row = session.execute(
                text("""
                    SELECT * FROM whois_cache
                    WHERE domain = :domain
                    AND looked_up_at > NOW() - INTERVAL '30 days'
                """),
                {"domain": domain},
            ).mappings().first()
            if row:
                return dict(row)
    except Exception:
        pass
    return None


def _cache_result(domain: str, result: dict):
    """Cache WHOIS result in DB."""
    import json
    try:
        with get_db_session() as session:
            session.execute(
                text("""
                    INSERT INTO whois_cache
                        (domain, registrar, whois_private, cloudflare_protected,
                         registrant_name, registrant_org, registrant_email,
                         registrant_country, name_servers, lookup_status,
                         creation_date, expiration_date)
                    VALUES
                        (:domain, :registrar, :whois_private, :cloudflare_protected,
                         :registrant_name, :registrant_org, :registrant_email,
                         :registrant_country, :name_servers, :lookup_status,
                         :creation_date, :expiration_date)
                    ON CONFLICT (domain) DO UPDATE SET
                        registrar = EXCLUDED.registrar,
                        whois_private = EXCLUDED.whois_private,
                        cloudflare_protected = EXCLUDED.cloudflare_protected,
                        registrant_name = EXCLUDED.registrant_name,
                        registrant_org = EXCLUDED.registrant_org,
                        registrant_email = EXCLUDED.registrant_email,
                        registrant_country = EXCLUDED.registrant_country,
                        name_servers = EXCLUDED.name_servers,
                        lookup_status = EXCLUDED.lookup_status,
                        creation_date = EXCLUDED.creation_date,
                        expiration_date = EXCLUDED.expiration_date,
                        looked_up_at = NOW()
                """),
                {
                    "domain": domain,
                    "registrar": result.get("registrar", ""),
                    "whois_private": result.get("whois_private", False),
                    "cloudflare_protected": result.get("cloudflare_protected", False),
                    "registrant_name": result.get("registrant_name", ""),
                    "registrant_org": result.get("registrant_org", ""),
                    "registrant_email": result.get("registrant_email", ""),
                    "registrant_country": result.get("registrant_country", ""),
                    "name_servers": json.dumps(result.get("name_servers", [])),
                    "lookup_status": result.get("lookup_status", "success"),
                    "creation_date": result.get("creation_date"),
                    "expiration_date": result.get("expiration_date"),
                },
            )
    except Exception as e:
        logger.debug(f"Failed to cache WHOIS for {domain}: {e}")

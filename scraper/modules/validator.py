"""Email and phone validation module."""

import re
import logging

import dns.resolver
import phonenumbers

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

EMAIL_BLACKLIST_PREFIXES = [
    "noreply", "no-reply", "donotreply", "admin", "webmaster",
    "postmaster", "hostmaster", "abuse", "spam", "test",
    "mailer-daemon", "root", "nobody", "www",
]

# Disposable email domains (top ones)
DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "tempmail.com", "throwaway.email",
    "yopmail.com", "sharklasers.com", "guerrillamailblock.com", "trashmail.com",
    "10minutemail.com", "temp-mail.org",
}

# MX record cache to avoid repeated lookups
_mx_cache: dict[str, bool] = {}


def validate_email(email: str) -> bool:
    """
    Validate email in 2 steps:
    1. Format regex
    2. DNS MX record exists

    No SMTP check (avoids IP blacklisting).
    """
    if not email or not isinstance(email, str):
        return False

    email = email.lower().strip()

    # Step 1: Regex format
    if not EMAIL_RE.match(email):
        return False

    local_part = email.split("@")[0]
    domain = email.split("@")[1]

    # Blacklisted prefixes
    if any(local_part.startswith(bl) for bl in EMAIL_BLACKLIST_PREFIXES):
        return False

    # Disposable domains
    if domain in DISPOSABLE_DOMAINS:
        return False

    # Step 2: DNS MX check (cached)
    if domain in _mx_cache:
        return _mx_cache[domain]

    try:
        mx_records = dns.resolver.resolve(domain, "MX")
        has_mx = len(mx_records) > 0
        _mx_cache[domain] = has_mx
        return has_mx
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        _mx_cache[domain] = False
        return False
    except Exception as e:
        logger.debug(f"DNS MX check error for {domain}: {e}")
        # On error, consider valid (don't lose contacts due to DNS hiccup)
        return True


def validate_phone(phone: str, country_code: str = None) -> bool:
    """Validate phone number format."""
    if not phone:
        return False

    try:
        parsed = phonenumbers.parse(phone, country_code)
        return phonenumbers.is_valid_number(parsed)
    except Exception:
        return False


def clean_phone(phone: str) -> str | None:
    """Clean and normalize phone number."""
    if not phone:
        return None

    cleaned = re.sub(r"[^\d+]", "", phone)

    # Minimum 8 digits
    if len(cleaned.replace("+", "")) < 8:
        return None

    return cleaned

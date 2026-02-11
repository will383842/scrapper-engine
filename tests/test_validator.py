"""Tests for the email/phone validation module."""

from scraper.modules.validator import validate_email, validate_phone, clean_phone
from unittest.mock import patch, MagicMock


class TestValidateEmail:
    def test_valid_email(self):
        with patch("scraper.modules.validator.dns.resolver.resolve") as mock_dns:
            mock_dns.return_value = [MagicMock()]
            assert validate_email("john@example.com") is True

    def test_invalid_format(self):
        assert validate_email("not-an-email") is False
        assert validate_email("missing@domain") is False
        assert validate_email("") is False
        assert validate_email(None) is False

    def test_blacklisted_prefix(self):
        assert validate_email("noreply@example.com") is False
        assert validate_email("admin@example.com") is False
        assert validate_email("webmaster@example.com") is False
        assert validate_email("postmaster@example.com") is False
        assert validate_email("abuse@example.com") is False

    def test_disposable_domain(self):
        assert validate_email("user@mailinator.com") is False
        assert validate_email("user@yopmail.com") is False
        assert validate_email("user@guerrillamail.com") is False

    def test_dns_failure_returns_true(self):
        """On DNS error, we keep the contact (don't lose it)."""
        with patch("scraper.modules.validator.dns.resolver.resolve") as mock_dns:
            mock_dns.side_effect = Exception("DNS timeout")
            assert validate_email("user@unknown-domain.xyz") is True


class TestValidatePhone:
    def test_valid_phone(self):
        assert validate_phone("+33612345678", "FR") is True

    def test_invalid_phone(self):
        assert validate_phone("123", "FR") is False
        assert validate_phone("", None) is False
        assert validate_phone(None, None) is False


class TestCleanPhone:
    def test_clean_valid(self):
        assert clean_phone("+33 6 12 34 56 78") == "+33612345678"
        assert clean_phone("06.12.34.56.78") == "0612345678"

    def test_too_short(self):
        assert clean_phone("123") is None

    def test_none_input(self):
        assert clean_phone(None) is None
        assert clean_phone("") is None

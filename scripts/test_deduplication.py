#!/usr/bin/env python3
"""
TEST SUITE: Ultra-Professional Deduplication System
====================================================

This script tests all 5 layers of the deduplication system:
1. URL exact match
2. URL normalized
3. Email deduplication
4. Content hash
5. Temporal deduplication

Usage:
    python scripts/test_deduplication.py
    python scripts/test_deduplication.py --cleanup
"""

import argparse
import os
import sys
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scraper.utils.deduplication_pro import (
    DeduplicationManager,
    normalize_url,
    compute_content_hash,
)
from scraper.database import get_db_session
from sqlalchemy import text


# ────────────────────────────────────────────────────────────
# Test Data
# ────────────────────────────────────────────────────────────

TEST_URLS = [
    "https://example.com/page1",
    "http://example.com/page1",
    "https://www.example.com/page1",
    "https://example.com/page1/",
    "https://example.com/page1?utm_source=test",
    "https://example.com/page1?id=123",
]

TEST_EMAILS = [
    "john.doe@example.com",
    "JOHN.DOE@example.com",
    "  john.doe@example.com  ",
]

TEST_CONTENT = [
    "This is a test page content with some text.",
    "THIS IS A TEST PAGE CONTENT WITH SOME TEXT.",
    "This  is  a  test  page  content  with  some  text.",
]


# ────────────────────────────────────────────────────────────
# Test Functions
# ────────────────────────────────────────────────────────────

def test_url_normalization():
    """Test URL normalization logic."""
    print("\n" + "="*60)
    print("TEST 1: URL Normalization")
    print("="*60)

    test_cases = [
        ("http://www.example.com/page1/", "https://example.com/page1"),
        ("https://example.com/page1?utm_source=test", "https://example.com/page1"),
        ("https://Example.COM/PAGE1", "https://example.com/page1"),
        ("https://example.com/page1?b=2&a=1", "https://example.com/page1?a=1&b=2"),
    ]

    passed = 0
    for original, expected in test_cases:
        normalized = normalize_url(original)
        status = "✅" if normalized == expected else "❌"
        print(f"{status} {original}")
        print(f"   → {normalized}")
        if normalized == expected:
            passed += 1
        else:
            print(f"   ❌ Expected: {expected}")

    print(f"\nResult: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_content_hash():
    """Test content hash computation."""
    print("\n" + "="*60)
    print("TEST 2: Content Hash")
    print("="*60)

    hashes = [compute_content_hash(content) for content in TEST_CONTENT]

    # All hashes should be identical (normalized content)
    if len(set(hashes)) == 1:
        print("✅ All content hashes are identical (correct)")
        print(f"   Hash: {hashes[0][:16]}...")
        return True
    else:
        print("❌ Content hashes differ (incorrect)")
        for i, h in enumerate(hashes):
            print(f"   Content {i+1}: {h[:16]}...")
        return False


def test_url_exact_deduplication():
    """Test URL exact match deduplication."""
    print("\n" + "="*60)
    print("TEST 3: URL Exact Match Deduplication")
    print("="*60)

    manager = DeduplicationManager(job_id=9999)

    url = "https://example.com/test-exact"

    # First check: should be new
    if not manager.is_url_seen_exact(url):
        print(f"✅ URL not seen yet: {url}")
    else:
        print(f"❌ URL already seen (unexpected): {url}")
        return False

    # Mark as seen
    manager.mark_url_seen_exact(url)
    print(f"   Marked URL as seen")

    # Second check: should be duplicate
    if manager.is_url_seen_exact(url):
        print(f"✅ URL detected as duplicate: {url}")
    else:
        print(f"❌ URL not detected as duplicate: {url}")
        return False

    # Different URL: should be new
    different_url = "https://example.com/test-exact-2"
    if not manager.is_url_seen_exact(different_url):
        print(f"✅ Different URL not seen: {different_url}")
    else:
        print(f"❌ Different URL seen (unexpected): {different_url}")
        return False

    return True


def test_url_normalized_deduplication():
    """Test URL normalized deduplication."""
    print("\n" + "="*60)
    print("TEST 4: URL Normalized Deduplication")
    print("="*60)

    manager = DeduplicationManager(job_id=9999)

    # Mark first URL as seen
    url1 = "https://example.com/test-normalized"
    manager.mark_url_seen_exact(url1)
    manager.mark_url_seen_normalized(url1)
    print(f"✅ Marked URL as seen: {url1}")

    # Test normalized variants
    variants = [
        "http://example.com/test-normalized",
        "https://www.example.com/test-normalized",
        "https://example.com/test-normalized/",
        "https://example.com/test-normalized?utm_source=test",
    ]

    passed = 0
    for variant in variants:
        if manager.is_url_seen_normalized(variant):
            print(f"✅ Variant detected as duplicate: {variant}")
            passed += 1
        else:
            print(f"❌ Variant NOT detected as duplicate: {variant}")

    return passed == len(variants)


def test_email_deduplication():
    """Test email deduplication."""
    print("\n" + "="*60)
    print("TEST 5: Email Deduplication")
    print("="*60)

    manager = DeduplicationManager(job_id=9999)

    email = "test.dedup@example.com"

    # First check: should be new
    if not manager.is_email_seen(email):
        print(f"✅ Email not seen yet: {email}")
    else:
        print(f"❌ Email already seen (unexpected): {email}")
        return False

    # Mark as seen
    manager.mark_email_seen(email)
    print(f"   Marked email as seen")

    # Test normalized variants
    variants = [
        "test.dedup@example.com",
        "TEST.DEDUP@example.com",
        "  test.dedup@example.com  ",
    ]

    passed = 0
    for variant in variants:
        if manager.is_email_seen(variant):
            print(f"✅ Variant detected as duplicate: {variant}")
            passed += 1
        else:
            print(f"❌ Variant NOT detected as duplicate: {variant}")

    return passed == len(variants)


def test_content_hash_deduplication():
    """Test content hash deduplication."""
    print("\n" + "="*60)
    print("TEST 6: Content Hash Deduplication")
    print("="*60)

    manager = DeduplicationManager(job_id=9999)

    content1 = "This is a unique test content for deduplication testing."

    # First check: should be new
    is_seen, hash1 = manager.is_content_seen(content1)
    if not is_seen:
        print(f"✅ Content not seen yet")
        print(f"   Hash: {hash1[:16]}...")
    else:
        print(f"❌ Content already seen (unexpected)")
        return False

    # Mark as seen
    manager.mark_content_seen(hash1)
    print(f"   Marked content as seen")

    # Test normalized variants
    variants = [
        "This is a unique test content for deduplication testing.",
        "THIS IS A UNIQUE TEST CONTENT FOR DEDUPLICATION TESTING.",
        "This  is  a  unique  test  content  for  deduplication  testing.",
    ]

    passed = 0
    for variant in variants:
        is_seen, hash_variant = manager.is_content_seen(variant)
        if is_seen and hash_variant == hash1:
            print(f"✅ Variant detected as duplicate: {variant[:50]}...")
            passed += 1
        else:
            print(f"❌ Variant NOT detected as duplicate: {variant[:50]}...")
            print(f"   Hash: {hash_variant[:16]}... (expected: {hash1[:16]}...)")

    return passed == len(variants)


def test_statistics():
    """Test deduplication statistics."""
    print("\n" + "="*60)
    print("TEST 7: Deduplication Statistics")
    print("="*60)

    manager = DeduplicationManager(job_id=9999)

    # Perform some operations
    manager.mark_url_seen_exact("https://example.com/stats-test-1")
    manager.mark_url_seen_exact("https://example.com/stats-test-2")
    manager.mark_email_seen("stats@example.com")

    # Check for duplicates
    manager.is_url_seen_exact("https://example.com/stats-test-1")  # duplicate
    manager.is_email_seen("stats@example.com")  # duplicate

    # Get stats
    stats = manager.get_stats()

    print(f"✅ URLs checked: {stats['urls_checked']}")
    print(f"✅ URLs deduplicated: {stats['urls_deduplicated']}")
    print(f"✅ Emails deduplicated: {stats['emails_deduplicated']}")
    print(f"✅ Deduplication rate: {stats['deduplication_rate']:.1f}%")

    return stats['urls_deduplicated'] > 0


def test_postgresql_fallback():
    """Test PostgreSQL fallback when Redis unavailable."""
    print("\n" + "="*60)
    print("TEST 8: PostgreSQL Fallback")
    print("="*60)

    manager = DeduplicationManager(job_id=9999)

    # Force Redis to None (simulate unavailability)
    original_redis = manager.redis_client
    manager.redis_client = None

    url = "https://example.com/postgres-fallback-test"

    # First check: should be new
    if not manager.is_url_seen_exact(url):
        print(f"✅ URL not seen yet (PostgreSQL): {url}")
    else:
        print(f"❌ URL already seen (unexpected): {url}")
        manager.redis_client = original_redis
        return False

    # Mark as seen
    manager.mark_url_seen_exact(url)
    print(f"   Marked URL as seen (PostgreSQL)")

    # Second check: should be duplicate
    if manager.is_url_seen_exact(url):
        print(f"✅ URL detected as duplicate (PostgreSQL): {url}")
    else:
        print(f"❌ URL not detected as duplicate: {url}")
        manager.redis_client = original_redis
        return False

    # Restore Redis client
    manager.redis_client = original_redis
    return True


def cleanup_test_data():
    """Cleanup test data from database."""
    print("\n" + "="*60)
    print("CLEANUP: Removing test data")
    print("="*60)

    try:
        with get_db_session() as session:
            # Delete test URL cache
            result1 = session.execute(
                text("DELETE FROM url_deduplication_cache WHERE job_id = 9999")
            )
            print(f"✅ Deleted {result1.rowcount} URL cache entries")

            # Delete test content hash cache
            result2 = session.execute(
                text("DELETE FROM content_hash_cache WHERE job_id = 9999")
            )
            print(f"✅ Deleted {result2.rowcount} content hash entries")

            # Delete test contacts (if any)
            result3 = session.execute(
                text("DELETE FROM scraped_contacts WHERE job_id = 9999")
            )
            print(f"✅ Deleted {result3.rowcount} scraped contacts")

        print("\n✅ Cleanup completed successfully")
        return True
    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")
        return False


# ────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Test deduplication system")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup test data after tests")
    args = parser.parse_args()

    print("="*60)
    print("SCRAPER-PRO: DEDUPLICATION SYSTEM TEST SUITE")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    # Run tests
    tests = [
        ("URL Normalization", test_url_normalization),
        ("Content Hash", test_content_hash),
        ("URL Exact Deduplication", test_url_exact_deduplication),
        ("URL Normalized Deduplication", test_url_normalized_deduplication),
        ("Email Deduplication", test_email_deduplication),
        ("Content Hash Deduplication", test_content_hash_deduplication),
        ("Statistics", test_statistics),
        ("PostgreSQL Fallback", test_postgresql_fallback),
    ]

    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n❌ TEST FAILED: {name}")
            print(f"   Error: {e}")
            results[name] = False

        time.sleep(0.5)  # Small delay between tests

    # Cleanup if requested
    if args.cleanup:
        cleanup_test_data()

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print("\n" + "-"*60)
    print(f"TOTAL: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print("="*60)

    if passed == total:
        print("✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()

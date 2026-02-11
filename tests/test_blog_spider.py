"""Tests for BlogContentSpider."""

import json

import pytest
from unittest.mock import MagicMock, patch

from scrapy.http import HtmlResponse, Request
from scraper.items import ArticleItem


def _fake_response(url, body, meta=None):
    """Create a fake Scrapy HtmlResponse for testing."""
    request = Request(url=url, meta=meta or {})
    return HtmlResponse(
        url=url,
        body=body.encode("utf-8"),
        request=request,
        encoding="utf-8",
    )


SAMPLE_ARTICLE_HTML = """
<html lang="en">
<head>
    <title>Living Abroad: A Complete Guide for Expats</title>
    <meta name="description" content="Everything you need to know about moving abroad.">
    <meta property="og:image" content="https://blog.example.com/images/expat-guide.jpg">
    <meta name="author" content="Jane Smith">
    <meta property="article:published_time" content="2025-06-15T10:00:00Z">
</head>
<body>
<article>
    <h1 class="entry-title">Living Abroad: A Complete Guide for Expats</h1>
    <span class="author-name">Jane Smith</span>
    <time datetime="2025-06-15T10:00:00Z">June 15, 2025</time>
    <div class="entry-content">
        <p>Moving to a new country is one of the most exciting and challenging
        experiences you can have. Whether you are relocating for work, retirement,
        or simply seeking a new adventure, the process requires careful planning.</p>
        <p>First, you need to research your destination thoroughly. Understand the
        cost of living, healthcare system, and cultural norms. Many expats find that
        joining local communities and online forums can be incredibly helpful.</p>
        <p>Second, make sure you handle all legal requirements. This includes visas,
        work permits, and insurance coverage. Consult with professionals who
        specialize in international relocation to avoid common pitfalls.</p>
        <p>Third, prepare your finances. Open a local bank account, understand
        the tax implications, and set up a budget that accounts for the differences
        in cost of living between your home country and your destination.</p>
        <a href="https://external-resource.com/visa-guide">Visa Guide</a>
        <a href="https://another-site.org/expat-tips">Expat Tips</a>
        <a href="/blog/healthcare-abroad">Healthcare Abroad</a>
        <a href="/blog/finding-housing">Finding Housing</a>
    </div>
</article>
</body>
</html>
"""

SAMPLE_LISTING_HTML = """
<html>
<head><title>Blog - Expat Guide</title></head>
<body>
<div class="blog-listing">
    <a href="/blog/2025/06/living-abroad-complete-guide">Living Abroad Guide</a>
    <a href="/blog/2024/03/best-countries-for-expats">Best Countries</a>
    <a href="/blog/2024/01/how-to-learn-a-new-language-quickly-and-easily">Learn a Language</a>
    <a href="/tag/expat">Expat Tag</a>
    <a href="/category/travel">Travel Category</a>
    <a href="/login">Login</a>
    <a href="https://other-domain.com/article">External Link</a>
</div>
<div class="pagination">
    <a class="next" href="/blog/page/2" rel="next">Next</a>
</div>
</body>
</html>
"""

SHORT_PAGE_HTML = """
<html>
<head><title>Navigation</title></head>
<body>
<article>
    <h1>Menu</h1>
    <div class="entry-content">
        <p>Home About Contact</p>
    </div>
</article>
</body>
</html>
"""


class TestBlogContentSpider:
    """Tests for BlogContentSpider."""

    def _make_spider(self, **kwargs):
        from scraper.spiders.blog_content_spider import BlogContentSpider

        defaults = {
            "job_id": 10,
            "start_url": "https://blog.example.com/blog/",
            "max_articles": 50,
            "scrape_depth": 2,
        }
        defaults.update(kwargs)
        return BlogContentSpider(**defaults)

    def test_init_single_url(self):
        """Spider should accept a single start_url."""
        spider = self._make_spider(start_url="https://blog.example.com/blog/")
        assert spider.start_urls_list == ["https://blog.example.com/blog/"]
        assert "blog.example.com" in spider.allowed_domains_set

    def test_init_multiple_urls(self):
        """Spider should accept a list of URLs."""
        spider = self._make_spider(
            start_url=None,
            urls=["https://site1.com/blog", "https://site2.com/news"],
        )
        assert len(spider.start_urls_list) == 2
        assert "site1.com" in spider.allowed_domains_set
        assert "site2.com" in spider.allowed_domains_set

    def test_init_urls_json_string(self):
        """Spider should parse JSON string for urls parameter."""
        spider = self._make_spider(
            start_url=None,
            urls='["https://a.com/blog", "https://b.com/blog"]',
        )
        assert len(spider.start_urls_list) == 2

    def test_start_requests(self):
        """start_requests should yield one request per start URL."""
        spider = self._make_spider()
        requests = list(spider.start_requests())
        assert len(requests) == 1
        assert requests[0].url == "https://blog.example.com/blog/"

    def test_parse_listing_discovers_articles(self):
        """parse_listing should discover article URLs and skip blocklisted ones."""
        spider = self._make_spider()
        response = _fake_response(
            "https://blog.example.com/blog/",
            SAMPLE_LISTING_HTML,
            meta={"depth": 0},
        )

        requests = list(spider.parse_listing(response))
        urls = [r.url for r in requests]

        # Should discover article URLs (date patterns, long slugs)
        assert any("/2025/06/living-abroad" in u for u in urls)
        assert any("/2024/03/best-countries" in u for u in urls)
        assert any("how-to-learn-a-new-language" in u for u in urls)

        # Should NOT follow tag/category/login/external
        assert not any("/tag/" in u for u in urls)
        assert not any("/category/" in u for u in urls)
        assert not any("/login" in u for u in urls)
        assert not any("other-domain.com" in u for u in urls)

    def test_parse_listing_follows_pagination(self):
        """parse_listing should follow pagination links."""
        spider = self._make_spider()
        response = _fake_response(
            "https://blog.example.com/blog/",
            SAMPLE_LISTING_HTML,
            meta={"depth": 0},
        )

        requests = list(spider.parse_listing(response))
        urls = [r.url for r in requests]

        # Should follow next page (rel="next")
        assert any("/blog/page/2" in u for u in urls)

    @patch("scraper.spiders.blog_content_spider.mark_url_seen")
    @patch("scraper.spiders.blog_content_spider.save_checkpoint")
    @patch("scraper.spiders.blog_content_spider.update_progress")
    def test_parse_article_extracts_content(self, mock_progress, mock_save, mock_mark):
        """parse_article should extract article content and yield ArticleItem."""
        spider = self._make_spider()
        response = _fake_response(
            "https://blog.example.com/blog/2025/06/living-abroad",
            SAMPLE_ARTICLE_HTML,
            meta={"depth": 1},
        )

        items = list(spider.parse_article(response))
        assert len(items) == 1

        item = items[0]
        assert isinstance(item, ArticleItem)
        assert item["title"] == "Living Abroad: A Complete Guide for Expats"
        assert item["domain"] == "blog.example.com"
        assert item["source_url"] == "https://blog.example.com/blog/2025/06/living-abroad"
        assert item["job_id"] == 10
        assert item["word_count"] >= 50

    @patch("scraper.spiders.blog_content_spider.mark_url_seen")
    @patch("scraper.spiders.blog_content_spider.save_checkpoint")
    @patch("scraper.spiders.blog_content_spider.update_progress")
    def test_parse_article_extracts_metadata(self, mock_progress, mock_save, mock_mark):
        """parse_article should extract author, date, meta description, featured image."""
        spider = self._make_spider()
        response = _fake_response(
            "https://blog.example.com/blog/article",
            SAMPLE_ARTICLE_HTML,
            meta={"depth": 1},
        )

        items = list(spider.parse_article(response))
        assert len(items) == 1
        item = items[0]

        assert item.get("meta_description") == "Everything you need to know about moving abroad."
        assert item.get("featured_image_url") == "https://blog.example.com/images/expat-guide.jpg"
        assert item.get("language") == "en"

    @patch("scraper.spiders.blog_content_spider.mark_url_seen")
    @patch("scraper.spiders.blog_content_spider.save_checkpoint")
    @patch("scraper.spiders.blog_content_spider.update_progress")
    def test_parse_article_extracts_links(self, mock_progress, mock_save, mock_mark):
        """parse_article should separate external and internal links."""
        spider = self._make_spider()
        response = _fake_response(
            "https://blog.example.com/blog/article",
            SAMPLE_ARTICLE_HTML,
            meta={"depth": 1},
        )

        items = list(spider.parse_article(response))
        assert len(items) == 1
        item = items[0]

        ext_links = item.get("external_links", [])
        int_links = item.get("internal_links", [])

        # External links
        ext_urls = [l["url"] for l in ext_links]
        assert any("external-resource.com" in u for u in ext_urls)
        assert any("another-site.org" in u for u in ext_urls)

        # Internal links
        int_urls = [l["url"] for l in int_links]
        assert any("healthcare-abroad" in u for u in int_urls)
        assert any("finding-housing" in u for u in int_urls)

    @patch("scraper.spiders.blog_content_spider.mark_url_seen")
    def test_parse_article_skips_short_content(self, mock_mark):
        """Articles with fewer than MIN_WORD_COUNT words should be skipped."""
        spider = self._make_spider()
        response = _fake_response(
            "https://blog.example.com/blog/short",
            SHORT_PAGE_HTML,
            meta={"depth": 1},
        )

        items = list(spider.parse_article(response))
        assert len(items) == 0

    @patch("scraper.spiders.blog_content_spider.mark_url_seen")
    @patch("scraper.spiders.blog_content_spider.save_checkpoint")
    @patch("scraper.spiders.blog_content_spider.update_progress")
    def test_max_articles_limit(self, mock_progress, mock_save, mock_mark):
        """Spider should stop yielding after max_articles is reached."""
        spider = self._make_spider(max_articles=1)
        response = _fake_response(
            "https://blog.example.com/blog/article",
            SAMPLE_ARTICLE_HTML,
            meta={"depth": 1},
        )

        # First article should succeed
        items1 = list(spider.parse_article(response))
        assert len(items1) == 1

        # Second call should yield nothing (max reached)
        items2 = list(spider.parse_article(response))
        assert len(items2) == 0

    @patch("scraper.spiders.blog_content_spider.mark_url_seen")
    @patch("scraper.spiders.blog_content_spider.save_checkpoint")
    @patch("scraper.spiders.blog_content_spider.update_progress")
    def test_checkpoint_saved_after_article(self, mock_progress, mock_save, mock_mark):
        """Checkpoint should be saved after each article is extracted."""
        spider = self._make_spider()
        response = _fake_response(
            "https://blog.example.com/blog/article",
            SAMPLE_ARTICLE_HTML,
            meta={"depth": 1},
        )

        list(spider.parse_article(response))

        mock_save.assert_called_once()
        call_args = mock_save.call_args
        assert call_args[0][0] == 10  # job_id
        checkpoint_data = call_args[0][1]
        assert checkpoint_data["articles_found"] == 1

    @patch("scraper.spiders.blog_content_spider.load_checkpoint")
    def test_resume_restores_state(self, mock_load):
        """With resume=true, spider should restore checkpoint state."""
        mock_load.return_value = {
            "articles_found": 5,
            "pages_crawled": 10,
            "seen_urls": ["https://blog.example.com/blog/old-article"],
        }

        spider = self._make_spider(resume="true")
        requests = list(spider.start_requests())

        assert spider.articles_found == 5
        assert spider.pages_crawled == 10
        assert "https://blog.example.com/blog/old-article" in spider._seen_urls

    def test_is_article_url_patterns(self):
        """_is_article_url should detect common blog article URL patterns."""
        spider = self._make_spider()

        # Should be detected as articles
        assert spider._is_article_url("/blog/my-first-post")
        assert spider._is_article_url("/2024/03/expat-life-in-france")
        assert spider._is_article_url("/articles/something")
        assert spider._is_article_url("/post/how-to-move-abroad-successfully-in-2024")

        # Should NOT be detected as articles
        assert not spider._is_article_url("/tag/travel")
        assert not spider._is_article_url("/category/lifestyle")
        assert not spider._is_article_url("/login")
        assert not spider._is_article_url("/admin/dashboard")
        assert not spider._is_article_url("/page/3")

    def test_is_article_url_long_slug(self):
        """Long slugs with 3+ hyphens should be detected as articles."""
        spider = self._make_spider()
        assert spider._is_article_url("/this-is-a-really-long-article-slug")
        assert not spider._is_article_url("/short")

    def test_domain_confinement(self):
        """parse_listing should not follow links to other domains."""
        spider = self._make_spider()

        html = """
        <html><body>
            <a href="https://blog.example.com/blog/2024/03/good-article">Good</a>
            <a href="https://evil.com/blog/2024/03/bad-article">Bad</a>
        </body></html>
        """
        response = _fake_response(
            "https://blog.example.com/blog/",
            html,
            meta={"depth": 0},
        )

        requests = list(spider.parse_listing(response))
        urls = [r.url for r in requests]

        assert any("blog.example.com" in u for u in urls)
        assert not any("evil.com" in u for u in urls)

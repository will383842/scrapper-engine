"""
Blog Content Spider - Scrapes blog articles for AI content generation.
Extracts title, full text, author, date, links via trafilatura with CSS fallback.
Supports checkpoint/resume for interrupted jobs.
"""

import json
import logging
import re
from urllib.parse import urljoin, urlparse

import scrapy

from scraper.items import ArticleItem
from scraper.utils.checkpoint import (
    load_checkpoint,
    mark_url_seen,
    save_checkpoint,
    update_progress,
)
from scraper.utils.metadata_extractor import MetadataExtractor

logger = logging.getLogger(__name__)

try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False
    logger.warning("trafilatura not installed, falling back to CSS extraction")

# Minimum word count to consider a page as an article (not navigation/listing)
MIN_WORD_COUNT = 50

# URL patterns that suggest a page is a blog article
ARTICLE_URL_PATTERNS = re.compile(
    r"(/blog/[^/]+|/article[s]?/|/post[s]?/|/news/[^/]+|"
    r"/\d{4}/\d{2}/|/\d{4}-\d{2}-|"
    r"/[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+)",  # slugs with 3+ hyphens
    re.IGNORECASE,
)

# URL patterns to skip (not articles)
BLOCKLIST_URL_PATTERNS = re.compile(
    r"(/tag[s]?/|/categor[yies]+/|/author[s]?/|/page/\d+|"
    r"/login|/register|/admin|/wp-admin|/cart|/checkout|"
    r"/search|/feed|/rss|/sitemap|/privacy|/terms|/cookie|"
    r"\.(pdf|zip|exe|dmg|mp4|mp3|avi|mov)$)",
    re.IGNORECASE,
)

# Pagination patterns for discovering article listing pages
PAGINATION_PATTERNS = [
    "a.next::attr(href)",
    "a.page-next::attr(href)",
    "a[rel='next']::attr(href)",
    "li.next a::attr(href)",
    ".pagination a::attr(href)",
    ".nav-links a.next::attr(href)",
    "a.older-posts::attr(href)",
    "a.load-more::attr(href)",
]


class BlogContentSpider(scrapy.Spider):
    name = "blog_content"

    def __init__(
        self,
        job_id=None,
        start_url=None,
        urls=None,
        max_articles=100,
        scrape_depth=2,
        resume="false",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.job_id = job_id
        self.max_articles = int(max_articles)
        self.scrape_depth = int(scrape_depth)
        self.resume = resume == "true"
        self.articles_found = 0
        self.pages_crawled = 0
        self._seen_urls = set()

        # Initialize metadata extractor
        self.metadata_extractor = MetadataExtractor()

        # Accept single URL or list
        if start_url:
            self.start_urls_list = [start_url]
        elif urls:
            if isinstance(urls, str):
                try:
                    self.start_urls_list = json.loads(urls)
                except (json.JSONDecodeError, TypeError):
                    self.start_urls_list = [urls] if urls.startswith("http") else []
            else:
                self.start_urls_list = urls
        else:
            self.start_urls_list = []

        # Determine allowed domains from start URLs
        self.allowed_domains_set = set()
        for url in self.start_urls_list:
            parsed = urlparse(url)
            if parsed.netloc:
                self.allowed_domains_set.add(parsed.netloc.lower())

    def start_requests(self):
        # Resume support
        if self.resume and self.job_id:
            checkpoint = load_checkpoint(int(self.job_id))
            if checkpoint:
                self.articles_found = checkpoint.get("articles_found", 0)
                self.pages_crawled = checkpoint.get("pages_crawled", 0)
                self._seen_urls = set(checkpoint.get("seen_urls", []))
                self.logger.info(
                    f"Resuming: {self.articles_found} articles found, "
                    f"{self.pages_crawled} pages crawled, "
                    f"{len(self._seen_urls)} URLs seen"
                )

        for url in self.start_urls_list:
            if url in self._seen_urls:
                continue
            yield scrapy.Request(
                url,
                callback=self.parse_listing,
                meta={"depth": 0},
                errback=self.handle_error,
            )

    def parse_listing(self, response):
        """Parse a blog listing/archive page to discover article links."""
        if self.articles_found >= self.max_articles:
            return

        current_depth = response.meta.get("depth", 0)
        domain = urlparse(response.url).netloc.lower()

        self._seen_urls.add(response.url)
        self.pages_crawled += 1

        # Extract all links on the page
        for href in response.css("a::attr(href)").getall():
            full_url = urljoin(response.url, href)
            parsed = urlparse(full_url)
            link_domain = parsed.netloc.lower()

            # Stay on the same domain
            if link_domain not in self.allowed_domains_set:
                continue

            # Normalize URL (remove fragment)
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                clean_url += f"?{parsed.query}"

            if clean_url in self._seen_urls:
                continue

            # Skip blocklisted URLs
            if BLOCKLIST_URL_PATTERNS.search(parsed.path):
                continue

            # If it looks like an article URL, scrape it
            if self._is_article_url(parsed.path):
                if self.articles_found >= self.max_articles:
                    return
                self._seen_urls.add(clean_url)
                yield scrapy.Request(
                    clean_url,
                    callback=self.parse_article,
                    meta={"depth": current_depth + 1},
                    errback=self.handle_error,
                )

        # Follow pagination links to discover more articles
        if current_depth < self.scrape_depth:
            for selector in PAGINATION_PATTERNS:
                for next_url in response.css(selector).getall():
                    full_next = urljoin(response.url, next_url)
                    if full_next not in self._seen_urls:
                        parsed_next = urlparse(full_next)
                        if parsed_next.netloc.lower() in self.allowed_domains_set:
                            self._seen_urls.add(full_next)
                            yield scrapy.Request(
                                full_next,
                                callback=self.parse_listing,
                                meta={"depth": current_depth + 1},
                                errback=self.handle_error,
                            )

            # Also follow links that look like listing/archive pages
            for href in response.css("a::attr(href)").getall():
                full_url = urljoin(response.url, href)
                parsed = urlparse(full_url)
                path_lower = parsed.path.lower()
                if (
                    full_url not in self._seen_urls
                    and parsed.netloc.lower() in self.allowed_domains_set
                    and any(
                        p in path_lower
                        for p in ["/blog", "/articles", "/posts", "/news", "/archives"]
                    )
                    and not BLOCKLIST_URL_PATTERNS.search(parsed.path)
                ):
                    self._seen_urls.add(full_url)
                    yield scrapy.Request(
                        full_url,
                        callback=self.parse_listing,
                        meta={"depth": current_depth + 1},
                        priority=1,
                        errback=self.handle_error,
                    )

    def parse_article(self, response):
        """Extract article content from a single article page."""
        if self.articles_found >= self.max_articles:
            return

        domain = urlparse(response.url).netloc.lower()
        mark_url_seen(response.url, spider_name=self.name)

        # Extract article content
        article_data = self._extract_article(response)

        if not article_data:
            return

        # Check minimum word count
        word_count = article_data.get("word_count", 0)
        if word_count < MIN_WORD_COUNT:
            self.logger.debug(
                f"Skipping {response.url}: only {word_count} words (min {MIN_WORD_COUNT})"
            )
            return

        # Extract links
        external_links, internal_links = self._extract_links(response, domain)

        # Extract universal metadata
        metadata = self.metadata_extractor.extract_all(response.url, response)

        self.articles_found += 1

        item = ArticleItem(
            title=article_data.get("title"),
            content_text=article_data.get("content_text"),
            content_html=article_data.get("content_html"),
            excerpt=article_data.get("excerpt"),
            author=article_data.get("author"),
            date_published=article_data.get("date_published"),
            categories=article_data.get("categories", []),
            tags=article_data.get("tags", []),
            external_links=external_links,
            internal_links=internal_links,
            featured_image_url=article_data.get("featured_image_url"),
            meta_description=article_data.get("meta_description"),
            word_count=word_count,
            language=article_data.get("language"),
            source_url=response.url,
            domain=domain,
            job_id=self.job_id,
            # Universal metadata
            country=metadata.get("country"),
            region=metadata.get("region"),
            city=metadata.get("city"),
            extracted_category=metadata.get("category"),
            extracted_subcategory=metadata.get("subcategory"),
            year=metadata.get("year"),
            month=metadata.get("month"),
        )

        # Checkpoint after each article
        if self.job_id:
            # Limit seen_urls in checkpoint to last 500 to avoid bloat
            seen_list = list(self._seen_urls)[-500:]
            save_checkpoint(int(self.job_id), {
                "articles_found": self.articles_found,
                "pages_crawled": self.pages_crawled,
                "seen_urls": seen_list,
            })
            progress = min(self.articles_found / self.max_articles * 100, 100.0)
            update_progress(
                int(self.job_id),
                progress,
                pages=self.pages_crawled,
                contacts=self.articles_found,
            )

        yield item

    def _extract_article(self, response):
        """Extract article data using trafilatura with CSS fallback."""
        result = {}

        if HAS_TRAFILATURA:
            extracted = trafilatura.bare_extraction(
                response.text,
                url=response.url,
                include_links=False,
                include_comments=False,
                include_tables=False,
                favor_recall=True,
            )
            if extracted:
                result["title"] = extracted.get("title")
                result["content_text"] = extracted.get("text", "")
                result["author"] = extracted.get("author")
                result["date_published"] = extracted.get("date")
                result["language"] = extracted.get("language")
                result["excerpt"] = extracted.get("description")
                result["categories"] = extracted.get("categories", []) or []
                result["tags"] = extracted.get("tags", []) or []

        # CSS fallback or supplement missing fields
        if not result.get("title"):
            result["title"] = (
                response.css("h1.entry-title::text").get()
                or response.css("h1.post-title::text").get()
                or response.css("article h1::text").get()
                or response.css("h1::text").get()
                or response.css("title::text").get("")
            )
            if result["title"]:
                result["title"] = result["title"].strip()

        if not result.get("content_text"):
            # Fallback: extract from article/main content areas
            paragraphs = (
                response.css("article p::text").getall()
                or response.css(".post-content p::text").getall()
                or response.css(".entry-content p::text").getall()
                or response.css("main p::text").getall()
            )
            result["content_text"] = "\n\n".join(p.strip() for p in paragraphs if p.strip())

        if not result.get("author"):
            result["author"] = (
                response.css("[rel='author']::text").get()
                or response.css(".author-name::text").get()
                or response.css("meta[name='author']::attr(content)").get()
            )

        if not result.get("date_published"):
            result["date_published"] = (
                response.css("time::attr(datetime)").get()
                or response.css("meta[property='article:published_time']::attr(content)").get()
                or response.css(".post-date::text").get()
            )

        # Extract content HTML from article body
        result["content_html"] = (
            response.css("article .entry-content").get()
            or response.css("article .post-content").get()
            or response.css("article").get("")
        )

        # Meta description
        result["meta_description"] = (
            response.css("meta[name='description']::attr(content)").get()
            or response.css("meta[property='og:description']::attr(content)").get()
        )

        # Featured image
        result["featured_image_url"] = (
            response.css("meta[property='og:image']::attr(content)").get()
            or response.css("article img::attr(src)").get()
        )

        # Excerpt (first 200 chars of content if not set)
        if not result.get("excerpt") and result.get("content_text"):
            text = result["content_text"]
            result["excerpt"] = text[:200].rsplit(" ", 1)[0] + "..." if len(text) > 200 else text

        # Word count
        content = result.get("content_text", "")
        result["word_count"] = len(content.split()) if content else 0

        # Language fallback
        if not result.get("language"):
            lang_attr = response.css("html::attr(lang)").get()
            if lang_attr:
                result["language"] = lang_attr[:10]

        return result if result.get("content_text") else None

    def _extract_links(self, response, current_domain):
        """Extract external and internal links from article body."""
        external = []
        internal = []

        # Try to get links from article body only
        article_el = (
            response.css("article")
            or response.css(".post-content")
            or response.css(".entry-content")
            or response.css("main")
        )

        if article_el:
            links = article_el.css("a::attr(href)").getall()
        else:
            links = response.css("a::attr(href)").getall()

        for href in links:
            full_url = urljoin(response.url, href)
            parsed = urlparse(full_url)

            # Skip anchors, javascript, mailto
            if not parsed.scheme or parsed.scheme not in ("http", "https"):
                continue

            link_domain = parsed.netloc.lower()
            link_data = {"url": full_url, "domain": link_domain}

            if link_domain == current_domain:
                internal.append(link_data)
            else:
                external.append(link_data)

        return external[:50], internal[:50]  # Cap at 50 each

    def _is_article_url(self, path):
        """Heuristic: does this URL path look like a blog article?"""
        if BLOCKLIST_URL_PATTERNS.search(path):
            return False
        if ARTICLE_URL_PATTERNS.search(path):
            return True
        # Slug heuristic: path has 3+ segments or long slug
        parts = [p for p in path.strip("/").split("/") if p]
        if parts:
            last_part = parts[-1]
            # Long slugs with hyphens are likely articles
            if last_part.count("-") >= 3 and len(last_part) > 20:
                return True
        return False

    def handle_error(self, failure):
        self.logger.warning(f"Request failed: {failure.request.url} - {failure.value}")

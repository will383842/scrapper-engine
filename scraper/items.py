"""Scrapy item definitions for scraper-pro."""

import scrapy


class ContactItem(scrapy.Item):
    """Standard contact item yielded by all spiders."""

    email = scrapy.Field()
    name = scrapy.Field()
    phone = scrapy.Field()
    website = scrapy.Field()
    address = scrapy.Field()
    social_media = scrapy.Field()
    source_type = scrapy.Field()
    source_url = scrapy.Field()
    domain = scrapy.Field()
    country = scrapy.Field()
    keywords = scrapy.Field()
    job_id = scrapy.Field()


class ArticleItem(scrapy.Item):
    """Blog article item yielded by the blog_content spider."""

    title = scrapy.Field()
    content_text = scrapy.Field()
    content_html = scrapy.Field()
    excerpt = scrapy.Field()
    author = scrapy.Field()
    date_published = scrapy.Field()
    categories = scrapy.Field()
    tags = scrapy.Field()
    external_links = scrapy.Field()
    internal_links = scrapy.Field()
    featured_image_url = scrapy.Field()
    meta_description = scrapy.Field()
    word_count = scrapy.Field()
    language = scrapy.Field()
    source_url = scrapy.Field()
    domain = scrapy.Field()
    job_id = scrapy.Field()

    # Universal metadata fields (extracted automatically)
    # Métadonnées géographiques
    country = scrapy.Field()  # "france", "spain", "usa"
    region = scrapy.Field()  # "europe", "asia", "africa"
    city = scrapy.Field()  # "paris", "bangkok"

    # Métadonnées de classification
    extracted_category = scrapy.Field()  # Catégorie extraite automatiquement
    extracted_subcategory = scrapy.Field()  # Sous-catégorie

    # Métadonnées temporelles additionnelles
    year = scrapy.Field()  # 2024
    month = scrapy.Field()  # 1-12

    # Legacy expat.com specific field (deprecated - use extracted_category)
    category_expat = scrapy.Field()

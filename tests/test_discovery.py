"""Tests for discovery module."""

import pytest

from wit.config import WitConfig, SiteConfig
from wit.discovery import (
    discover_pages,
    discover_pages_for_site,
    discover_from_urls,
    discover_from_sitemap,
    discover_from_crawl,
    _should_include_url,
)


class TestShouldIncludeUrl:
    """Tests for _should_include_url function."""
    
    def test_no_patterns(self):
        """Test with no include/exclude patterns."""
        assert _should_include_url("/about", [], []) is True
    
    def test_exclude_pattern(self):
        """Test URL excluded by pattern."""
        assert _should_include_url("/admin/users", [], ["/admin/*"]) is False
    
    def test_include_pattern(self):
        """Test URL included by pattern."""
        assert _should_include_url("/docs/intro", ["/docs/*"], []) is True
    
    def test_not_in_include(self):
        """Test URL not in include patterns."""
        assert _should_include_url("/blog/post", ["/docs/*"], []) is False
    
    def test_exclude_takes_precedence(self):
        """Test exclude takes precedence over include."""
        assert _should_include_url("/docs/v1/old", ["/docs/*"], ["/docs/v1/*"]) is False


class TestDiscoverFromUrls:
    """Tests for discover_from_urls function."""
    
    def test_simple_urls(self):
        """Test discovering simple URLs without patterns."""
        urls = discover_from_urls(
            "https://example.com",
            ["/", "/about", "/contact"],
            {"timeout": 30, "user_agent": "test"},
            None
        )
        
        assert "https://example.com/" in urls
        assert "https://example.com/about" in urls
        assert "https://example.com/contact" in urls
    
    def test_url_pattern_expansion(self):
        """Test URL pattern expansion with mock fetch."""
        def mock_fetch(url):
            return """
            <html>
                <body>
                    <a href="/docs/intro">Intro</a>
                    <a href="/docs/guide">Guide</a>
                    <a href="/blog/post">Blog</a>
                </body>
            </html>
            """
        
        urls = discover_from_urls(
            "https://example.com",
            ["/docs/*"],
            {"timeout": 30, "user_agent": "test"},
            mock_fetch
        )
        
        assert "https://example.com/docs/intro" in urls
        assert "https://example.com/docs/guide" in urls
        # Blog should not be included
        assert "https://example.com/blog/post" not in urls


class TestDiscoverFromSitemap:
    """Tests for discover_from_sitemap function."""
    
    def test_simple_sitemap(self):
        """Test parsing a simple sitemap."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/</loc></url>
            <url><loc>https://example.com/about</loc></url>
            <url><loc>https://example.com/contact</loc></url>
        </urlset>
        """
        
        def mock_fetch(url):
            return sitemap_xml
        
        urls = discover_from_sitemap(
            "https://example.com",
            "/sitemap.xml",
            {"timeout": 30, "user_agent": "test"},
            mock_fetch
        )
        
        assert "https://example.com/" in urls
        assert "https://example.com/about" in urls
        assert "https://example.com/contact" in urls
    
    def test_sitemap_without_namespace(self):
        """Test parsing sitemap without XML namespace."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset>
            <url><loc>https://example.com/page1</loc></url>
            <url><loc>https://example.com/page2</loc></url>
        </urlset>
        """
        
        def mock_fetch(url):
            return sitemap_xml
        
        urls = discover_from_sitemap(
            "https://example.com",
            "/sitemap.xml",
            {"timeout": 30, "user_agent": "test"},
            mock_fetch
        )
        
        assert "https://example.com/page1" in urls
        assert "https://example.com/page2" in urls
    
    def test_sitemap_index(self):
        """Test parsing a sitemap index."""
        sitemap_index = """<?xml version="1.0" encoding="UTF-8"?>
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap><loc>https://example.com/sitemap-pages.xml</loc></sitemap>
        </sitemapindex>
        """
        
        sub_sitemap = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page</loc></url>
        </urlset>
        """
        
        def mock_fetch(url):
            if "sitemap-pages" in url:
                return sub_sitemap
            return sitemap_index
        
        urls = discover_from_sitemap(
            "https://example.com",
            "/sitemap.xml",
            {"timeout": 30, "user_agent": "test"},
            mock_fetch
        )
        
        assert "https://example.com/page" in urls
    
    def test_sitemap_filters_external_urls(self):
        """Test that external URLs are filtered out."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page</loc></url>
            <url><loc>https://other-site.com/page</loc></url>
        </urlset>
        """
        
        def mock_fetch(url):
            return sitemap_xml
        
        urls = discover_from_sitemap(
            "https://example.com",
            "/sitemap.xml",
            {"timeout": 30, "user_agent": "test"},
            mock_fetch
        )
        
        assert "https://example.com/page" in urls
        assert "https://other-site.com/page" not in urls


class TestDiscoverFromCrawl:
    """Tests for discover_from_crawl function."""
    
    def test_simple_crawl(self):
        """Test simple crawling."""
        pages = {
            "https://example.com/": """
                <html><body>
                    <a href="/about">About</a>
                    <a href="/contact">Contact</a>
                </body></html>
            """,
            "https://example.com/about": "<html><body>About page</body></html>",
            "https://example.com/contact": "<html><body>Contact page</body></html>",
        }
        
        def mock_fetch(url):
            return pages.get(url, "<html><body></body></html>")
        
        urls = discover_from_crawl(
            base_url="https://example.com",
            start="/",
            max_depth=1,
            max_pages=10,
            include=[],
            exclude=[],
            scraping_config={"timeout": 30, "user_agent": "test", "delay": 0},
            fetch_func=mock_fetch
        )
        
        assert "https://example.com/" in urls
        assert "https://example.com/about" in urls
        assert "https://example.com/contact" in urls
    
    def test_crawl_respects_max_depth(self):
        """Test that crawl respects max_depth."""
        pages = {
            "https://example.com/": '<a href="/level1">L1</a>',
            "https://example.com/level1": '<a href="/level1/level2">L2</a>',
            "https://example.com/level1/level2": '<a href="/level1/level2/level3">L3</a>',
        }
        
        def mock_fetch(url):
            return f"<html><body>{pages.get(url, '')}</body></html>"
        
        urls = discover_from_crawl(
            base_url="https://example.com",
            start="/",
            max_depth=1,
            max_pages=10,
            include=[],
            exclude=[],
            scraping_config={"timeout": 30, "user_agent": "test", "delay": 0},
            fetch_func=mock_fetch
        )
        
        assert "https://example.com/" in urls
        assert "https://example.com/level1" in urls
        # level2 should not be included (depth 2)
        assert "https://example.com/level1/level2" not in urls
    
    def test_crawl_respects_max_pages(self):
        """Test that crawl respects max_pages."""
        pages = {
            "https://example.com/": """
                <a href="/page1">P1</a>
                <a href="/page2">P2</a>
                <a href="/page3">P3</a>
                <a href="/page4">P4</a>
                <a href="/page5">P5</a>
            """,
        }
        
        def mock_fetch(url):
            return f"<html><body>{pages.get(url, '')}</body></html>"
        
        urls = discover_from_crawl(
            base_url="https://example.com",
            start="/",
            max_depth=2,
            max_pages=3,
            include=[],
            exclude=[],
            scraping_config={"timeout": 30, "user_agent": "test", "delay": 0},
            fetch_func=mock_fetch
        )
        
        assert len(urls) == 3
    
    def test_crawl_with_include_pattern(self):
        """Test crawl with include patterns."""
        pages = {
            "https://example.com/": '<a href="/docs/intro">Docs</a><a href="/blog/post">Blog</a>',
            "https://example.com/docs/intro": "<p>Docs</p>",
            "https://example.com/blog/post": "<p>Blog</p>",
        }
        
        def mock_fetch(url):
            return f"<html><body>{pages.get(url, '')}</body></html>"
        
        urls = discover_from_crawl(
            base_url="https://example.com",
            start="/",
            max_depth=2,
            max_pages=10,
            include=["/", "/docs/*"],
            exclude=[],
            scraping_config={"timeout": 30, "user_agent": "test", "delay": 0},
            fetch_func=mock_fetch
        )
        
        assert "https://example.com/" in urls
        assert "https://example.com/docs/intro" in urls
        assert "https://example.com/blog/post" not in urls
    
    def test_crawl_with_exclude_pattern(self):
        """Test crawl with exclude patterns."""
        pages = {
            "https://example.com/": '<a href="/page">Page</a><a href="/admin/users">Admin</a>',
        }
        
        def mock_fetch(url):
            return f"<html><body>{pages.get(url, '')}</body></html>"
        
        urls = discover_from_crawl(
            base_url="https://example.com",
            start="/",
            max_depth=2,
            max_pages=10,
            include=[],
            exclude=["/admin/*"],
            scraping_config={"timeout": 30, "user_agent": "test", "delay": 0},
            fetch_func=mock_fetch
        )
        
        assert "https://example.com/" in urls
        assert "https://example.com/page" in urls
        assert "https://example.com/admin/users" not in urls
    
    def test_crawl_ignores_external_links(self):
        """Test that crawl ignores external links."""
        pages = {
            "https://example.com/": '<a href="/internal">Int</a><a href="https://other.com/page">Ext</a>',
        }
        
        def mock_fetch(url):
            return f"<html><body>{pages.get(url, '')}</body></html>"
        
        urls = discover_from_crawl(
            base_url="https://example.com",
            start="/",
            max_depth=2,
            max_pages=10,
            include=[],
            exclude=[],
            scraping_config={"timeout": 30, "user_agent": "test", "delay": 0},
            fetch_func=mock_fetch
        )
        
        assert "https://example.com/" in urls
        assert "https://example.com/internal" in urls
        assert "https://other.com/page" not in urls


class TestDiscoverPagesForSite:
    """Tests for discover_pages_for_site function."""
    
    def test_discover_with_urls(self):
        """Test discovery using URL list."""
        site = SiteConfig(
            name="example",
            base_url="https://example.com",
            pages={"urls": ["/", "/about"]}
        )
        
        urls = discover_pages_for_site(site)
        
        assert "https://example.com/" in urls
        assert "https://example.com/about" in urls
    
    def test_discover_default_to_base_url(self):
        """Test that empty config defaults to base URL."""
        site = SiteConfig(
            name="example",
            base_url="https://example.com",
            pages={}
        )
        
        urls = discover_pages_for_site(site)
        
        assert "https://example.com" in urls
    
    def test_discover_with_sitemap(self):
        """Test discovery using sitemap."""
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page1</loc></url>
            <url><loc>https://example.com/page2</loc></url>
        </urlset>
        """
        
        def mock_fetch(url):
            return sitemap_xml
        
        site = SiteConfig(
            name="example",
            base_url="https://example.com",
            pages={"sitemap": "/sitemap.xml"}
        )
        
        urls = discover_pages_for_site(site, fetch_func=mock_fetch)
        
        assert "https://example.com/page1" in urls
        assert "https://example.com/page2" in urls


class TestDiscoverPages:
    """Tests for discover_pages function (legacy/backwards compatibility)."""
    
    def test_discover_with_urls(self):
        """Test discovery using URL list."""
        config = WitConfig(
            base_url="https://example.com",
            pages={"urls": ["/", "/about"]}
        )
        
        urls = discover_pages(config)
        
        assert "https://example.com/" in urls
        assert "https://example.com/about" in urls
    
    def test_discover_default_to_base_url(self):
        """Test that empty config defaults to base URL."""
        config = WitConfig(
            base_url="https://example.com",
            pages={}
        )
        
        urls = discover_pages(config)
        
        assert "https://example.com" in urls
    
    def test_discover_pages_uses_first_site(self):
        """Test that discover_pages uses the first site for multi-site configs."""
        sites = [
            SiteConfig(
                name="site1",
                base_url="https://site1.com",
                pages={"urls": ["/page1"]}
            ),
            SiteConfig(
                name="site2",
                base_url="https://site2.com",
                pages={"urls": ["/page2"]}
            ),
        ]
        config = WitConfig(sites=sites)
        
        urls = discover_pages(config)
        
        # Should only return pages from first site
        assert "https://site1.com/page1" in urls
        assert "https://site2.com/page2" not in urls


class TestDatePlaceholders:
    """{year} lets a per-year release-notes URL roll over without a config edit."""

    def test_year_is_expanded(self):
        from datetime import date
        from wit.discovery import expand_date_placeholders
        out = expand_date_placeholders("/ai-bi/release-notes/{year}", today=date(2027, 1, 3))
        assert out == "/ai-bi/release-notes/2027"

    def test_month_is_zero_padded(self):
        from datetime import date
        from wit.discovery import expand_date_placeholders
        out = expand_date_placeholders("/notes/{year}/{month}", today=date(2027, 3, 1))
        assert out == "/notes/2027/03"

    def test_plain_urls_untouched(self):
        from wit.discovery import expand_date_placeholders
        assert expand_date_placeholders("/pricing") == "/pricing"

    def test_discover_from_urls_applies_it(self):
        from datetime import date
        from wit.discovery import discover_from_urls
        out = discover_from_urls("https://x.test", ["/notes/{year}"], {})
        assert out == [f"https://x.test/notes/{date.today().year}"]

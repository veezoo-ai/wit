"""Page discovery for wit - sitemap parsing, crawling, URL expansion."""

import re
import time
import xml.etree.ElementTree as ET
from collections import deque
from typing import Callable, TYPE_CHECKING
from datetime import date
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from wit.config import SiteConfig, WitConfig

from wit.utils import get_logger, is_same_domain, matches_pattern, normalize_url


def discover_pages_for_site(site: "SiteConfig", fetch_func: Callable | None = None) -> list[str]:
    """Discover all pages to scrape for a single site.
    
    Args:
        site: SiteConfig instance with page discovery settings.
        fetch_func: Optional custom fetch function for testing.
        
    Returns:
        List of absolute URLs to scrape.
    """
    logger = get_logger()
    pages = site.pages
    urls = set()
    
    # Option 1: Explicit URL list
    if "urls" in pages:
        discovered = discover_from_urls(site.base_url, pages["urls"], site.scraping, fetch_func)
        urls.update(discovered)
        logger.debug(f"Discovered {len(discovered)} pages from URL list")
    
    # Option 2: Sitemap
    if "sitemap" in pages:
        discovered = discover_from_sitemap(site.base_url, pages["sitemap"], site.scraping, fetch_func)
        urls.update(discovered)
        logger.debug(f"Discovered {len(discovered)} pages from sitemap")
    
    # Option 3: Crawl
    if "crawl" in pages:
        crawl_config = pages["crawl"]
        discovered = discover_from_crawl(
            base_url=site.base_url,
            start=crawl_config.get("start", "/"),
            max_depth=crawl_config.get("max_depth", 2),
            max_pages=crawl_config.get("max_pages", 50),
            include=crawl_config.get("include", []),
            exclude=crawl_config.get("exclude", []),
            scraping_config=site.scraping,
            fetch_func=fetch_func,
        )
        urls.update(discovered)
        logger.debug(f"Discovered {len(discovered)} pages from crawling")
    
    # If no discovery method specified, default to just the base URL
    if not urls:
        logger.warning("No page discovery method specified, defaulting to base URL only")
        urls.add(site.base_url)
    
    return sorted(urls)


def discover_pages(config: "WitConfig", fetch_func: Callable | None = None) -> list[str]:
    """Discover all pages to scrape based on configuration.
    
    Deprecated: Use discover_pages_for_site instead for multi-site support.
    This function is kept for backwards compatibility and only returns
    pages for the first site.
    
    Args:
        config: WitConfig instance with page discovery settings.
        fetch_func: Optional custom fetch function for testing.
        
    Returns:
        List of absolute URLs to scrape.
    """
    if config.sites:
        return discover_pages_for_site(config.sites[0], fetch_func)
    return []


def expand_date_placeholders(url: str, today: date | None = None) -> str:
    """Resolve {year} and {month} in a URL pattern to the current date.
    
    Some sites publish a fresh page per period and never offer a stable alias
    (e.g. .../release-notes/2026). Without this, such a URL silently freezes
    on New Year's Day and someone has to remember to bump it.
    """
    if "{" not in url:
        return url
    today = today or date.today()
    return url.replace("{year}", f"{today.year}").replace("{month}", f"{today.month:02d}")


def discover_from_urls(
    base_url: str, 
    urls: list[str], 
    scraping_config: dict,
    fetch_func: Callable | None = None
) -> list[str]:
    """Expand URL patterns (globs) to actual URLs.
    
    Args:
        base_url: Base URL to resolve relative URLs.
        urls: List of URL patterns (may contain * wildcards).
        scraping_config: Scraping configuration for fetching.
        fetch_func: Optional custom fetch function for testing.
        
    Returns:
        List of absolute URLs.
    """
    logger = get_logger()
    result = set()
    
    for url_pattern in urls:
        url_pattern = expand_date_placeholders(url_pattern)
        
        # Check if pattern contains wildcard
        if "*" in url_pattern:
            # Need to fetch the parent page and find matching links
            parent_path = url_pattern.rsplit("/*", 1)[0] or "/"
            parent_url = normalize_url(parent_path, base_url)
            
            logger.debug(f"Expanding pattern {url_pattern} from {parent_url}")
            
            try:
                html = _fetch_html(parent_url, scraping_config, fetch_func)
                soup = BeautifulSoup(html, "lxml")
                
                # Find all links
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    full_url = normalize_url(href, base_url)
                    path = urlparse(full_url).path
                    
                    if is_same_domain(full_url, base_url) and matches_pattern(path, url_pattern):
                        result.add(full_url)
                        
            except Exception as e:
                logger.warning(f"Failed to expand pattern {url_pattern}: {e}")
        else:
            # Direct URL
            result.add(normalize_url(url_pattern, base_url))
    
    return list(result)


def discover_from_sitemap(
    base_url: str, 
    sitemap_path: str,
    scraping_config: dict,
    fetch_func: Callable | None = None
) -> list[str]:
    """Parse sitemap.xml and extract URLs.
    
    Args:
        base_url: Base URL of the website.
        sitemap_path: Path to sitemap (e.g., /sitemap.xml).
        scraping_config: Scraping configuration for fetching.
        fetch_func: Optional custom fetch function for testing.
        
    Returns:
        List of URLs found in sitemap.
    """
    logger = get_logger()
    sitemap_url = normalize_url(sitemap_path, base_url)
    
    try:
        xml_content = _fetch_html(sitemap_url, scraping_config, fetch_func)
        return _parse_sitemap_xml(xml_content, base_url, scraping_config, fetch_func)
    except Exception as e:
        logger.warning(f"Failed to fetch sitemap {sitemap_url}: {e}")
        return []


def _parse_sitemap_xml(
    xml_content: str, 
    base_url: str,
    scraping_config: dict,
    fetch_func: Callable | None = None
) -> list[str]:
    """Parse sitemap XML content and extract URLs.
    
    Handles both regular sitemaps and sitemap indexes.
    """
    logger = get_logger()
    urls = []
    
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        logger.warning(f"Failed to parse sitemap XML: {e}")
        return []
    
    # Handle XML namespaces
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    
    # Check if this is a sitemap index
    sitemap_refs = root.findall(".//sm:sitemap/sm:loc", ns) or root.findall(".//sitemap/loc")
    
    if sitemap_refs:
        # This is a sitemap index, recurse into each sitemap
        logger.debug(f"Found sitemap index with {len(sitemap_refs)} sitemaps")
        for sitemap_ref in sitemap_refs:
            sub_sitemap_url = sitemap_ref.text.strip() if sitemap_ref.text else ""
            if sub_sitemap_url:
                try:
                    sub_content = _fetch_html(sub_sitemap_url, scraping_config, fetch_func)
                    sub_urls = _parse_sitemap_xml(sub_content, base_url, scraping_config, fetch_func)
                    urls.extend(sub_urls)
                except Exception as e:
                    logger.warning(f"Failed to fetch sub-sitemap {sub_sitemap_url}: {e}")
    else:
        # Regular sitemap with URL entries
        url_elements = root.findall(".//sm:url/sm:loc", ns) or root.findall(".//url/loc")
        
        for url_elem in url_elements:
            url = url_elem.text.strip() if url_elem.text else ""
            if url and is_same_domain(url, base_url):
                urls.append(url)
    
    return urls


def discover_from_crawl(
    base_url: str,
    start: str,
    max_depth: int,
    max_pages: int,
    include: list[str],
    exclude: list[str],
    scraping_config: dict,
    fetch_func: Callable | None = None,
) -> list[str]:
    """Crawl site following links up to max_depth.
    
    Args:
        base_url: Base URL of the website.
        start: Starting path to crawl from.
        max_depth: Maximum link depth to follow.
        max_pages: Maximum number of pages to discover.
        include: List of patterns to include (if empty, include all).
        exclude: List of patterns to exclude.
        scraping_config: Scraping configuration for fetching.
        fetch_func: Optional custom fetch function for testing.
        
    Returns:
        List of discovered URLs.
    """
    logger = get_logger()
    
    start_url = normalize_url(start, base_url)
    
    # BFS queue: (url, depth)
    queue = deque([(start_url, 0)])
    visited = set()
    discovered = []
    
    delay = scraping_config.get("delay", 1.0)
    
    while queue and len(discovered) < max_pages:
        url, depth = queue.popleft()
        
        if url in visited:
            continue
        
        visited.add(url)
        
        # Check if URL should be included
        path = urlparse(url).path
        
        if not _should_include_url(path, include, exclude):
            logger.debug(f"Skipping {url} (excluded by pattern)")
            continue
        
        discovered.append(url)
        logger.debug(f"Discovered {url} (depth={depth})")
        
        # Don't crawl deeper if at max depth
        if depth >= max_depth:
            continue
        
        # Fetch page and extract links
        try:
            if len(visited) > 1:  # Add delay except for first request
                time.sleep(delay)
            
            html = _fetch_html(url, scraping_config, fetch_func)
            soup = BeautifulSoup(html, "lxml")
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                
                # Skip anchors, javascript, mailto, etc.
                if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    continue
                
                full_url = normalize_url(href, base_url)
                
                # Only follow links on same domain
                if is_same_domain(full_url, base_url) and full_url not in visited:
                    queue.append((full_url, depth + 1))
                    
        except Exception as e:
            logger.warning(f"Failed to crawl {url}: {e}")
    
    return discovered


def _should_include_url(path: str, include: list[str], exclude: list[str]) -> bool:
    """Check if a URL path should be included based on patterns.
    
    Args:
        path: URL path to check.
        include: Patterns that must match (if empty, include all).
        exclude: Patterns that must not match.
        
    Returns:
        True if URL should be included.
    """
    # Check exclusions first
    for pattern in exclude:
        if matches_pattern(path, pattern):
            return False
    
    # If no include patterns, include everything not excluded
    if not include:
        return True
    
    # Check if matches any include pattern
    for pattern in include:
        if matches_pattern(path, pattern):
            return True
    
    return False


def _fetch_html(url: str, scraping_config: dict, fetch_func: Callable | None = None) -> str:
    """Fetch HTML content from a URL.
    
    Args:
        url: URL to fetch.
        scraping_config: Scraping configuration.
        fetch_func: Optional custom fetch function.
        
    Returns:
        HTML content as string.
    """
    if fetch_func:
        return fetch_func(url)
    
    headers = {"User-Agent": scraping_config.get("user_agent", "wit/1.0")}
    timeout = scraping_config.get("timeout", 30)
    
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    
    return response.text

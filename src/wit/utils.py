"""Utility functions for wit - URL handling, file naming, logging."""

import logging
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode


# Tracking parameters to strip from URLs
# These cause unnecessary diffs between scrapes due to dynamic values
TRACKING_PARAMS = {
    # HubSpot
    "__hstc",
    "__hssc",
    "__hsfp",
    # Google Analytics / Ads
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "gclsrc",
    # Facebook
    "fbclid",
    # Microsoft Ads
    "msclkid",
    # Twitter
    "twclid",
    # LinkedIn
    "li_fat_id",
    # Generic tracking
    "_ga",
    "_gl",
    "mc_cid",
    "mc_eid",
    # Session/cache busting
    "ref",
    "source",
    # Vercel stamps every /_next/image URL with the deployment id, which
    # rotates on each deploy and rewrote every image reference on a tracked
    # Next.js site (12 pages per deploy) without any content changing.
    "dpl",
}


def setup_logging(verbose: bool = False, quiet: bool = False) -> logging.Logger:
    """Set up logging with appropriate level.
    
    Args:
        verbose: If True, set to DEBUG level.
        quiet: If True, set to WARNING level.
        
    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger("wit")
    
    # Clear existing handlers
    logger.handlers = []
    
    if verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    else:
        level = logging.INFO
    
    logger.setLevel(level)
    
    # Create console handler with formatting
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)
    
    # Format: [LEVEL] message
    formatter = logging.Formatter("[%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger


def get_logger() -> logging.Logger:
    """Get the wit logger instance."""
    return logging.getLogger("wit")


def normalize_url(url: str, base_url: str) -> str:
    """Normalize a URL relative to base URL.
    
    Args:
        url: URL to normalize (can be relative or absolute).
        base_url: Base URL to resolve relative URLs against.
        
    Returns:
        Absolute URL.
    """
    # Handle relative URLs
    if url.startswith("/"):
        return urljoin(base_url, url)
    
    # Handle already absolute URLs
    if url.startswith(("http://", "https://")):
        return url
    
    # Handle relative URLs without leading slash
    return urljoin(base_url + "/", url)


def strip_tracking_params(url: str) -> str:
    """Remove tracking parameters from a URL.
    
    Strips common tracking parameters (HubSpot, Google Analytics, Facebook, etc.)
    that cause unnecessary diffs between scrapes due to dynamic nonces and IDs.
    
    Args:
        url: The URL to normalize.
        
    Returns:
        URL with tracking parameters removed.
    """
    try:
        parsed = urlparse(url)
        
        # Skip if no query string
        if not parsed.query:
            return url
        
        # Parse query parameters
        params = parse_qs(parsed.query, keep_blank_values=True)
        
        # Filter out tracking parameters (case-insensitive)
        filtered_params = {
            k: v for k, v in params.items()
            if k.lower() not in TRACKING_PARAMS
        }
        
        # Rebuild URL
        new_query = urlencode(filtered_params, doseq=True) if filtered_params else ""
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        ))
        
        return normalized
    except Exception:
        # If parsing fails, return original URL
        return url


def url_to_filepath(url: str, base_url: str, output_dir: Path) -> Path:
    """Convert a URL to a local file path.
    
    Args:
        url: The URL to convert.
        base_url: The base URL of the website.
        output_dir: The output directory for files.
        
    Returns:
        Path object representing the local file path.
        
    Examples:
        / -> output_dir/index.md
        /about -> output_dir/about.md
        /docs/getting-started -> output_dir/docs/getting-started.md
        /blog/2024/01/post -> output_dir/blog/2024/01/post.md
    """
    # Parse the URL
    parsed = urlparse(url)
    path = parsed.path
    
    # Remove base URL path if present
    base_parsed = urlparse(base_url)
    if base_parsed.path and path.startswith(base_parsed.path):
        path = path[len(base_parsed.path):]
    
    # Clean up the path
    path = path.strip("/")
    
    # Handle root URL
    if not path:
        return output_dir / "index.md"
    
    # Remove file extensions if present
    if path.endswith(".html") or path.endswith(".htm"):
        path = path.rsplit(".", 1)[0]
    
    # Handle trailing slashes (directory index)
    if url.endswith("/") and path:
        path = f"{path}/index"
    
    # Sanitize path components
    parts = path.split("/")
    sanitized_parts = [sanitize_filename(part) for part in parts]
    
    # Build the file path
    filepath = output_dir / "/".join(sanitized_parts[:-1]) / f"{sanitized_parts[-1]}.md" if len(sanitized_parts) > 1 else output_dir / f"{sanitized_parts[0]}.md"
    
    return filepath


def sanitize_filename(name: str) -> str:
    """Sanitize a string to be a valid filename.
    
    Args:
        name: The string to sanitize.
        
    Returns:
        Sanitized filename.
    """
    # Replace problematic characters
    name = re.sub(r'[<>:"/\\|?*]', "-", name)
    
    # Replace multiple dashes with single dash
    name = re.sub(r"-+", "-", name)
    
    # Remove leading/trailing dashes and whitespace
    name = name.strip("- \t")
    
    # Handle empty names
    if not name:
        return "unnamed"
    
    return name


def is_same_domain(url: str, base_url: str) -> bool:
    """Check if a URL belongs to the same domain as the base URL.
    
    Args:
        url: URL to check.
        base_url: Base URL to compare against.
        
    Returns:
        True if URLs are on the same domain.
    """
    parsed_url = urlparse(url)
    parsed_base = urlparse(base_url)
    
    return parsed_url.netloc == parsed_base.netloc or not parsed_url.netloc


def matches_pattern(url: str, pattern: str) -> bool:
    """Check if a URL matches a glob-like pattern.
    
    Args:
        url: URL path to check.
        pattern: Glob pattern (supports * wildcard).
        
    Returns:
        True if URL matches the pattern.
    """
    # Convert glob pattern to regex
    # Escape special regex chars except *
    regex_pattern = re.escape(pattern).replace(r"\*", ".*")
    regex_pattern = f"^{regex_pattern}$"
    
    return bool(re.match(regex_pattern, url))


def extract_path(url: str) -> str:
    """Extract the path component from a URL.
    
    Args:
        url: Full or relative URL.
        
    Returns:
        Path component of the URL.
    """
    parsed = urlparse(url)
    return parsed.path or "/"


def format_commit_message(template: str, changed_files: list[str]) -> str:
    """Format a commit message using the template.
    
    Args:
        template: Message template with {changed_count} and {changed_files} placeholders.
        changed_files: List of changed file paths.
        
    Returns:
        Formatted commit message.
    """
    # Truncate file list if too long
    max_files = 5
    if len(changed_files) > max_files:
        files_str = ", ".join(changed_files[:max_files]) + f", ... (+{len(changed_files) - max_files} more)"
    else:
        files_str = ", ".join(changed_files)
    
    return template.format(
        changed_count=len(changed_files),
        changed_files=files_str,
    )

# wit - Website in Git

[![PyPI version](https://badge.fury.io/py/wit.svg)](https://badge.fury.io/py/wit)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**wit** scrapes websites and stores the content as markdown files in a git repository. It handles fetching, HTML-to-markdown conversion, and git commits. Designed to run in GitHub Actions for automated website tracking.

## Features

- 📦 **Standalone pip-installable package**
- 🖥️ **CLI interface** for easy use in GitHub Actions
- ⚙️ **Configurable via YAML** config file
- 📄 **Support for multiple pages/URLs**
- 🌐 **Multi-site support** - track multiple websites in one config
- 🗺️ **Sitemap support** (auto-discover pages)
- 🔄 **HTML to clean markdown** conversion
- 🎯 **Selective content extraction** (CSS selectors)
- 🌐 **JavaScript rendering** support (optional, via Playwright)
- 📝 **Automatic git commit** with meaningful messages
- ✨ **Incremental updates** (only commit if content changed)
- 🤖 **Polite scraping** (configurable delays, user-agent)

## Installation

```bash
pip install wit
```

For JavaScript rendering support (SPAs, dynamic content):

```bash
pip install 'wit[js]'
playwright install chromium
```

## Quick Start

### Initialize a config file

```bash
wit init --base-url https://example.com
```

This creates a `wit.yaml` configuration file.

### Scrape a website

```bash
wit scrape
```

### Scrape and commit changes

```bash
wit scrape --commit
```

### Scrape a single URL (ad-hoc)

```bash
wit scrape-url https://example.com/page --output content/page.md
```

### List pages (dry run)

```bash
wit list
```

## CLI Reference

```bash
# Scrape using config file (default: wit.yaml)
wit scrape

# Scrape with custom config
wit scrape --config my-config.yaml

# Scrape and commit changes
wit scrape --commit

# Scrape only specific site(s) from multi-site config
wit scrape --site docs
wit scrape --site docs,blog  # comma-separated

# Scrape a single URL (ad-hoc, no config needed)
wit scrape-url https://example.com/page --output content/page.md

# Initialize a new config file
wit init

# Initialize a multi-site config template
wit init --multi-site

# List pages that would be scraped (dry run)
wit list
wit list --site docs  # list pages from specific site only

# List all configured sites
wit sites

# Verbose output
wit -v scrape

# Quiet mode (warnings only)
wit -q scrape
```

## Configuration

### `wit.yaml`

```yaml
# Required: base URL of the website
base_url: https://example.com

# Output directory for markdown files
output_dir: content

# How to discover pages (choose one or combine)
pages:
  # Option 1: explicit list
  urls:
    - /
    - /about
    - /pricing
    - /docs
    - /blog/*  # glob pattern - scrape all matching links
    - /release-notes/{year}  # {year} and {month} resolve to today's date,
                             # for sites that publish one page per period
  
  # Option 2: sitemap
  sitemap: /sitemap.xml
  
  # Option 3: crawl from start page
  crawl:
    start: /
    max_depth: 2
    max_pages: 50
    include: 
      - /docs/*
      - /blog/*
    exclude:
      - /admin/*
      - /api/*

# Content extraction
selectors:
  # Main content (first match wins)
  content:
    - main
    - article
    - .content
    - .post-body
    - "#main-content"
  
  # Elements to remove before conversion
  remove:
    - nav
    - footer
    - header
    - script
    - style
    - .ads
    - .sidebar
    - .comments
    - "#cookie-banner"
  
  # Optional: extract title separately
  title: h1

# Scraping behavior
scraping:
  delay: 1.0              # seconds between requests
  timeout: 30             # request timeout
  user_agent: "wit/1.0"   # custom user agent
  javascript: false       # enable JS rendering (requires playwright)
  
# Markdown conversion options
markdown:
  heading_style: atx      # atx (#) or setext (underline)
  strip_links: false      # remove hyperlinks
  include_images: true    # include image references
  code_language: auto     # try to detect code block languages

# Git commit settings (used with --commit flag)
git:
  author_name: wit[bot]
  author_email: wit[bot]@users.noreply.github.com
  message_template: "Update {changed_count} page(s): {changed_files}"

# Metadata
metadata:
  include_source_url: true
  include_timestamp: true
  include_title: true
```

## Output Format

### Markdown File Structure

```markdown
---
source: https://example.com/about
scraped_at: 2024-01-15T10:30:00Z
title: About Us
---

# About Us

Company description goes here...

## Our Mission

More content...
```

### File Naming

URLs are converted to filenames:

| URL | Filename |
|-----|----------|
| `/` | `index.md` |
| `/about` | `about.md` |
| `/docs/getting-started` | `docs/getting-started.md` |
| `/blog/2024/01/post` | `blog/2024/01/post.md` |

Directory structure mirrors URL structure.

## GitHub Actions Usage

### Basic tracking workflow

```yaml
name: Track Website

on:
  schedule:
    - cron: '0 */6 * * *'  # every 6 hours
  workflow_dispatch:

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install wit
        run: pip install wit

      - name: Scrape and commit
        run: wit scrape --commit

      - name: Push changes
        run: git push
```

### With JavaScript Rendering

```yaml
      - name: Install wit with JS support
        run: |
          pip install 'wit[js]'
          playwright install chromium

      - name: Scrape (with JS)
        run: wit scrape --commit
```

## Example Configurations

### Simple Blog Tracker

```yaml
base_url: https://blog.example.com
output_dir: posts

pages:
  sitemap: /sitemap.xml

selectors:
  content: [article, .post-content]
  remove: [.comments, .share-buttons, .related-posts]
  title: h1.post-title
```

### Documentation Site

```yaml
base_url: https://docs.example.com
output_dir: docs

pages:
  crawl:
    start: /
    max_depth: 3
    include: [/docs/*, /api/*]
    exclude: [/docs/v1/*]  # skip old versions

selectors:
  content: [.docs-content, main]
  remove: [nav, .sidebar, .toc, footer]

scraping:
  delay: 0.5
```

### JavaScript-Heavy SPA

```yaml
base_url: https://app.example.com
output_dir: content

pages:
  urls:
    - /features
    - /pricing
    - /changelog

scraping:
  javascript: true
  timeout: 60

selectors:
  content: ["#app main", .page-content]
  remove: [.modal, .toast, .loading-spinner]
```

### Multi-Site Tracking

Track multiple websites in a single config file:

```yaml
# Define multiple sites to track
sites:
  - name: docs
    base_url: https://docs.example.com
    output_dir: content/docs
    pages:
      sitemap: /sitemap.xml
    selectors:
      content: [.docs-content, main]
  
  - name: blog
    base_url: https://blog.example.com
    output_dir: content/blog
    pages:
      crawl:
        start: /
        max_depth: 2
    selectors:
      content: [article, .post-content]
  
  - name: changelog
    base_url: https://changelog.example.com
    output_dir: content/changelog
    pages:
      urls:
        - /

# Global settings (apply to all sites unless overridden)
selectors:
  remove: [nav, footer, header, .ads, .sidebar]

scraping:
  delay: 1.0
  timeout: 30

git:
  message_template: "Update {changed_count} page(s): {changed_files}"
```

Then scrape all sites or specific ones:

```bash
# Scrape all sites
wit scrape

# Scrape only the docs site
wit scrape --site docs

# Scrape docs and blog
wit scrape --site docs,blog

# List all configured sites
wit sites

# List pages from specific site
wit list --site blog
```

## Error Handling

| Error | Behavior |
|-------|----------|
| Network timeout | Retry up to 3 times, then skip with warning |
| 404 Not Found | Skip page, log warning |
| 5xx Server Error | Retry with backoff, then skip |
| Rate limiting (429) | Respect Retry-After header |
| Invalid HTML | Best-effort conversion, log warning |
| JS render timeout | Fall back to static HTML if possible |

Failed pages do not prevent other pages from being scraped.

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/open-veezoo/wit.git
cd wit

# Install with dev dependencies
pip install -e '.[dev]'

# Run tests
pytest
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=wit --cov-report=html

# Run specific tests
pytest tests/test_config.py -v
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Notes

- Respect robots.txt by default (configurable)
- Include reasonable default user-agent identifying the tool
- Playwright is optional — most sites work with plain requests
- Git operations assume the tool runs inside a git repo
- The tool does NOT push changes — that's left to the CI workflow

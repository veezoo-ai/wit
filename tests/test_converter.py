"""Tests for converter module."""

import pytest

from wit.converter import html_to_markdown, add_metadata


class TestHtmlToMarkdown:
    """Tests for html_to_markdown function."""
    
    def test_simple_html(self):
        """Test converting simple HTML."""
        html = "<h1>Title</h1><p>Some text here.</p>"
        result = html_to_markdown(html, {})
        
        assert "# Title" in result
        assert "Some text here." in result
    
    def test_heading_levels(self):
        """Test converting different heading levels."""
        html = "<h1>H1</h1><h2>H2</h2><h3>H3</h3>"
        result = html_to_markdown(html, {"heading_style": "atx"})
        
        assert "# H1" in result
        assert "## H2" in result
        assert "### H3" in result
    
    def test_paragraph(self):
        """Test converting paragraphs."""
        html = "<p>First paragraph.</p><p>Second paragraph.</p>"
        result = html_to_markdown(html, {})
        
        assert "First paragraph." in result
        assert "Second paragraph." in result
    
    def test_links(self):
        """Test converting links."""
        html = '<p>Check out <a href="https://example.com">this link</a>.</p>'
        result = html_to_markdown(html, {})
        
        assert "[this link](https://example.com)" in result
    
    def test_strip_links(self):
        """Test stripping links option."""
        html = '<p>Check out <a href="https://example.com">this link</a>.</p>'
        result = html_to_markdown(html, {"strip_links": True})
        
        assert "[" not in result
        assert "this link" in result
    
    def test_normalize_urls_strips_tracking_params(self):
        """Test that normalize_urls strips tracking parameters from links."""
        html = '<p><a href="https://example.com/page?utm_source=google&id=123">Link</a></p>'
        result = html_to_markdown(html, {"normalize_urls": True})
        
        assert "utm_source" not in result
        assert "id=123" in result
        assert "[Link]" in result
    
    def test_normalize_urls_strips_fbclid(self):
        """Test stripping Facebook click ID from links."""
        html = '<p><a href="https://example.com/page?fbclid=abc123">Link</a></p>'
        result = html_to_markdown(html, {"normalize_urls": True})
        
        assert "fbclid" not in result
        assert "https://example.com/page" in result
    
    def test_normalize_urls_strips_hubspot_params(self):
        """Test stripping HubSpot tracking parameters from links."""
        html = '<p><a href="https://example.com/page?__hstc=abc&__hssc=def">Link</a></p>'
        result = html_to_markdown(html, {"normalize_urls": True})
        
        assert "__hstc" not in result
        assert "__hssc" not in result
    
    def test_normalize_urls_default_enabled(self):
        """Test that URL normalization is enabled by default."""
        html = '<p><a href="https://example.com/page?utm_source=google">Link</a></p>'
        result = html_to_markdown(html, {})  # No options, use defaults
        
        assert "utm_source" not in result
    
    def test_normalize_urls_can_be_disabled(self):
        """Test that URL normalization can be disabled."""
        html = '<p><a href="https://example.com/page?utm_source=google">Link</a></p>'
        result = html_to_markdown(html, {"normalize_urls": False})
        
        assert "utm_source" in result
    
    def test_normalize_urls_preserves_non_tracking_params(self):
        """Test that non-tracking query parameters are preserved."""
        html = '<p><a href="https://example.com/search?q=test&page=2">Link</a></p>'
        result = html_to_markdown(html, {"normalize_urls": True})
        
        assert "q=test" in result
        assert "page=2" in result
    
    def test_images(self):
        """Test converting images."""
        html = '<img src="image.png" alt="Description">'
        result = html_to_markdown(html, {"include_images": True})
        
        assert "![Description](image.png)" in result
    
    def test_exclude_images(self):
        """Test excluding images option."""
        html = '<p>Text <img src="image.png" alt="Description"> more text</p>'
        result = html_to_markdown(html, {"include_images": False})
        
        assert "image.png" not in result
    
    def test_lists(self):
        """Test converting lists."""
        html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        result = html_to_markdown(html, {})
        
        assert "- Item 1" in result or "* Item 1" in result
        assert "- Item 2" in result or "* Item 2" in result
    
    def test_ordered_lists(self):
        """Test converting ordered lists."""
        html = "<ol><li>First</li><li>Second</li></ol>"
        result = html_to_markdown(html, {})
        
        assert "1." in result
        assert "First" in result
        assert "Second" in result
    
    def test_code_block(self):
        """Test converting code blocks."""
        html = "<pre><code>print('hello')</code></pre>"
        result = html_to_markdown(html, {})
        
        assert "```" in result
        assert "print('hello')" in result
    
    def test_code_block_with_language(self):
        """Test converting code blocks with language class."""
        html = '<pre><code class="language-python">print("hello")</code></pre>'
        result = html_to_markdown(html, {"code_language": "auto"})
        
        assert "```python" in result
    
    def test_inline_code(self):
        """Test converting inline code."""
        html = "<p>Use <code>git commit</code> to save.</p>"
        result = html_to_markdown(html, {})
        
        assert "`git commit`" in result
    
    def test_bold_text(self):
        """Test converting bold text."""
        html = "<p>This is <strong>important</strong>.</p>"
        result = html_to_markdown(html, {})
        
        assert "**important**" in result
    
    def test_italic_text(self):
        """Test converting italic text."""
        html = "<p>This is <em>emphasized</em>.</p>"
        result = html_to_markdown(html, {})
        
        assert "*emphasized*" in result
    
    def test_blockquote(self):
        """Test converting blockquotes."""
        html = "<blockquote>A quote here.</blockquote>"
        result = html_to_markdown(html, {})
        
        assert "> A quote" in result or ">A quote" in result
    
    def test_table(self):
        """Test converting tables."""
        html = """
        <table>
            <tr><th>Name</th><th>Value</th></tr>
            <tr><td>A</td><td>1</td></tr>
        </table>
        """
        result = html_to_markdown(html, {})
        
        assert "Name" in result
        assert "Value" in result
    
    def test_cleanup_excessive_newlines(self):
        """Test that excessive newlines are cleaned up."""
        html = "<p>Text</p>\n\n\n\n\n<p>More text</p>"
        result = html_to_markdown(html, {})
        
        # Should not have more than 2 consecutive blank lines
        assert "\n\n\n\n" not in result


class TestAddMetadata:
    """Tests for add_metadata function."""
    
    def test_add_source_url(self):
        """Test adding source URL metadata."""
        result = add_metadata(
            "# Title\n\nContent",
            "https://example.com/page",
            None,
            {"include_source_url": True, "include_timestamp": False, "include_title": False}
        )
        
        assert "---" in result
        assert "source: https://example.com/page" in result
    
    def test_add_timestamp(self):
        """Test adding timestamp metadata."""
        result = add_metadata(
            "# Title\n\nContent",
            "https://example.com/page",
            None,
            {"include_source_url": False, "include_timestamp": True, "include_title": False}
        )
        
        assert "scraped_at:" in result
    
    def test_add_title(self):
        """Test adding title metadata."""
        result = add_metadata(
            "Content",
            "https://example.com/page",
            "My Page Title",
            {"include_source_url": False, "include_timestamp": False, "include_title": True}
        )
        
        assert 'title: "My Page Title"' in result
    
    def test_all_metadata(self):
        """Test adding all metadata."""
        result = add_metadata(
            "Content",
            "https://example.com/page",
            "Title",
            {"include_source_url": True, "include_timestamp": True, "include_title": True}
        )
        
        assert "---" in result
        assert "source:" in result
        assert "scraped_at:" in result
        assert "title:" in result
    
    def test_no_metadata(self):
        """Test with no metadata enabled."""
        result = add_metadata(
            "Content",
            "https://example.com/page",
            "Title",
            {"include_source_url": False, "include_timestamp": False, "include_title": False}
        )
        
        assert "---" not in result
        assert result == "Content"
    
    def test_title_with_quotes(self):
        """Test title with quotes is escaped."""
        result = add_metadata(
            "Content",
            "https://example.com/page",
            'Title with "quotes"',
            {"include_source_url": False, "include_timestamp": False, "include_title": True}
        )
        
        assert '\\"quotes\\"' in result


class TestBlobUrls:
    """blob: URLs are per-load UUIDs from video players and carry no signal."""

    def test_blob_link_keeps_text_and_drops_href(self):
        from wit.converter import html_to_markdown
        html = '<p><a href="blob:https://example.com/680f408d-4ebe">Watch</a></p>'
        md = html_to_markdown(html, {})
        assert "Watch" in md
        assert "blob:" not in md

    def test_blob_image_is_dropped(self):
        from wit.converter import html_to_markdown
        html = '<p>before <img src="blob:https://example.com/5fc8a687" alt="x"> after</p>'
        md = html_to_markdown(html, {})
        assert "blob:" not in md
        assert "before" in md and "after" in md

    def test_blob_video_is_dropped(self):
        """<video src=blob:> is what Wistia embeds actually produce."""
        from wit.converter import html_to_markdown
        html = ('<p>intro</p><video poster="https://fast.wistia.com/blank.gif" '
                'src="blob:https://example.com/727a6c17"></video><p>outro</p>')
        md = html_to_markdown(html, {})
        assert "blob:" not in md
        assert "blank.gif" not in md
        assert "intro" in md and "outro" in md

    def test_ordinary_links_untouched(self):
        from wit.converter import html_to_markdown
        md = html_to_markdown('<a href="https://example.com/p">p</a>', {})
        assert "https://example.com/p" in md

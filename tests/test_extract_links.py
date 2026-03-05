from crawler import extract_links

def test_extract_links_basic():
    html = '<a href="/blog">Blog</a>'
    sites = []
    links = extract_links(html, "https://example.com/", "https://example.com/", sites)
    assert "https://example.com/blog/" in links

def test_extract_links_no_duplicates():
    html = '<a href="/blog">Blog</a><a href="/blog/">Blog</a>'
    sites = []
    links = extract_links(html, "https://example.com/", "https://example.com/", sites)
    assert len(links) == 1

def test_extract_links_ignores_external():
    html = '<a href="https://other.com/page">Extern</a>'
    sites = []
    links = extract_links(html, "https://example.com/", "https://example.com/", sites)
    assert len(links) == 0

def test_extract_links_ignores_mailto():
    html = '<a href="mailto:test@example.com">Mail</a>'
    sites = []
    links = extract_links(html, "https://example.com/", "https://example.com/", sites)
    assert len(links) == 0

def test_extract_links_ignores_empty_href():
    html = '<a href="">Empty</a>'
    sites = []
    links = extract_links(html, "https://example.com/", "https://example.com/", sites)
    assert len(links) == 0

def test_extract_links_self_link():
    html = '<a href="/">Home</a>'
    sites = ["https://example.com/"]
    extract_links(html, "https://example.com/", "https://example.com/", sites)
    assert len(sites) == 1

def test_extract_links_query_string():
    """Ignore query strings"""
    html = '<a href="/blog?page=1">Blog</a><a href="/blog?page=2">Blog 2</a>'
    sites = []
    links = extract_links(html, "https://example.com/", "https://example.com/", sites)
    assert len(links) == 1
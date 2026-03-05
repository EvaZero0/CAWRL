from crawler import normalize_url

def test_normalize_url_adds_scheme():
    assert normalize_url("example.com") == "https://example.com/"

def test_normalize_url_adds_trailing_slash():
    assert normalize_url("https://example.com") == "https://example.com/"

def test_normalize_url_keeps_existing_scheme():
    assert normalize_url("http://example.com") == "http://example.com/"

def test_normalize_url_already_normalized():
    assert normalize_url("https://example.com/") == "https://example.com/"


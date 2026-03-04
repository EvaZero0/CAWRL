# 🐍 CAWRL 🕷️

A web crawler and broken link checker with a browser-based dashboard. Built with Python and FastAPI.

---

## Features

- Crawls all internal pages of a website starting from a given URL
- Detects broken links (HTTP 4xx / 5xx / timeouts)
- Respects `robots.txt` (RFC 9309 compliant via [Protego](https://github.com/scrapy/protego)), with an option to disable
- Live log and stats dashboard in the browser via Server-Sent Events
- Configurable page limit and crawl delay
- Stop button to cancel a running crawl
- JSON export of crawl results

---

## Requirements

- Python 3.x **or** Docker

---

## Getting started

### With Docker (recommended)

```bash
git clone https://github.com/EvaZero0/CAWRL
cd cawrl
docker compose up --build
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

No Python installation required – Docker handles everything.

### Without Docker

```bash
pip install -r requirements.txt
python app.py
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Project structure

```
CAWRL/
├── app.py              # FastAPI backend, SSE streaming, stop/export endpoints
├── crawler.py          # Core crawl logic (requests + BeautifulSoup + Protego)
├── index.html          # Dashboard HTML
├── static/
│   ├── style.css
│   └── script.js
├── requirements.txt
├── Dockerfile
└── compose.yaml
```

---

## Usage

1. Enter a URL in the input field (without `https://`)
2. Configure the options:
   - **Respect robots.txt** — toggle to ignore `robots.txt` rules if needed
   - **Max. pages** — limit how many pages the crawler visits
   - **No limit** — disables the page limit (use with caution on large sites)
   - **Delay** — time in seconds between requests, to avoid overloading servers
3. Click **Start**
4. Watch the live log and broken links panel update in real time
5. Click **Stop** to cancel at any time
6. Use **Export JSON** to download the full crawl result

---

## Notes

- The crawler only follows internal links (same domain as the start URL)
- XML files are skipped
- Only one crawl can run at a time
- `robots.txt` is parsed for both the `*` and `CAWRL` user-agent blocks

---

## Dependencies

| Package | Purpose |
|---|---|
| `requests` | HTTP requests |
| `beautifulsoup4` | HTML parsing |
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `protego` | robots.txt parsing (RFC 9309) |

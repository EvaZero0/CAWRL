import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse  #, urldefrag
import protego
import time

HEADERS = {
    "User-Agent": "CAWRL/1.0"                                       #Identify the crawler to web servers
}


def normalize_url(url):
    """Normalizes a URL by ensuring it has a scheme and trailing slash."""
    parsed = urlparse(url)
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc or parsed.path                            #If no netloc, input was probably "example.com" without scheme
    path = parsed.path if parsed.netloc else ""
    if not path.endswith("/"):
        path += "/"
    return f"{scheme}://{netloc}{path}"


def get_start_url(url):
    """Normalizes the input URL and follows redirects to get the actual start URL.
    Returns both the normalized input URL (for robots.txt) and the final URL after redirects."""
    input_url = normalize_url(url)
    redirect_response = requests.get(input_url, allow_redirects=True, headers=HEADERS)  #Follow redirect and get final URL
    start_url = normalize_url(redirect_response.url)
    return input_url, start_url


def get_robots(input_url):
    """Fetches and parses robots.txt using Protego (RFC 9309 compliant).
    Returns a tuple of (found: bool, robots_text: str, parser: protego.Protego|None)."""
    robots_url = input_url + "robots.txt"                            #Construct the URL for robots.txt from the base URL
    robots_response = requests.get(robots_url, headers=HEADERS)     #Fetch the robots.txt file
    if not robots_response.ok:
        print("No robots.txt found!")
        return False, "", None                                       #Return None parser if robots.txt not found
    robots_text = robots_response.text
    print(robots_text)                                               #Print the robots.txt content for debugging
    rp = protego.Protego.parse(robots_text)                          #Parse robots.txt using Protego (RFC 9309)
    return True, robots_text, rp                                     #Return found, raw text, and the parser object


def fetch_page(url):
    """Fetches the HTML content of a page.
    Returns a tuple of (html: str|None, status_code: int, load_time: float)."""
    start_time = time.time()
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        load_time = round(time.time() - start_time, 2)
        if response.status_code >= 400:                              #Treat 4xx and 5xx as broken links
            print(f"Broken link ({response.status_code}): {url}")
            return None, response.status_code, load_time
        return response.text, response.status_code, load_time
    except requests.exceptions.RequestException as e:
        load_time = round(time.time() - start_time, 2)
        print(f"Error fetching {url}: {e}")
        return None, 0, load_time                                    #Return status 0 on connection error / timeout


def extract_title(html):
    """Extracts the title of an HTML page and returns it as a string."""
    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.string:                             #Check if title exists and is not empty
        return soup.title.string
    return "No title found"                                          #Fallback if title is missing or empty


def extract_links(html, url, start_url, sites):
    """Extracts all links from an HTML page, adds new ones to the sites queue and returns all found links."""
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a"):
        href = a.get("href")
        if href and not ("@" in href or "#" in href or href.startswith("mailto:") or href.startswith("tel:") or href.startswith("javascript:")):
            absolute_href = urljoin(url, href)                       #Build absolute URL from the current URL and the found link
            if absolute_href.startswith(start_url):                  #Only add links that are on the same domain
                if absolute_href not in sites:
                    sites.append(absolute_href)
                links.add(absolute_href)
    return links


def crawl(start_url, rp, respect_robots, max_pages=200, crawl_delay=0.5, callback=None, stop_event=None):
    """Crawls all pages starting from start_url, respects robots.txt if enabled.
    max_pages=0 means no limit. Calls callback(event) after each page if provided.
    Returns a list of all crawled pages with their titles and links."""
    sites = [start_url]                                              #List of sites to crawl, starting with the start URL
    all_data = []
    broken_links = []
    i = 0

    while i < len(sites):
        if stop_event and stop_event.is_set():                           #Stop if stop event is set
            print("Crawl stopped by user.")
            break

        current_url = sites[i]

        if ".xml" in current_url:                                    #Skip XML files
            i += 1
            continue

        if respect_robots and rp and not rp.can_fetch(current_url, "CAWRL"):  #Check robots.txt rules using Protego
            if callback:
                callback({"type": "skip", "url": current_url, "reason": "robots.txt"})
            i += 1
            continue

        if callback:
            callback({"type": "crawling", "url": current_url, "count": i + 1})

        html_content, status_code, load_time = fetch_page(current_url)

        if status_code >= 400 or status_code == 0:                   #Broken link detected
            broken_links.append({"url": current_url, "status": status_code})
            if callback:
                callback({"type": "broken", "url": current_url, "status": status_code})
            i += 1
            continue

        if html_content:
            title = extract_title(html_content)
            print(title)
            print("=> " + current_url)
            links = extract_links(html_content, current_url, start_url, sites)
            all_data.append({
                "Site": title + ": " + current_url,                  #Page title and URL
                "Links": list(links)                                  #All links found on this page
            })
            if callback:
                callback({
                    "type": "page_done",
                    "url": current_url,
                    "title": title,
                    "status": status_code,
                    "load_time": load_time,
                    "links_found": len(links),
                })
            time.sleep(crawl_delay)                                  #Be polite to the server

        i += 1

    summary = {
        "total_pages": len(all_data),
        "broken_count": len(broken_links),
        "broken_links": broken_links,
        "avg_load_time": 0.0,
        "pages": all_data,
    }

    if callback:
        callback({"type": "done", **summary})

    return summary
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import threading
import queue
import json
import os

from crawler import get_start_url, get_robots, crawl

app = FastAPI()

# Serve CSS and JS from the static/ folder
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

# Global state for the current crawl session
crawl_state = {
    "running": False,
    "summary": None,
    "event_queue": queue.Queue(),
}

stop_event = threading.Event()

class CrawlRequest(BaseModel):
    """Request body for starting a crawl."""
    url: str
    respect_robots: bool = True
    max_pages: int = 200                                             #0 = no limit
    crawl_delay: float = 0.5


@app.get("/", response_class=HTMLResponse)
def index():
    """Serve the dashboard frontend."""
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, encoding="utf-8") as f:
        return f.read()


@app.post("/start")
def start_crawl(req: CrawlRequest):
    """Start a new crawl in a background thread. Returns robots.txt info to the frontend."""
    if crawl_state["running"]:
        return JSONResponse({"error": "A crawl is already running"}, status_code=409)

    try:
        input_url, start_url = get_start_url(req.url)               #Normalize URL and follow redirects
    except Exception as e:
        return JSONResponse({"error": f"Could not reach URL: {e}"}, status_code=400)

    found, robots_text, rp = get_robots(input_url)                  #Fetch and parse robots.txt

    # Reset crawl state for new session
    crawl_state["running"] = True
    crawl_state["summary"] = None
    crawl_state["event_queue"] = queue.Queue()

    def run():
        """Run the crawl in a background thread and push events into the queue."""
        def cb(event):
            crawl_state["event_queue"].put(event)

        summary = crawl(
            start_url=start_url,
            rp=rp,
            respect_robots=req.respect_robots,
            max_pages=req.max_pages,
            crawl_delay=req.crawl_delay,
            callback=cb,
            stop_event=stop_event,
        )
        crawl_state["summary"] = summary
        crawl_state["running"] = False

    stop_event.clear()                                                   #Reset stop flag for new crawl

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    robots_info = {
        "found": found,
        "disallow_count": sum(1 for line in robots_text.splitlines() if line.strip().lower().startswith("disallow:") and line.split(":",1)[1].strip()),  #Count non-empty disallow rules
        "base_url": start_url,
    }
    return JSONResponse({"status": "started", "robots": robots_info})


@app.get("/stream")
def stream_events():
    """Stream crawl events to the frontend via Server-Sent Events."""
    def event_generator():
        while True:
            try:
                event = crawl_state["event_queue"].get(timeout=30)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") == "done":                      #Close stream when crawl is done
                    break
            except Exception:
                break                                                #Close stream on timeout or error

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/status")
def status():
    """Returns the current crawl status."""
    return JSONResponse({
        "running": crawl_state["running"],
        "has_summary": crawl_state["summary"] is not None,
    })


@app.post("/stop")
def stop_crawl():
    """Signals the crawl thread to stop after the current page."""
    stop_event.set()
    crawl_state["running"] = False
    return JSONResponse({"status": "stopping"})


@app.get("/export")
def export():
    """Returns the full crawl summary as JSON for download."""
    if not crawl_state["summary"]:
        return JSONResponse({"error": "No crawl data available"}, status_code=404)
    return JSONResponse(crawl_state["summary"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
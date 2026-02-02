import os
import re
import json
import subprocess
import sys
from datetime import datetime

# ---------------------------------------------------------
# AUTO-INSTALL REQUIRED PACKAGES
# ---------------------------------------------------------
try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

try:
    import yt_dlp
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
    import yt_dlp


# ---------------------------------------------------------
# PATHS — AUTOMATIC, NO EDITS NEEDED
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTICLES_DIR = os.path.join(BASE_DIR, "articles")
DATA_JSON = os.path.join(BASE_DIR, "data.json")

os.makedirs(ARTICLES_DIR, exist_ok=True)


# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
CHANNEL_URL = "https://www.youtube.com/channel/UCc_YGWm25v8oKIhMoQDQRLA"

LMSTUDIO_API_URL = "http://127.0.0.1:1234/v1/chat/completions"
LMSTUDIO_MODEL = "qwen2.5-3b-instruct"

BRAND_NAME = "Banking With Billy"
PRIMARY_COLOR = "#020617"
ACCENT_COLOR = "#f97316"


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def clean_name(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()


def call_lmstudio(meta: dict) -> str:
    title = meta["title"]
    description = meta.get("description", "")
    tags = meta.get("tags", [])
    channel = meta.get("uploader", "")
    upload_date = meta.get("upload_date", "")

    prompt = f"""
You are a senior financial journalist trained in Bloomberg, Reuters, and AP News.
Turn the metadata into a clean, professional article.

Metadata:
- Title: {title}
- Channel: {channel}
- Upload date: {upload_date}
- Description:
{description}

- Tags: {", ".join(tags)}

Follow this exact structure:

HEADLINE:
SUBHEADLINE:
LEAD:
BODY:
WHY IT MATTERS:
WHAT'S NEXT:

Rules:
- No emojis
- No slang
- No fiction
- No rhetorical questions
- No exclamation marks
- AP style
- Bloomberg clarity
- Reuters neutrality
"""

    payload = {
        "model": LMSTUDIO_MODEL,
        "messages": [
            {"role": "system", "content": "You are a senior journalist for Banking With Billy."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6,
        "max_tokens": 1200,
    }

    resp = requests.post(LMSTUDIO_API_URL, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def extract_block(text: str, label: str) -> str:
    pattern = rf"{label}:\s*(.*?)(?=\n[A-Z ]+?:|\Z)"
    m = re.search(pattern, text, flags=re.S)
    return m.group(1).strip() if m else ""


# ---------------------------------------------------------
# YOUTUBE METADATA ONLY (NO DOWNLOADS)
# ---------------------------------------------------------
def get_latest_video():
    ydl_opts = {
        "quiet": True,
        "extract_flat": False,
        "playlistend": 1,
        "forcejson": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(CHANNEL_URL, download=False)
        latest = info["entries"][0]

        video_id = latest["id"]
        thumb = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"

        return {
            "id": video_id,
            "title": latest["title"],
            "description": latest.get("description", ""),
            "uploader": latest.get("uploader", ""),
            "upload_date": latest.get("upload_date", ""),
            "tags": latest.get("tags", []),
            "webpage_url": f"https://www.youtube.com/watch?v={video_id}",
            "thumbnail_url": thumb
        }


# ---------------------------------------------------------
# ARTICLE BUILDER (EMBED ONLY)
# ---------------------------------------------------------
def build_article_html(meta, article_text):
    video_id = meta["id"]
    headline = extract_block(article_text, "HEADLINE")
    subheadline = extract_block(article_text, "SUBHEADLINE")
    lead = extract_block(article_text, "LEAD")
    body = extract_block(article_text, "BODY")
    why = extract_block(article_text, "WHY IT MATTERS")
    nxt = extract_block(article_text, "WHAT'S NEXT")

    body_html = "".join(f"<p>{p}</p>" for p in body.split("\n") if p.strip())
    why_html = "".join(f"<li>{l.strip('- ').strip()}</li>" for l in why.splitlines() if l.strip())

    year = datetime.now().year

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{headline} | {BRAND_NAME}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="description" content="{subheadline[:160].replace('"', '')}">
  <style>
    :root {{
      --bg: {PRIMARY_COLOR};
      --fg: #e5e7eb;
      --accent: {ACCENT_COLOR};
      --card: #020617;
      --border: #111827;
    }}
    body {{
      font-family: system-ui, sans-serif;
      background: var(--bg);
      color: var(--fg);
      padding: 2rem;
      line-height: 1.7;
    }}
    .shell {{ max-width: 960px; margin: 0 auto; }}
    iframe {{
      width: 100%;
      height: 420px;
      border-radius: 1rem;
      margin-bottom: 1rem;
    }}
    h1 {{ font-size: 2rem; margin-bottom: .5rem; }}
    .subheadline {{ color: #9ca3af; margin-bottom: 1rem; }}
    .lead {{ margin-bottom: 1.5rem; }}
    .body p {{ margin-bottom: 1rem; }}
    footer {{ margin-top: 3rem; color: #6b7280; }}
  </style>
</head>
<body>
  <div class="shell">

    <iframe 
      src="https://www.youtube.com/embed/{video_id}" 
      frameborder="0" 
      allowfullscreen>
    </iframe>

    <h1>{headline}</h1>
    <div class="subheadline">{subheadline}</div>
    <div class="lead">{lead}</div>

    <section class="body">{body_html}</section>

    <h2>Why it matters</h2>
    <ul>{why_html}</ul>

    <h2>What’s next</h2>
    <p>{nxt}</p>

    <footer>© {year} {BRAND_NAME}</footer>
  </div>
</body>
</html>
"""


# ---------------------------------------------------------
# MAIN ENGINE
# ---------------------------------------------------------
def run_engine():
    print("Fetching latest video metadata...")
    meta = get_latest_video()

    print("Generating article text via LM Studio...")
    article_text = call_lmstudio(meta)

    print("Building HTML article...")
    page_title = clean_name(meta["title"])
    html = build_article_html(meta, article_text)

    out_path = os.path.join(ARTICLES_DIR, page_title + ".html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print("Updating data.json...")
    data = {
        "headline": extract_block(article_text, "HEADLINE"),
        "summary": extract_block(article_text, "SUBHEADLINE"),
        "thumbnail": meta["thumbnail_url"],
        "source": meta.get("uploader", ""),
        "time": meta.get("upload_date", ""),
        "trending": "Latest Video",
        "top_story": True,
        "video_url": meta["webpage_url"]
    }

    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print("Done.")
    return out_path


if __name__ == "__main__":
    run_engine()

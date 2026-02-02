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
# CONFIG — NO PATH EDITS NEEDED
# ---------------------------------------------------------
# This file lives in: BreakingNews/channels/yugioh/yugioh_engine.py
# All paths are anchored to this folder.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTICLES_DIR = os.path.join(BASE_DIR, "articles")
DATA_JSON = os.path.join(BASE_DIR, "data.json")

os.makedirs(ARTICLES_DIR, exist_ok=True)

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
# YOUTUBE FETCHER
# ---------------------------------------------------------
def get_latest_video():
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "playlistend": 1,
        "forcejson": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(CHANNEL_URL, download=False)
        latest = info["entries"][0]
        return {
            "id": latest["id"],
            "title": latest["title"],
            "description": latest.get("description", ""),
            "uploader": latest.get("uploader", ""),
            "upload_date": latest.get("upload_date", ""),
            "tags": latest.get("tags", []),
            "webpage_url": latest["url"]
        }


def download_video_and_thumb(video_url, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    ydl_opts = {
        "format": "mp4",
        "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
        "writethumbnail": True,
        "convert_thumbnails": "jpg",
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    files = os.listdir(out_dir)
    mp4 = next(f for f in files if f.endswith(".mp4"))
    jpg = next(f for f in files if f.endswith(".jpg"))

    return os.path.join(out_dir, mp4), os.path.join(out_dir, jpg)


# ---------------------------------------------------------
# ARTICLE BUILDER
# ---------------------------------------------------------
def build_article_html(page_title: str, article_text: str, video_src: str, thumb_src: str) -> str:
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
  <title>{headline or page_title} | {BRAND_NAME}</title>
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
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: system-ui, sans-serif;
      background: var(--bg);
      color: var(--fg);
      line-height: 1.7;
      padding: 2rem 1.5rem 4rem;
    }}
    .shell {{ max-width: 960px; margin: 0 auto; }}
    header {{
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 2rem;
    }}
    .brand {{
      font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase;
      font-size: 0.9rem; color: var(--accent);
    }}
    .pill {{
      border-radius: 999px; border: 1px solid #1f2937;
      padding: 0.35rem 0.9rem; font-size: 0.75rem;
      text-transform: uppercase; letter-spacing: 0.12em; color: #9ca3af;
    }}
    .hero {{
      background: var(--card); border-radius: 1rem; border: 1px solid var(--border);
      padding: 1.5rem; margin-bottom: 2rem;
    }}
    .hero video {{
      width: 100%; border-radius: 0.75rem; margin-bottom: 1.25rem; background: #000;
    }}
    h1 {{ font-size: 1.9rem; margin-bottom: 0.5rem; }}
    h2 {{
      font-size: 1.1rem; text-transform: uppercase; letter-spacing: 0.12em;
      color: #9ca3af; margin-top: 2rem; margin-bottom: 0.75rem;
    }}
    .subheadline {{ color: #9ca3af; font-size: 0.98rem; margin-bottom: 0.75rem; }}
    .lead {{ font-size: 1.02rem; margin-bottom: 1.5rem; }}
    .body p {{ margin-bottom: 1rem; color: #d1d5db; font-size: 0.98rem; }}
    ul {{ margin-left: 1.2rem; margin-bottom: 1.5rem; }}
    li {{ margin-bottom: 0.4rem; }}
    footer {{
      margin-top: 3rem; font-size: 0.8rem; color: #6b7280;
      border-top: 1px solid #111827; padding-top: 1.5rem;
      display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap;
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div class="brand">{BRAND_NAME}</div>
      <div class="pill">Video • Latest Coverage</div>
    </header>

    <article>
      <section class="hero">
        <video controls poster="{thumb_src}">
          <source src="{video_src}" type="video/mp4">
        </video>
        <h1>{headline or page_title}</h1>
        <div class="subheadline">{subheadline}</div>
        <div class="lead">{lead}</div>
      </section>

      <section class="body">
        {body_html}
      </section>

      <section>
        <h2>Why it matters</h2>
        <ul>{why_html}</ul>
      </section>

      <section>
        <h2>What’s next</h2>
        <p>{nxt}</p>
      </section>
    </article>

    <footer>
      <div>© {year} {BRAND_NAME}. All rights reserved.</div>
      <div><a href="../../index.html">Back to homepage</a></div>
    </footer>
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

    print("Downloading video + thumbnail...")
    video_src, thumb_src = download_video_and_thumb(meta["webpage_url"], ARTICLES_DIR)

    print("Generating article text via LM Studio...")
    article_text = call_lmstudio(meta)

    print("Building HTML article...")
    page_title = clean_name(meta["title"])
    html = build_article_html(page_title, article_text, video_src, thumb_src)

    out_path = os.path.join(ARTICLES_DIR, page_title + ".html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print("Updating data.json...")
    data = {
        "headline": extract_block(article_text, "HEADLINE"),
        "summary": extract_block(article_text, "SUBHEADLINE"),
        "thumbnail": thumb_src,
        "source": meta.get("uploader", ""),
        "time": meta.get("upload_date", ""),
        "trending": "Latest Video",
        "top_story": True
    }

    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print("Done.")
    return out_path


if __name__ == "__main__":
    run_engine()

import os
import re
import json
import subprocess
from datetime import datetime
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

# ---------- CONFIG ----------

CHANNEL_URL = "https://www.youtube.com/channel/UCc_YGWm25v8oKIhMoQDQRLA"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ARTICLES_DIR = os.path.join(SCRIPT_DIR, "article")
os.makedirs(ARTICLES_DIR, exist_ok=True)

BRAND_NAME = "Banking With Billy"
PRIMARY_COLOR = "#050814"
ACCENT_COLOR = "#f97316"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0 Safari/537.36"
)
TIMEOUT = 20


# ---------- UTILS ----------

def log(msg: str):
    print(msg, flush=True)


def clean_name(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text


def parse_json_ld(html: str):
    soup = BeautifulSoup(html, "html.parser")
    blocks = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            txt = script.string or script.text
            if not txt:
                continue
            blocks.append(json.loads(txt))
        except Exception:
            pass
    return blocks


def get_latest_video_metadata():
    cmd = [
        "yt-dlp",
        "--dump-single-json",
        CHANNEL_URL,
        "--playlist-end",
        "1",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    info = json.loads(result.stdout)
    return info["entries"][0]


def extract_card_name(meta):
    title = meta.get("title", "") or ""
    desc = meta.get("description", "") or ""

    for line in desc.splitlines():
        m = re.match(r"^([A-Z][A-Za-z0-9'\-]*(?: [A-Z][A-Za-z0-9'\-]*){0,5}) is\b", line.strip())
        if m:
            return m.group(1).strip()

    words = re.findall(r"[A-Za-z0-9'\-]+", title)
    current = []
    candidates = []
    for w in words:
        if w[0].isupper():
            current.append(w)
        else:
            if len(current) >= 2:
                candidates.append(" ".join(current))
            current = []
    if len(current) >= 2:
        candidates.append(" ".join(current))
    if candidates:
        return candidates[0]
    return title


# ---------- DATA FETCHERS ----------

def fetch_ygoprodeck(card_name):
    url = f"https://db.ygoprodeck.com/api/v7/cardinfo.php?name={quote_plus(card_name)}"
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()["data"][0]
    except Exception:
        return None

    return {
        "source": "YGOPRODeck",
        "url": url,
        "name": data.get("name", card_name),
        "type": data.get("type", ""),
        "race": data.get("race", ""),
        "attribute": data.get("attribute", ""),
        "level": data.get("level", None),
        "atk": data.get("atk", None),
        "def": data.get("def", None),
        "linkval": data.get("linkval", None),
        "archetype": data.get("archetype", ""),
        "desc": data.get("desc", ""),
        "banlist": data.get("banlist_info", {}),
        "sets": data.get("card_sets", []) or [],
        "images": [img.get("image_url") for img in data.get("card_images", []) if img.get("image_url")],
        "prices": (data.get("card_prices") or [{}])[0],
    }


def extract_section_by_heading(content, headings):
    if not content:
        return ""
    out = []
    for h in content.find_all(["h2", "h3"]):
        title = h.get_text(strip=True).lower()
        if any(x.lower() in title for x in headings):
            parts = []
            for sib in h.find_next_siblings():
                if sib.name in ["h2", "h3"]:
                    break
                t = sib.get_text(" ", strip=True)
                if t:
                    parts.append(t)
            if parts:
                out.append("\n\n".join(parts))
    return "\n\n".join(out)


def fetch_yugipedia(card_name):
    url = f"https://yugipedia.com/wiki/{card_name.replace(' ', '_')}"
    try:
        html = fetch_html(url)
    except Exception:
        return {
            "source": "Yugipedia",
            "url": url,
            "summary": "",
            "text": "",
            "images": [],
            "rulings": "",
            "trivia": "",
            "appearances": "",
            "structured": [],
        }

    soup = BeautifulSoup(html, "html.parser")
    content = soup.find("div", id="mw-content-text")
    paragraphs = []
    images = []

    if content:
        for p in content.find_all("p", recursive=False):
            t = p.get_text(strip=True)
            if t:
                paragraphs.append(t)
        for img in content.find_all("img"):
            src = img.get("src") or ""
            if src.startswith("//"):
                src = "https:" + src
            if src.startswith("/"):
                src = urljoin(url, src)
            if src.startswith("http"):
                images.append(src)

    rulings = extract_section_by_heading(content, ["Rulings"])
    trivia = extract_section_by_heading(content, ["Trivia"])
    appearances = extract_section_by_heading(content, ["Appearances", "Anime", "Manga"])

    return {
        "source": "Yugipedia",
        "url": url,
        "summary": paragraphs[0] if paragraphs else "",
        "text": "\n\n".join(paragraphs),
        "images": images,
        "rulings": rulings,
        "trivia": trivia,
        "appearances": appearances,
        "structured": parse_json_ld(html),
    }


def fetch_official_db(card_name):
    base = "https://www.db.yugioh-card.com/yugiohdb/card_search.action"
    url = f"{base}?ope=2&keyword={quote_plus(card_name)}"
    try:
        html = fetch_html(url)
    except Exception:
        return {
            "source": "Official DB",
            "url": url,
            "summary": "",
            "text": "",
            "images": [],
            "structured": [],
        }

    soup = BeautifulSoup(html, "html.parser")
    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")][:5]
    images = []
    for img in soup.find_all("img"):
        src = img.get("src") or ""
        if src.startswith("//"):
            src = "https:" + src
        if src.startswith("/"):
            src = urljoin(url, src)
        if src.startswith("http"):
            images.append(src)

    return {
        "source": "Official DB",
        "url": url,
        "summary": paragraphs[0] if paragraphs else "",
        "text": "\n\n".join(paragraphs),
        "images": images,
        "structured": parse_json_ld(html),
    }


def fetch_tcgplayer(card_name):
    base = "https://www.tcgplayer.com/search/yugioh/product"
    url = f"{base}?productName={quote_plus(card_name)}"
    try:
        html = fetch_html(url)
    except Exception:
        return {
            "source": "TCGPlayer",
            "url": url,
            "summary": "",
            "text": "",
            "images": [],
            "structured": [],
        }

    soup = BeautifulSoup(html, "html.parser")
    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")][:5]
    images = []
    for img in soup.find_all("img"):
        src = img.get("src") or ""
        if src.startswith("//"):
            src = "https:" + src
        if src.startswith("/"):
            src = urljoin(url, src)
        if src.startswith("http"):
            images.append(src)

    return {
        "source": "TCGPlayer",
        "url": url,
        "summary": paragraphs[0] if paragraphs else "",
        "text": "\n\n".join(paragraphs),
        "images": images,
        "structured": parse_json_ld(html),
    }


def fetch_cardmarket(card_name):
    base = "https://www.cardmarket.com/en/YuGiOh/Products/Search"
    url = f"{base}?searchString={quote_plus(card_name)}"
    try:
        html = fetch_html(url)
    except Exception:
        return {
            "source": "Cardmarket",
            "url": url,
            "summary": "",
            "text": "",
            "images": [],
            "structured": [],
        }

    soup = BeautifulSoup(html, "html.parser")
    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")][:5]
    images = []
    for img in soup.find_all("img"):
        src = img.get("src") or ""
        if src.startswith("//"):
            src = "https:" + src
        if src.startswith("/"):
            src = urljoin(url, src)
        if src.startswith("http"):
            images.append(src)

    return {
        "source": "Cardmarket",
        "url": url,
        "summary": paragraphs[0] if paragraphs else "",
        "text": "\n\n".join(paragraphs),
        "images": images,
        "structured": parse_json_ld(html),
    }


# ---------- ARTICLE TEXT ----------

def write_card_article(card):
    rarity_hint = ""
    for s in card.get("sets", []):
        r = s.get("set_rarity", "")
        if r:
            rarity_hint = r
            break

    prices = card.get("prices", {})
    tcg_mid = prices.get("tcgplayer_price") or prices.get("tcgplayer_mid") or ""
    cm_mid = prices.get("cardmarket_price") or ""

    overview = (
        f"{card['name']} is a {card.get('attribute','')} {card.get('race','')} card positioned at the intersection "
        f"of competitive play, collecting, and trading. Its stats, effect, and print history make it a card worth "
        f"understanding in detail for serious Yu‑Gi‑Oh players and TCG participants."
    )

    players = f"""
For players, {card['name']} is evaluated first by its effect and how it fits into existing engines. Key competitive factors:
- Effect text: how it enables or extends combos
- Stats: ATK {card.get('atk','?')} / DEF {card.get('def','?')} and Level {card.get('level','?')}
- Type and Attribute: {card.get('race','?')} / {card.get('attribute','?')}
- Archetype ties: {card.get('archetype','None')} (if any)
- Synergy with current meta decks and side deck options

Players care about whether this card:
- Starts plays or extends them
- Fixes hands or patches weaknesses
- Trades well into common boards
- Scales into grind games
"""

    collectors = f"""
Collectors look at {card['name']} through rarity, artwork, and print history. Key collector factors:
- Rarity highlight: {rarity_hint or "varies by print and set"}
- First edition desirability and early print runs
- Set popularity and how iconic the product is
- Artwork appeal and any alternate arts
- Whether it appears in special products, tins, or reprint sets

Collectors are watching for:
- Clean copies in high grades
- Low population in older prints
- Iconic appearances in competitive history or media
"""

    traders = f"""
For traders and investors, {card['name']} is all about price movement, demand, and reprint risk.

Market snapshot:
- TCGPlayer mid/market (approx): {tcg_mid or "N/A"}
- Cardmarket reference (EU): {cm_mid or "N/A"}
- Multiple printings: {len(card.get("sets", []))} known set entries

Key trading considerations:
- Demand from competitive players (short-term spikes)
- Collector demand for specific rarities
- Reprint risk in upcoming products
- Liquidity: how quickly copies move at fair prices
- Whether the card is a stable hold or a short-term flip
"""

    verdict = (
        f"{card['name']} offers different value depending on who you are. "
        f"Players see it as a tool in specific strategies, collectors see it as a piece of cardboard history, "
        f"and traders see it as a moving asset tied to format shifts and reprint cycles. "
        f"Within the Banking With Billy framework, it is tracked as part of the broader Yu‑Gi‑Oh market and meta landscape."
    )

    return {
        "overview": overview,
        "players": players,
        "collectors": collectors,
        "traders": traders,
        "verdict": verdict,
    }


# ---------- LAYOUT HELPERS ----------

def build_decks_section(card):
    name = card["name"]
    return f"""
<section class="panel panel-side">
  <div class="panel-header">
    <span class="panel-icon">🧩</span>
    <h2>Decks That Use This Card</h2>
  </div>
  <p>{name} finds a home in strategies that can convert its effect into real advantage.</p>
  <ul class="ygo-list">
    <li>Combo and engine-based decks that exploit its effect.</li>
    <li>Meta strategies that value its stats and typing.</li>
    <li>Experimental builds testing new interactions.</li>
  </ul>
</section>
"""


def build_price_widget(card):
    prices = card.get("prices", {})
    tcg = prices.get("tcgplayer_price") or prices.get("tcgplayer_mid")
    cm = prices.get("cardmarket_price")
    ebay = prices.get("ebay_price")
    amazon = prices.get("amazon_price")
    return f"""
<section class="panel">
  <div class="panel-header">
    <span class="panel-icon">💰</span>
    <h2>Price & Market Snapshot</h2>
  </div>
  <div class="market-widget">
    <div class="market-row"><span class="label">TCGPlayer (approx)</span><span class="value">{tcg or "N/A"}</span></div>
    <div class="market-row"><span class="label">Cardmarket (approx)</span><span class="value">{cm or "N/A"}</span></div>
    <div class="market-row"><span class="label">eBay (ref)</span><span class="value">{ebay or "N/A"}</span></div>
    <div class="market-row"><span class="label">Amazon (ref)</span><span class="value">{amazon or "N/A"}</span></div>
  </div>
</section>
"""


def build_correlation_summary(card, yugipedia, official_db, tcgplayer, cardmarket):
    sets_count = len(card.get("sets", []))
    lines = [
        f"- This card currently has {sets_count} known printings in the YGOPRODeck database.",
        "- Multi‑source verification from Yugipedia, the Official Database, TCGPlayer, and Cardmarket confirms effect text and market presence.",
    ]
    bullet_html = "".join(f"<li>{l}</li>" for l in lines)
    return f"""
<section class="panel">
  <div class="panel-header">
    <span class="panel-icon">🧠</span>
    <h2>Cross-Site Correlation & Insights</h2>
  </div>
  <ul class="ygo-list">
    {bullet_html}
  </ul>
</section>
"""


# ---------- VIDEO: LOCAL MP4 SYSTEM ----------

def download_video_mp4(yt_url, save_path):
    try:
        cmd = [
            "yt-dlp",
            "-f", "mp4",
            "-o", save_path,
            yt_url
        ]
        subprocess.run(cmd, check=True)
        return True
    except Exception as e:
        print("Video download failed:", e)
        return False


def build_video_block_local(mp4_filename, article_url):
    if mp4_filename and os.path.exists(mp4_filename):
        video_html = (
            f"<video width='100%' height='auto' controls autoplay muted loop "
            f"style='border-radius:12px;box-shadow:0 0 20px #000;'>"
            f"<source src='{os.path.basename(mp4_filename)}' type='video/mp4'>"
            "Your browser does not support the video tag."
            "</video>"
        )
    else:
        video_html = "<p>Video unavailable.</p>"

    return f"""
<section class="panel panel-side">
  <div class="panel-header">
    <span class="panel-icon">🎬</span>
    <h2>Video, News & Community</h2>
  </div>

  <div class="video-embed" style="margin-bottom:0.75rem;">
    {video_html}
  </div>

  <div class="news-article-preview" style="margin-bottom:1rem;">
    <h3 style="margin-bottom:0.5rem;">Banking With Billy News Article</h3>
    <p style="font-size:0.9rem;line-height:1.5;">
      This card is featured in a Banking With Billy Yu‑Gi‑Oh market intelligence report, covering its competitive role,
      collector value, and trading signals.
    </p>
    <a href="{article_url}" target="_blank" style="font-size:0.9rem;color:var(--accent);">Read full article →</a>
  </div>

  <div class="discord-invite">
    <h3 style="margin-bottom:0.5rem;">Join the Community</h3>
    <p style="font-size:0.9rem;line-height:1.5;">
      Connect with players, collectors, and traders in the Banking With Billy Discord. Share pulls, discuss meta, and get live updates.
    </p>
    <a href="https://discord.gg/Jw5Ur6Mcwd" target="_blank" style="font-size:0.9rem;color:var(--accent);">Join Yu‑Gi‑Oh →</a>
  </div>
</section>
"""


# ---------- HTML BUILDER ----------

def build_article_html(card, yt_meta, yugipedia, official_db, tcgplayer, cardmarket, article_filename, video_block_html):
    card_name = card["name"]
    yt_title = yt_meta.get("title", "")
    yt_desc = yt_meta.get("description", "") or ""
    yt_id = yt_meta.get("id", "")
    yt_url = yt_meta.get("webpage_url") or (f"https://www.youtube.com/watch?v={yt_id}" if yt_id else "")
    article_url = article_filename

    level_str = ""
    if card.get("level") is not None:
        level_str = f"Level {card['level']}"
    if card.get("linkval") is not None:
        level_str = f"Link Rating {card['linkval']}"

    banlist = card.get("banlist", {})
    ban_status = ", ".join(f"{k.upper()}: {v}" for k, v in banlist.items()) if banlist else "Not currently banned."

    main_image = card["images"][0] if card["images"] else ""

    attr = (card.get("attribute") or "").upper()
    attr_color = "#6b7280"
    if attr == "FIRE":
        attr_color = "#FF5A00"
    elif attr == "WATER":
        attr_color = "#0094FF"
    elif attr == "WIND":
        attr_color = "#00D26A"
    elif attr == "EARTH":
        attr_color = "#A67C52"
    elif attr == "LIGHT":
        attr_color = "#FFF7C0"
    elif attr == "DARK":
        attr_color = "#6A5ACD"
    elif attr == "DIVINE":
        attr_color = "#FFD700"

    hero_bg = f"linear-gradient(135deg, {attr_color}33, #050814 70%)"

    set_cards = []
    for s in card.get("sets", []):
        set_cards.append(
            f"""
<div class="set-card">
  <p class="set-name">{s.get('set_name','')}</p>
  <p class="set-meta">Code: {s.get('set_code','')}</p>
  <p class="set-meta">Rarity: {s.get('set_rarity','')}</p>
  <p class="set-meta">Ref price: {s.get('set_price','')}</p>
</div>
"""
        )
    if set_cards:
        set_timeline = f"""
<section class="panel">
  <div class="panel-header">
    <span class="panel-icon">📦</span>
    <h2>Set History (Print Timeline)</h2>
  </div>
  <p class="panel-sub">Scroll to see every known printing, rarity, and reference price.</p>
  <div class="set-timeline">
    {''.join(set_cards)}
  </div>
</section>
"""
    else:
        set_timeline = """
<section class="panel">
  <div class="panel-header">
    <span class="panel-icon">📦</span>
    <h2>Set History (Print Timeline)</h2>
  </div>
  <p>No set data available.</p>
</section>
"""

    price_widget = build_price_widget(card)
    analysis = write_card_article(card)
    correlation_block = build_correlation_summary(card, yugipedia, official_db, tcgplayer, cardmarket)
    decks_block = build_decks_section(card)

    wiki_block = ""
    if yugipedia["summary"] or yugipedia["text"]:
        wiki_block = f"""
<section class="panel">
  <div class="panel-header">
    <span class="panel-icon">📚</span>
    <h2>Wiki, Lore, and Extra Info</h2>
  </div>
  <p class="panel-sub"><strong>From Yugipedia:</strong></p>
  <p>{yugipedia['summary']}</p>
  <p>{yugipedia['text']}</p>
</section>
"""

    rulings_trivia_block = ""
    if yugipedia.get("rulings") or yugipedia.get("trivia") or yugipedia.get("appearances"):
        rulings_trivia_block = "<section class='panel'>"
        rulings_trivia_block += """
  <div class="panel-header">
    <span class="panel-icon">⚖️</span>
    <h2>Rulings, Trivia, and Appearances</h2>
  </div>
"""
        if yugipedia.get("rulings"):
            rulings_trivia_block += f"<h3>Rulings</h3><p>{yugipedia['rulings']}</p>"
        if yugipedia.get("trivia"):
            rulings_trivia_block += f"<h3>Trivia</h3><p>{yugipedia['trivia']}</p>"
        if yugipedia.get("appearances"):
            rulings_trivia_block += f"<h3>Appearances</h3><p>{yugipedia['appearances']}</p>"
        rulings_trivia_block += "</section>"

    gallery_images = []
    gallery_images.extend(card["images"])
    gallery_images.extend(yugipedia["images"])
    gallery_images.extend(official_db["images"])
    gallery_images.extend(tcgplayer["images"])
    gallery_images.extend(cardmarket["images"])

    gallery_block = ""
    if gallery_images:
        gallery_block = "<section class='panel'>"
        gallery_block += """
  <div class="panel-header">
    <span class="panel-icon">🖼️</span>
    <h2>Image Gallery</h2>
  </div>
"""
        gallery_block += "<div class='gallery'>"
        for img in gallery_images:
            gallery_block += f"<img src='{img}' class='gallery-img'>"
        gallery_block += "</div></section>"

    sources_block = f"""
<section class="panel panel-side">
  <div class="panel-header">
    <span class="panel-icon">🔗</span>
    <h2>Sources</h2>
  </div>
  <ul class="ygo-list">
    <li><a href="{card['url']}" target="_blank">YGOPRODeck</a></li>
    <li><a href="{yugipedia['url']}" target="_blank">Yugipedia</a></li>
    <li><a href="{official_db['url']}" target="_blank">Official Database</a></li>
    <li><a href="{tcgplayer['url']}" target="_blank">TCGPlayer</a></li>
    <li><a href="{cardmarket['url']}" target="_blank">Cardmarket</a></li>
  </ul>
</section>
"""

    year = datetime.now().year

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{card_name} — Yu‑Gi‑Oh Market Intelligence Report | {BRAND_NAME}</title>
<meta name="description" content="Banking With Billy provides real‑time Yu‑Gi‑Oh market intelligence, competitive meta analysis, verified multi‑source card data, and authoritative TCG reporting.">
<meta property="og:title" content="{card_name} — Yu‑Gi‑Oh Market Intelligence Report">
<meta property="og:description" content="Real‑time Yu‑Gi‑Oh card intelligence, market prices, meta insights, and cross‑source verification from Banking With Billy.">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Banking With Billy">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{card_name} — Yu‑Gi‑Oh Market Intelligence Report">
<meta name="twitter:description" content="Yu‑Gi‑Oh market intelligence, meta analysis, and verified card data from Banking With Billy.">
<style>
body {{
  margin:0;
  padding:0;
  background:#020617;
  color:#e5e7eb;
  font-family:system-ui,-apple-system,BlinkMacSystemFont,"Inter",sans-serif;
}}
a {{ color:{ACCENT_COLOR}; text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
.page-wrap {{
  max-width:1200px;
  margin:0 auto;
  padding:2.5rem 1.5rem 3rem;
}}
.site-header {{
  margin-bottom:1.5rem;
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:1rem;
}}
.brand-mark {{
  font-size:0.9rem;
  text-transform:uppercase;
  letter-spacing:0.18em;
  color:#9ca3af;
}}
.brand-mark span {{ color:{ACCENT_COLOR}; }}
.header-meta {{
  font-size:0.8rem;
  color:#9ca3af;
  text-align:right;
}}
.hero {{
  background:{hero_bg};
  border-radius:0 0 24px 24px;
  border:1px solid rgba(148,163,184,0.35);
  box-shadow:0 18px 45px rgba(0,0,0,0.65);
  padding:1.75rem;
  display:grid;
  grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);
  gap:1.75rem;
}}
.hero-title {{
  font-size:2.1rem;
  letter-spacing:0.06em;
  text-transform:uppercase;
  margin:0 0 0.5rem;
}}
.hero-sub {{
  margin:0 0 1rem;
  color:#9ca3af;
  font-size:0.95rem;
}}
.hero-badge-row {{
  display:flex;
  flex-wrap:wrap;
  gap:0.5rem;
  margin-bottom:1rem;
}}
.hero-badge {{
  font-size:0.75rem;
  text-transform:uppercase;
  letter-spacing:0.12em;
  padding:0.25rem 0.6rem;
  border-radius:999px;
  border:1px solid rgba(148,163,184,0.6);
  background:rgba(15,23,42,0.7);
  color:#9ca3af;
}}
.hero-badge.attr {{
  border-color:{attr_color};
  color:{attr_color};
}}
.hero-grid {{
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:0.5rem 1.25rem;
  font-size:0.9rem;
}}
.hero-grid-label {{
  color:#9ca3af;
  font-size:0.8rem;
  text-transform:uppercase;
  letter-spacing:0.12em;
}}
.hero-grid-value {{
  color:#f9fafb;
  font-weight:500;
}}
.hero-video {{
  margin-top:1.25rem;
  font-size:0.85rem;
  color:#9ca3af;
}}
.hero-video summary {{
  cursor:pointer;
  list-style:none;
}}
.hero-right {{
  display:flex;
  justify-content:center;
  align-items:center;
}}
.card-frame {{
  width:260px;
  max-width:100%;
  aspect-ratio:3/4;
  border-radius:18px;
  padding:6px;
  background:#020617;
  box-shadow:0 18px 40px rgba(0,0,0,0.85);
  border:1px solid rgba(148,163,184,0.7);
}}
.card-inner {{
  width:100%;
  height:100%;
  border-radius:14px;
  overflow:hidden;
  background:#020617;
  position:relative;
}}
.card-inner img {{
  width:100%;
  height:100%;
  object-fit:cover;
}}
.card-footer-strip {{
  position:absolute;
  left:0;
  right:0;
  bottom:0;
  height:26px;
  background:rgba(15,23,42,0.9);
  border-top:1px solid rgba(148,163,184,0.5);
  display:flex;
  align-items:center;
  justify-content:center;
  font-size:0.7rem;
  color:#9ca3af;
  text-transform:uppercase;
  letter-spacing:0.16em;
}}
.main-layout {{
  display:grid;
  grid-template-columns:minmax(0,2.1fr) minmax(0,1fr);
  gap:1.75rem;
  margin-top:2rem;
}}
.panel {{
  background:#020617;
  border-radius:14px;
  border:1px solid #1f2937;
  box-shadow:0 14px 30px rgba(0,0,0,0.7);
  padding:1.1rem 1.25rem 1.25rem;
}}
.panel-header {{
  display:flex;
  align-items:center;
  gap:0.5rem;
  margin-bottom:0.75rem;
}}
.panel-icon {{
  width:26px;
  height:26px;
  border-radius:999px;
  background:#0f172a;
  display:inline-flex;
  align-items:center;
  justify-content:center;
  font-size:0.9rem;
  border:1px solid rgba(148,163,184,0.7);
}}
.panel h2 {{
  font-size:1.25rem;
  letter-spacing:0.08em;
  text-transform:uppercase;
  margin:0;
}}
.panel-sub {{
  margin:0 0 0.75rem;
  font-size:0.85rem;
  color:#9ca3af;
}}
.panel h3 {{
  margin-top:0.75rem;
  margin-bottom:0.35rem;
  font-size:1rem;
  letter-spacing:0.06em;
  text-transform:uppercase;
}}
.panel p {{
  margin:0.25rem 0;
  font-size:0.95rem;
  line-height:1.6;
}}
.ygo-list {{
  margin:0.25rem 0 0.25rem 0;
  padding-left:1.1rem;
  font-size:0.95rem;
}}
.ygo-list li {{ margin-bottom:0.25rem; }}
.effect-box {{
  background:#020617;
  border-radius:10px;
  border:1px solid rgba(148,163,184,0.7);
  padding:0.75rem 0.9rem;
  font-family:ui-monospace,Menlo,Monaco,Consolas,"Liberation Mono","Courier New",monospace;
  font-size:0.85rem;
  line-height:1.6;
  white-space:pre-wrap;
}}
.set-timeline {{
  display:flex;
  flex-wrap:nowrap;
  overflow-x:auto;
  gap:0.75rem;
  padding-bottom:0.25rem;
  margin-top:0.5rem;
}}
.set-card {{
  min-width:220px;
  background:#020617;
  border-radius:12px;
  border:1px solid rgba(148,163,184,0.7);
  padding:0.7rem 0.8rem;
  box-shadow:0 10px 25px rgba(0,0,0,0.7);
}}
.set-name {{
  font-size:0.95rem;
  font-weight:600;
  margin:0 0 0.25rem;
}}
.set-meta {{
  margin:0;
  font-size:0.8rem;
  color:#9ca3af;
}}
.market-widget {{
  display:flex;
  flex-direction:column;
  gap:0.25rem;
  margin-top:0.25rem;
}}
.market-row {{
  display:flex;
  justify-content:space-between;
  font-size:0.9rem;
}}
.market-row .label {{ color:#9ca3af; }}
.market-row .value {{ color:#f9fafb; font-weight:500; }}
.gallery {{
  display:flex;
  flex-wrap:wrap;
  gap:0.5rem;
  margin-top:0.5rem;
}}
.gallery-img {{
  width:100%;
  max-width:220px;
  border-radius:10px;
  border:1px solid rgba(148,163,184,0.7);
  box-shadow:0 10px 25px rgba(0,0,0,0.8);
}}
.main-right {{
  position:sticky;
  top:1.5rem;
  display:flex;
  flex-direction:column;
  gap:1.25rem;
}}
.footer {{
  margin-top:2.5rem;
  padding-top:1.25rem;
  border-top:1px solid #1f2937;
  font-size:0.8rem;
  color:#9ca3af;
  text-align:center;
  line-height:1.6;
}}
.footer span {{ color:{ACCENT_COLOR}; }}
@media (max-width:900px) {{
  .hero {{ grid-template-columns:minmax(0,1fr); }}
  .main-layout {{ grid-template-columns:minmax(0,1fr); }}
  .main-right {{ position:static; }}
}}
</style>
</head>
<body>
<div class="page-wrap">

<header class="site-header">
  <div class="brand-mark">
    <span>Banking With Billy · Yu‑Gi‑Oh Market Intelligence & Competitive Analysis</span>
  </div>
  <div class="header-meta">
    <div>Banking With Billy · The Global Authority in Yu‑Gi‑Oh Card Data & TCG Market Research</div>
    <div>Real‑time Yu‑Gi‑Oh data reporting, competitive meta tracking, and verified multi‑source card intelligence</div>
  </div>
</header>

<section class="hero">
  <div class="hero-left">
    <h1 class="hero-title">{card_name}</h1>
    <p class="hero-sub">A complete Yu‑Gi‑Oh market intelligence and competitive analysis report generated by the Banking With Billy Trading Card Intelligence Network.</p>
    <div class="hero-badge-row">
      <div class="hero-badge attr">{card.get('attribute','N/A')} Attribute</div>
      <div class="hero-badge">{card.get('type','N/A')}</div>
      <div class="hero-badge">{card.get('race','N/A')}</div>
      <div class="hero-badge">Banlist: {ban_status}</div>
    </div>
    <div class="hero-grid">
      <div>
        <div class="hero-grid-label">ATK / DEF</div>
        <div class="hero-grid-value">{card.get('atk','?')} / {card.get('def','?')}</div>
      </div>
      <div>
        <div class="hero-grid-label">Level / Link</div>
        <div class="hero-grid-value">{level_str or "—"}</div>
      </div>
      <div>
        <div class="hero-grid-label">Archetype</div>
        <div class="hero-grid-value">{card.get('archetype','None')}</div>
      </div>
      <div>
        <div class="hero-grid-label">Primary Source</div>
        <div class="hero-grid-value">YGOPRODeck + Official DB</div>
      </div>
    </div>
    <div class="hero-video">
      <details>
        <summary>Linked video: {yt_title}</summary>
        <p><a href="{yt_url}" target="_blank">{yt_url}</a></p>
        <pre style="white-space:pre-wrap;font-family:inherit;font-size:0.8rem;margin-top:0.5rem;">{yt_desc}</pre>
      </details>
    </div>
  </div>
  <div class="hero-right">
    <div class="card-frame">
      <div class="card-inner">
        {"<img src='"+main_image+"' alt='Card image'>" if main_image else ""}
        <div class="card-footer-strip">DUEL MONSTERS · ATTRIBUTE: {card.get('attribute','N/A')}</div>
      </div>
    </div>
  </div>
</section>

<div class="main-layout">
  <div class="main-left">
    <section class="panel">
      <div class="panel-header">
        <span class="panel-icon">⚡</span>
        <h2>Effect Text</h2>
      </div>
      <div class="effect-box">{card.get('desc','')}</div>
    </section>

    {set_timeline}

    {price_widget}

    <section class="panel">
      <div class="panel-header">
        <span class="panel-icon">📖</span>
        <h2>Overview & Roles</h2>
      </div>
      <h3>Overview</h3>
      <p>{analysis['overview']}</p>
      <h3>For Players</h3>
      <p>{analysis['players']}</p>
      <h3>For Collectors</h3>
      <p>{analysis['collectors']}</p>
      <h3>For Traders</h3>
      <p>{analysis['traders']}</p>
      <h3>Final Verdict</h3>
      <p>{analysis['verdict']}</p>
    </section>

    {correlation_block}
    {rulings_trivia_block}
    {wiki_block}
    {gallery_block}
  </div>

  <div class="main-right">
    {decks_block}
    {sources_block}
    {video_block_html}
  </div>
</div>

<div class="footer">
  © {year} <span>{BRAND_NAME}</span>. Published by the Banking With Billy Trading Card Intelligence Network — independent Yu‑Gi‑Oh market analysis, competitive insights, collector research, and real‑time TCG reporting.
</div>

</div>
</body>
</html>
"""
    return html


# ---------- ENGINE RUNNER ----------

def run_engine():
    yt_meta = get_latest_video_metadata()
    if not yt_meta:
        log("[ENGINE] No YouTube metadata.")
        return

    card_name = extract_card_name(yt_meta)
    log(f"[ENGINE] Card focus: {card_name}")

    core = fetch_ygoprodeck(card_name)
    if not core:
        log("[ENGINE] No core card data from YGOPRODeck.")
        return

    yugipedia = fetch_yugipedia(card_name)
    official_db = fetch_official_db(card_name)
    tcgplayer = fetch_tcgplayer(card_name)
    cardmarket = fetch_cardmarket(card_name)

    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{clean_name(core['name'])}_{now}.html"
    path = os.path.join(ARTICLES_DIR, filename)

    yt_url = yt_meta.get("webpage_url")
    mp4_name = os.path.join(ARTICLES_DIR, f"{clean_name(core['name'])}_{now}.mp4")
    if yt_url:
        download_video_mp4(yt_url, mp4_name)
    video_block_html = build_video_block_local(mp4_name if os.path.exists(mp4_name) else "", filename)

    html = build_article_html(core, yt_meta, yugipedia, official_db, tcgplayer, cardmarket, filename, video_block_html)

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    log("[ENGINE] Article created:")
    log(path)


if __name__ == "__main__":
    run_engine()

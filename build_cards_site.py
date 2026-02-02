import requests
import xml.etree.ElementTree as ET
from html import unescape
from datetime import datetime

# ============================
# CARD API HELPERS
# ============================

def fetch_latest_ygo_card():
    try:
        url = "https://db.ygoprodeck.com/api/v7/cardinfo.php?num=1&offset=0"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        card = data["data"][0]
        name = card.get("name", "Yu-Gi-Oh! Card")
        img = card.get("card_images", [{}])[0].get("image_url", "")
        link = f"https://db.ygoprodeck.com/card/?search={name.replace(' ', '+')}"
        return {
            "game": "Yu-Gi-Oh!",
            "name": name,
            "image": img,
            "link": link,
        }
    except Exception:
        return {
            "game": "Yu-Gi-Oh!",
            "name": "Yu-Gi-Oh! Card",
            "image": "",
            "link": "https://db.ygoprodeck.com/",
        }


def fetch_latest_pokemon_card():
    try:
        url = "https://api.pokemontcg.io/v2/cards?page=1&pageSize=1"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        card = data["data"][0]
        name = card.get("name", "Pokémon Card")
        images = card.get("images", {})
        img = images.get("large") or images.get("small") or ""
        link = f"https://pokemontcg.io/card/{card.get('id','')}"
        return {
            "game": "Pokémon",
            "name": name,
            "image": img,
            "link": link,
        }
    except Exception:
        return {
            "game": "Pokémon",
            "name": "Pokémon Card",
            "image": "",
            "link": "https://www.pokemon.com/",
        }


def fetch_latest_mtg_card():
    try:
        # random card, effectively "latest/varied" for display
        url = "https://api.scryfall.com/cards/random"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        card = r.json()
        name = card.get("name", "Magic: The Gathering Card")
        img = ""
        if "image_uris" in card:
            img = card["image_uris"].get("normal") or card["image_uris"].get("large") or ""
        elif "card_faces" in card and card["card_faces"]:
            face = card["card_faces"][0]
            img = face.get("image_uris", {}).get("normal", "")
        link = card.get("scryfall_uri", "https://scryfall.com/")
        return {
            "game": "Magic: The Gathering",
            "name": name,
            "image": img,
            "link": link,
        }
    except Exception:
        return {
            "game": "Magic: The Gathering",
            "name": "Magic: The Gathering Card",
            "image": "",
            "link": "https://scryfall.com/",
        }


# ============================
# RSS NEWS HELPERS
# ============================

def clean_text(text, max_len=220):
    if not text:
        return ""
    out = []
    inside = False
    for ch in text:
        if ch == "<":
            inside = True
        elif ch == ">":
            inside = False
        elif not inside:
            out.append(ch)
    s = " ".join("".join(out).split())
    s = unescape(s)
    if len(s) > max_len:
        s = s[:max_len].rsplit(" ", 1)[0] + "…"
    return s


def fetch_rss_items(url, limit=5):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        items = []
        for item in root.findall(".//item")[:limit]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = (item.findtext("description") or "").strip()
            items.append({
                "title": unescape(title),
                "link": link,
                "summary": clean_text(desc),
            })
        return items
    except Exception:
        return []


# ============================
# HTML TEMPLATE
# ============================

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Banking With Billy Cards – Live TCG Engine</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body { background:#050509; color:#f9fafb; font-family:system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin:0; }
a { color:#f97316; text-decoration:none; }
a:hover { text-decoration:underline; }
.header { padding:20px; background:linear-gradient(90deg,#020617,#111827); border-bottom:1px solid #1f2937; }
.header-title { font-size:24px; font-weight:700; }
.header-sub { font-size:13px; color:#9ca3af; margin-top:4px; }
.page { max-width:1200px; margin:0 auto; padding:20px; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:20px; }
.card-block { background:#020617; border:1px solid #1f2937; border-radius:16px; padding:16px; box-shadow:0 10px 30px rgba(0,0,0,0.4); }
.card-game { font-size:13px; text-transform:uppercase; letter-spacing:0.08em; color:#a855f7; margin-bottom:6px; }
.card-name { font-size:18px; font-weight:600; margin-bottom:10px; }
.card-img-wrap { text-align:center; margin-bottom:12px; }
.card-img-wrap img { max-width:100%; border-radius:12px; box-shadow:0 12px 40px rgba(0,0,0,0.7); }
.card-link { font-size:13px; color:#f97316; margin-bottom:12px; display:block; }
.news-title { font-size:13px; font-weight:600; color:#e5e7eb; margin-bottom:8px; text-transform:uppercase; letter-spacing:0.08em; }
.news-item { margin-bottom:10px; }
.news-item a { font-size:14px; font-weight:500; color:#e5e7eb; }
.news-summary { font-size:12px; color:#9ca3af; margin-top:2px; }
.footer { padding:16px; font-size:11px; color:#6b7280; text-align:center; border-top:1px solid #111827; margin-top:20px; }
@media (max-width:640px){
  .header-title { font-size:20px; }
}
</style>
</head>
<body>

<div class="header">
  <div class="header-title">Banking With Billy Cards – Live TCG Feed</div>
  <div class="header-sub">Auto-updating card images and news for Yu-Gi-Oh!, Pokémon, and Magic: The Gathering.</div>
</div>

<div class="page">
  <div class="grid">
    {CARD_BLOCKS}
  </div>
</div>

<div class="footer">
  Last updated: {LAST_UPDATED} · Banking With Billy Cards – Live Trading Card Engine
</div>

</body>
</html>
"""


# ============================
# BLOCK BUILDERS
# ============================

def build_news_list(items):
    if not items:
        return '<div class="news-item"><span class="news-summary">No recent headlines available.</span></div>'
    parts = []
    for it in items:
        parts.append(f"""
      <div class="news-item">
        <a href="{it['link']}" target="_blank" rel="noopener noreferrer">{it['title']}</a>
        <div class="news-summary">{it['summary']}</div>
      </div>
    """)
    return "\n".join(parts)


def build_card_block(card, news_items):
    img_html = ""
    if card["image"]:
        img_html = f'<img src="{card["image"]}" alt="{card["name"]}">'
    else:
        img_html = '<div style="width:100%;height:220px;border-radius:12px;background:#111827;display:flex;align-items:center;justify-content:center;font-size:12px;color:#6b7280;">No image available</div>'

    news_html = build_news_list(news_items)

    return f"""
  <div class="card-block">
    <div class="card-game">{card['game']}</div>
    <div class="card-name">{card['name']}</div>
    <div class="card-img-wrap">
      <a href="{card['link']}" target="_blank" rel="noopener noreferrer">
        {img_html}
      </a>
    </div>
    <a class="card-link" href="{card['link']}" target="_blank" rel="noopener noreferrer">
      View full card details →
    </a>
    <div class="news-title">Latest {card['game']} headlines</div>
    {news_html}
  </div>
"""


# ============================
# MAIN BUILD
# ============================

def main():
    # Fetch latest cards
    ygo_card = fetch_latest_ygo_card()
    pokemon_card = fetch_latest_pokemon_card()
    mtg_card = fetch_latest_mtg_card()

    # Fetch news per game
    ygo_news = fetch_rss_items("https://ygorganization.com/feed/", limit=5)
    pokemon_news = fetch_rss_items("https://www.pokebeach.com/feed", limit=5)
    mtg_news = fetch_rss_items("https://www.mtggoldfish.com/articles.rss", limit=5)

    # Build blocks
    blocks = []
    blocks.append(build_card_block(ygo_card, ygo_news))
    blocks.append(build_card_block(pokemon_card, pokemon_news))
    blocks.append(build_card_block(mtg_card, mtg_news))

    html = HTML_TEMPLATE.replace("{CARD_BLOCKS}", "\n".join(blocks))
    html = html.replace("{LAST_UPDATED}", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    main()

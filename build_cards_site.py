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
        return {"game": "Yu-Gi-Oh!", "name": name, "image": img, "link": link}
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
        return {"game": "Pokémon", "name": name, "image": img, "link": link}
    except Exception:
        return {
            "game": "Pokémon",
            "name": "Pokémon Card",
            "image": "",
            "link": "https://www.pokemon.com/",
        }


def fetch_latest_mtg_card():
    try:
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
        return {"game": "Magic: The Gathering", "name": name, "image": img, "link": link}
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
            items.append(
                {
                    "title": unescape(title),
                    "link": link,
                    "summary": clean_text(desc),
                }
            )
        return items
    except Exception:
        return []


# ============================
# HTML BLOCK BUILDERS
# ============================

def build_news_list(items):
    if not items:
        return '<div class="news-item"><div class="news-item-summary">No recent headlines available.</div></div>'
    parts = []
    for it in items:
        parts.append(
            f"""
<div class="news-item">
  <div class="news-item-title"><a href="{it['link']}" target="_blank" rel="noopener noreferrer">{it['title']}</a></div>
  <div class="news-item-summary">{it['summary']}</div>
</div>
""".strip()
        )
    return "\n".join(parts)


def build_card_block(card, news_items):
    img_html = ""
    if card["image"]:
        img_html = f'<img class="live-card-img" src="{card["image"]}" alt="{card["name"]}">'
    else:
        img_html = '<div style="width:260px;height:360px;border-radius:12px;background:#111827;display:flex;align-items:center;justify-content:center;font-size:12px;color:#6b7280;margin-bottom:16px;">No image available</div>'

    news_html = build_news_list(news_items)

    return f"""
<div class="live-card-block">
  <div class="live-card-title">Latest {card['game']} Card</div>
  <a href="{card['link']}" target="_blank" rel="noopener noreferrer">
    {img_html}
  </a>
  {news_html}
</div>
""".strip()


def build_live_section(ygo_card, ygo_news, pokemon_card, pokemon_news, mtg_card, mtg_news):
    return f"""
<!-- AUTO-INSERTED LIVE TCG BLOCKS -->
<style>
.live-blocks-wrapper {{
  max-width: 1200px;
  margin: 40px auto;
  padding: 20px;
  border-top: 1px solid #1f2937;
}}
.live-blocks-title {{
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 16px;
}}
.live-blocks-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 20px;
}}
.live-card-block {{
  background: #111827;
  border-radius: 16px;
  border: 1px solid #1f2937;
  padding: 16px;
}}
.live-card-title {{
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
}}
.live-card-img {{
  width: 100%;
  max-width: 260px;
  border-radius: 12px;
  display: block;
  margin-bottom: 12px;
  box-shadow: 0 12px 40px rgba(0,0,0,0.6);
}}
.news-item-title a {{
  color: #f9fafb;
  text-decoration: none;
}}
.news-item-title a:hover {{
  text-decoration: underline;
}}
.news-item-summary {{
  font-size: 13px;
  color: #9ca3af;
}}
.live-updated-tag {{
  font-size: 11px;
  color: #9ca3af;
  margin-top: 8px;
}}
</style>

<div class="live-blocks-wrapper">
  <div class="live-blocks-title">Live TCG Cards & Headlines</div>
  <div class="live-updated-tag">Auto-updated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}</div>
  <div class="live-blocks-grid">
    {build_card_block(ygo_card, ygo_news)}
    {build_card_block(pokemon_card, pokemon_news)}
    {build_card_block(mtg_card, mtg_news)}
  </div>
</div>
""".strip()


# ============================
# MAIN BUILD
# ============================

def main():
    # 1. Read your existing homepage (unchanged layout)
    with open("index.html", "r", encoding="utf-8") as f:
        original_html = f.read()

    # 2. Fetch live cards
    ygo_card = fetch_latest_ygo_card()
    pokemon_card = fetch_latest_pokemon_card()
    mtg_card = fetch_latest_mtg_card()

    # 3. Fetch live news
    ygo_news = fetch_rss_items("https://ygorganization.com/feed/", limit=5)
    pokemon_news = fetch_rss_items("https://www.pokebeach.com/feed", limit=5)
    mtg_news = fetch_rss_items("https://www.mtggoldfish.com/articles.rss", limit=5)

    # 4. Build the live section
    live_section = build_live_section(
        ygo_card, ygo_news,
        pokemon_card, pokemon_news,
        mtg_card, mtg_news
    )

    # 5. Inject before </body> if present, else append
    lower = original_html.lower()
    if "</body>" in lower:
        idx = lower.rfind("</body>")
        new_html = original_html[:idx] + "\n" + live_section + "\n" + original_html[idx:]
    else:
        new_html = original_html + "\n" + live_section + "\n"

    # 6. Write back to index.html
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(new_html)


if __name__ == "__main__":
    main()

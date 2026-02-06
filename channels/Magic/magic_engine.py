import os
import re
import json
import urllib.parse
import subprocess
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
CHANNEL_ID = "UCJrZVI-xv4O0J8QGu5GbkAw"
FEED_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"

BRAND_NAME = "Banking With Billy"
PRIMARY_COLOR = "#05030a"
ACCENT_COLOR = "#f39c12"
SECONDARY_COLOR = "#8e44ad"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ARTICLES_DIR = os.path.join(SCRIPT_DIR, "article_magic")
LOGS_DIR = os.path.join(SCRIPT_DIR, "article_magic_logs")

os.makedirs(ARTICLES_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0 Safari/537.36"
)
TIMEOUT = 20

SCRYFALL_NAMED_FUZZY = "https://api.scryfall.com/cards/named?fuzzy={name}"

MTG_DOMAINS = [
    "scryfall.com", "gatherer.wizards.com", "wizards.com", "mtggoldfish.com",
    "edhrec.com", "cardkingdom.com", "tcgplayer.com", "starcitygames.com",
    "mtgstocks.com", "cardmarket.com", "cardmarket.eu",
    "mtg.fandom.com", "coolstuffinc.com", "reddit.com",
    "quietspeculation.com", "mtgrocks.com", "mtgprice.com"
]

MTG_KEYWORDS = [
    "mtg", "magic the gathering", "commander", "edh", "deck", "card", "equipment",
    "instant", "sorcery", "creature", "artifact", "planeswalker", "combo",
    "wizards of the coast", "tcg", "trading card game"
]


# ---------------------------------------------------------
# UTILS
# ---------------------------------------------------------
def log(msg: str):
    print(msg, flush=True)


def clean_name(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()


def safe_get(d, key, default=""):
    if d is None:
        return default
    v = d.get(key)
    return v if v is not None else default


def fetch_html(url: str) -> str | None:
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        return r.text
    except Exception:
        return None


def download_video_mp4(video_url: str, article_dir: str, base_name: str) -> str | None:
    if not video_url:
        return None

    os.makedirs(article_dir, exist_ok=True)
    out_path = os.path.join(article_dir, f"{base_name}.mp4")

    try:
        subprocess.run(
            ["yt-dlp", "-f", "mp4", "-o", out_path, video_url],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return None

    return out_path if os.path.exists(out_path) else None


# ---------------------------------------------------------
# FEED: GET ONLY THE LATEST VIDEO
# ---------------------------------------------------------
def get_latest_video():
    r = requests.get(FEED_URL, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.text, "xml")
    entry = soup.find("entry")
    if entry is None:
        return None

    title_el = entry.find("title")
    link_el = entry.find("link")
    desc_el = entry.find("media:description")
    video_id_el = entry.find("yt:videoId")

    title = title_el.text if title_el else ""
    url = link_el.get("href") if link_el else ""
    desc = desc_el.text if desc_el else ""
    video_id = video_id_el.text if video_id_el else ""

    return {
        "title": title.strip(),
        "url": url.strip(),
        "description": desc.strip(),
        "video_id": video_id.strip(),
    }


# ---------------------------------------------------------
# EXTRACT CARD NAME FROM TITLE
# ---------------------------------------------------------
def extract_card_name(title: str) -> str:
    for sep in ["—", "-", "|"]:
        if sep in title:
            title = title.split(sep)[0]
            break
    return title.strip()


# ---------------------------------------------------------
# SCRYFALL CARD DATA
# ---------------------------------------------------------
def get_card_data(card_name: str):
    query = urllib.parse.quote_plus(card_name)
    url = SCRYFALL_NAMED_FUZZY.format(name=query)
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("object") == "error":
            return None
        return data
    except Exception:
        return None


# ---------------------------------------------------------
# GLOBAL SEARCH (BING/MSN) USING FULL TITLE
# ---------------------------------------------------------
def search_web(query: str):
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.bing.com/search?q={encoded}"
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception:
        return []

    results = []
    for item in soup.select("li.b_algo h2 a"):
        href = item.get("href")
        if href and href.startswith("http"):
            results.append(href)
    return results


# ---------------------------------------------------------
# MTG FILTER
# ---------------------------------------------------------
def filter_mtg_links(links):
    filtered = []
    for link in links:
        lower = link.lower()
        if any(domain in lower for domain in MTG_DOMAINS):
            filtered.append(link)
            continue
        if any(keyword in lower for keyword in MTG_KEYWORDS):
            filtered.append(link)
            continue
    seen = set()
    out = []
    for l in filtered:
        if l not in seen:
            seen.add(l)
            out.append(l)
    return out


# ---------------------------------------------------------
# MULTI-SOURCE URL BUILDERS
# ---------------------------------------------------------
def build_scryfall_url(card_data):
    if not card_data:
        return None
    return safe_get(card_data, "scryfall_uri", None)


def build_gatherer_url(card_name: str):
    if not card_name:
        return None
    q = urllib.parse.quote_plus(card_name)
    return f"https://gatherer.wizards.com/Pages/Search/Default.aspx?name=+[{q}]"


def build_edhrec_url(card_name: str):
    if not card_name:
        return None
    slug = card_name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return f"https://edhrec.com/card/{slug}"


def build_goldfish_url(card_name: str):
    if not card_name:
        return None
    q = urllib.parse.quote_plus(card_name)
    return f"https://www.mtggoldfish.com/q?query_string={q}"


def build_cardmarket_url(card_name: str):
    if not card_name:
        return None
    q = urllib.parse.quote_plus(card_name)
    return f"https://www.cardmarket.com/en/Magic/Products/Search?searchString={q}"


def build_pricecharting_url(card_name: str):
    if not card_name:
        return None
    q = urllib.parse.quote_plus(f"Magic {card_name}")
    return f"https://www.pricecharting.com/search-products?type=prices&q={q}"


def build_tcgplayer_url(card_name: str):
    if not card_name:
        return None
    q = urllib.parse.quote_plus(card_name)
    return f"https://www.tcgplayer.com/search/magic/product?productLineName=magic&q={q}"


# ---------------------------------------------------------
# MULTI-SOURCE AGGREGATION
# ---------------------------------------------------------
def build_multi_source_links(card_name: str, card_data, mtg_links):
    sources = {
        "scryfall": [],
        "gatherer": [],
        "edhrec": [],
        "goldfish": [],
        "cardmarket": [],
        "pricecharting": [],
        "tcgplayer": [],
        "web_mtg": [],
    }

    scryfall_url = build_scryfall_url(card_data)
    if scryfall_url:
        sources["scryfall"].append(scryfall_url)

    g_url = build_gatherer_url(card_name)
    if g_url:
        sources["gatherer"].append(g_url)

    e_url = build_edhrec_url(card_name)
    if e_url:
        sources["edhrec"].append(e_url)

    gf_url = build_goldfish_url(card_name)
    if gf_url:
        sources["goldfish"].append(gf_url)

    cm_url = build_cardmarket_url(card_name)
    if cm_url:
        sources["cardmarket"].append(cm_url)

    pc_url = build_pricecharting_url(card_name)
    if pc_url:
        sources["pricecharting"].append(pc_url)

    tcg_url = build_tcgplayer_url(card_name)
    if tcg_url:
        sources["tcgplayer"].append(tcg_url)

    for link in mtg_links:
        sources["web_mtg"].append(link)

    return sources


# ---------------------------------------------------------
# ARTICLE TEXT (MTG)
# ---------------------------------------------------------
def build_article_text(card_data, video_title: str, multi_sources):
    if not card_data:
        overview = (
            f"{video_title} is being tracked as a Magic: The Gathering content signal without a resolved single card. "
            "This report is operating in general MTG mode, logging the video as part of the broader product and format ecosystem."
        )
        players = (
            f"This video, titled \"{video_title}\", is treated as a gameplay and experience log. "
            "Players can use it to understand how certain cards perform in real scenarios, how openings feel, "
            "and how different pulls impact deckbuilding decisions."
        )
        collectors = (
            "For collectors, the focus is on the products opened, the rarity distribution, and any standout foils, "
            "mythics, or special treatments that appear on camera."
        )
        traders = (
            "For traders and speculators, the video is a live snapshot of what products are being opened, which cards are highlighted, "
            "and how the community might respond to specific pulls."
        )
        formats = (
            "Without a single resolved card, format impact is tracked at the product level—"
            "which sets are being opened, which archetypes appear, and how often certain themes recur."
        )
        risk = (
            "Reprint risk, volatility, and liquidity are inferred from the sets and products featured, "
            "rather than a single card. This content still feeds into the broader MTG signal network."
        )
        verdict = (
            "Even without a resolved single-card focus, this content is logged as part of the "
            "Banking With Billy MTG signal network, contributing to a broader picture of product interest, "
            "set engagement, and player attention."
        )
        cross = (
            "- This content is tracked across Scryfall, Gatherer, TCGPlayer, Cardmarket, EDHREC, MTGGoldfish, and PriceCharting.\n"
            "- Set and product context are inferred from the video title, description, and external links.\n"
            "- Commander and competitive usage are monitored via EDHREC and MTGGoldfish where applicable.\n"
            "- Official rules text and rulings are anchored to Gatherer and Scryfall.\n"
            "- Market snapshots are cross-checked to detect spikes, reprint shocks, and long-term trends."
        )
        return {
            "overview": overview,
            "players": players,
            "collectors": collectors,
            "traders": traders,
            "formats": formats,
            "risk": risk,
            "verdict": verdict,
            "cross": cross,
        }

    name = card_data.get("name", "Unknown Card")
    mana_cost = card_data.get("mana_cost", "")
    type_line = card_data.get("type_line", "Unknown")
    rarity = card_data.get("rarity", "unknown")
    set_name = card_data.get("set_name", "Unknown set")
    color_identity = card_data.get("color_identity", [])
    power = card_data.get("power")
    toughness = card_data.get("toughness")

    color_identity_str = "".join(color_identity) if color_identity else "Colorless (identity: —)"
    stats_str = f"{power}/{toughness}" if power and toughness else "N/A"

    overview = (
        f"{name} is a {rarity} Magic: The Gathering card from the set {set_name}. "
        f"It is printed as a {type_line}, with mana cost {mana_cost or 'N/A'} and color identity {color_identity_str}. "
        "In the Banking With Billy framework, it is tracked as part of the broader MTG ecosystem across formats, "
        "from Commander and Modern to Pioneer and Standard."
    )

    players = (
        f"For players, {name} is evaluated through its mana efficiency, card advantage, and board impact. "
        "Key competitive factors:\n"
        f"- Mana cost: {mana_cost or 'N/A'} and how it fits into curve and tempo\n"
        f"- Type line: {type_line}\n"
        f"- Colors: {color_identity_str}\n"
        f"- Stats: {stats_str}\n"
        "- Oracle text: how its rules text converts into real game actions\n\n"
        "Players care whether this card:\n"
        "- Generates immediate value or long-term inevitability\n"
        "- Slots cleanly into existing archetypes or enables new shells\n"
        "- Trades favorably against the current metagame’s threats and answers\n"
        "- Scales in multiplayer environments like Commander"
    )

    collectors = (
        f"Collectors look at {name} through rarity, set context, and print history. Key collector factors:\n"
        f"- Rarity: {rarity}\n"
        f"- Set: {set_name}\n"
        "- Artwork: illustration, frame treatment, and special variants\n"
        "- Print history: original printing vs. reprints, promos, and special editions\n\n"
        "Collectors are watching for:\n"
        "- Early printings, special frames, and premium treatments\n"
        "- Low population in high grades\n"
        "- Iconic status in Commander, cube, or competitive formats"
    )

    traders = (
        f"For traders and investors, {name} is a moving position tied to format demand, reprint risk, "
        "and cross-format playability. Market snapshot (Scryfall price fields) is used as a baseline, "
        "with external references from TCGPlayer, Cardmarket, and PriceCharting.\n\n"
        "Key trading considerations:\n"
        "- Commander demand and EDHREC adoption\n"
        "- Competitive demand in Modern, Pioneer, Legacy, and Standard\n"
        "- Reprint risk in Masters sets, Secret Lairs, and supplemental products\n"
        "- Liquidity: how quickly copies move at realistic prices"
    )

    formats = (
        f"{name} is evaluated across Commander, Modern, Pioneer, and Standard. "
        "Commander demand is often driven by synergy and uniqueness, while competitive formats care more "
        "about efficiency, flexibility, and interaction with the top decks in the meta."
    )

    risk = (
        f"Reprint risk for {name} is monitored through its set history and role in popular formats. "
        "High visibility on multi-source platforms like Scryfall, EDHREC, and MTGGoldfish, combined with "
        "frequent content appearances, can increase volatility but also deepen liquidity."
    )

    verdict = (
        f"{name} sits at the intersection of gameplay, collection, and finance. "
        "Within Banking With Billy’s MTG engine, it is tracked as a live asset whose value is shaped by "
        "format trends, reprints, and player demand across paper and digital play."
    )

    cross = (
        "- This card is tracked across Scryfall, Gatherer, TCGPlayer, Cardmarket, EDHREC, MTGGoldfish, and PriceCharting.\n"
        f"- Set context: {set_name}, with multi-currency pricing and digital (MTGO) references where available.\n"
        "- Commander usage is monitored via EDHREC, while competitive formats are tracked through MTGGoldfish.\n"
        "- Official rules text and rulings are anchored to Gatherer and Scryfall.\n"
        "- Market snapshots are cross-checked to detect spikes, reprint shocks, and long-term trends."
    )

    return {
        "overview": overview,
        "players": players,
        "collectors": collectors,
        "traders": traders,
        "formats": formats,
        "risk": risk,
        "verdict": verdict,
        "cross": cross,
        "color_identity": color_identity_str,
        "stats": stats_str,
    }


# ---------------------------------------------------------
# VERDICT + PULSE + TIMELINE HELPERS
# ---------------------------------------------------------
def build_billy_verdict(card_data):
    if not card_data:
        return {
            "comp": "medium",
            "coll": "medium",
            "mkt": "medium",
            "label": "Signal in observation mode — no resolved single card, but content is feeding the MTG network."
        }

    prices = card_data.get("prices", {}) or {}
    usd = prices.get("usd")
    usd_foil = prices.get("usd_foil")
    rarity = card_data.get("rarity", "unknown")

    def price_bucket(v):
        try:
            f = float(v)
        except Exception:
            return "low"
        if f >= 20:
            return "high"
        if f >= 5:
            return "medium"
        return "low"

    buckets = []
    if usd:
        buckets.append(price_bucket(usd))
    if usd_foil:
        buckets.append(price_bucket(usd_foil))

    if "mythic" in rarity:
        coll = "high"
    elif "rare" in rarity:
        coll = "medium"
    else:
        coll = "low"

    if "high" in buckets:
        mkt = "high"
    elif "medium" in buckets:
        mkt = "medium"
    else:
        mkt = "low"

    if coll == "high" and mkt in ("high", "medium"):
        comp = "high"
    elif mkt == "high":
        comp = "medium"
    else:
        comp = "medium"

    label = (
        "Competitive, collectible, and market-active — monitored closely for format shifts and price movement."
        if mkt == "high" or coll == "high"
        else "Stable but watchlisted — tracked for emerging synergies, reprints, and Commander adoption."
    )

    return {
        "comp": comp,
        "coll": coll,
        "mkt": mkt,
        "label": label,
    }


def build_pulse_bar(card_data):
    if not card_data:
        return (
            "Live MTG Market Pulse · Tracking this video as a general Magic signal — "
            "set interest, product openings, and player attention are being logged."
        )

    prices = card_data.get("prices", {}) or {}
    usd = prices.get("usd") or "N/A"
    usd_foil = prices.get("usd_foil") or "N/A"
    eur = prices.get("eur") or "N/A"
    rarity = card_data.get("rarity", "unknown")
    set_name = card_data.get("set_name", "Unknown set")
    name = card_data.get("name", "Unknown Card")

    return (
        f"Live MTG Market Pulse · {name} · Set: {set_name} · Rarity: {rarity} · "
        f"Scryfall USD: {usd} · Foil: {usd_foil} · EUR: {eur}"
    )


def build_timeline(card_data, video_meta):
    events = []

    if card_data:
        name = card_data.get("name", "Unknown Card")
        set_name = card_data.get("set_name", "Unknown set")
        released_at = card_data.get("released_at")
        if released_at:
            events.append(f"{released_at} — First printing of {name} in {set_name}.")
        else:
            events.append(f"First printing of {name} in {set_name} (release date not available).")

        rarity = card_data.get("rarity", "unknown")
        events.append(f"Rarity classified as {rarity}, tracked across Commander and competitive formats.")

        prices = card_data.get("prices", {}) or {}
        usd = prices.get("usd")
        usd_foil = prices.get("usd_foil")
        if usd or usd_foil:
            events.append(
                f"Price baselines established on Scryfall — USD: {usd or 'N/A'}, Foil: {usd_foil or 'N/A'}."
            )
        events.append("Ongoing monitoring via EDHREC and MTGGoldfish for format adoption and meta shifts.")
    else:
        events.append("Video logged as a general Magic: The Gathering signal without a resolved single card.")
        events.append("Product, set, and archetype interest inferred from title, description, and visual pulls.")
        events.append("Signal contributes to Banking With Billy’s MTG ecosystem tracking and content‑driven attention flows.")

    if video_meta:
        ts = datetime.now().strftime("%Y-%m-%d")
        events.append(f"{ts} — Featured in a Banking With Billy Magic: The Gathering intelligence report.")

    return "\n".join(f"- {e}" for e in events)


# ---------------------------------------------------------
# HTML BUILDER
# ---------------------------------------------------------
def build_article_html(card_data, multi_sources, video_meta, mp4_path):
    title = video_meta.get("title", "")
    video_url = video_meta.get("url", "")
    video_desc = video_meta.get("description", "")
    video_id = video_meta.get("video_id", "")

    if card_data:
        card_name = card_data.get("name", "Unknown Card")
        mana_cost = card_data.get("mana_cost", "")
        type_line = card_data.get("type_line", "Unknown")
        rarity = card_data.get("rarity", "unknown")
        set_name = card_data.get("set_name", "Unknown set")
        oracle_text = card_data.get("oracle_text", "") or "No rules text available."
        prices = card_data.get("prices", {}) or {}
        usd = prices.get("usd") or "N/A"
        usd_foil = prices.get("usd_foil") or "N/A"
        eur = prices.get("eur") or "N/A"
        eur_foil = prices.get("eur_foil") or "N/A"
        tix = prices.get("tix") or "N/A"
        image_uris = card_data.get("image_uris") or {}
        main_image = (
            image_uris.get("large")
            or image_uris.get("normal")
            or image_uris.get("png")
            or ""
        )
        art_crop = image_uris.get("art_crop") or main_image
    else:
        card_name = title or "Magic: The Gathering Video Report"
        mana_cost = "N/A"
        type_line = "Unknown"
        rarity = "unknown"
        set_name = "Unknown set"
        oracle_text = (
            "Your search criteria didn’t match anything in the Multiverse. Please try again!"
        )
        usd = usd_foil = eur = eur_foil = tix = "N/A"
        main_image = ""
        art_crop = ""

    analysis = build_article_text(card_data, title, multi_sources)
    color_identity_str = analysis.get("color_identity", "Unknown") if card_data else "Unknown"
    stats_str = analysis.get("stats", "N/A") if card_data else "N/A"
    year = 2026

    scryfall_links = multi_sources.get("scryfall", [])
    gatherer_links = multi_sources.get("gatherer", [])
    edhrec_links = multi_sources.get("edhrec", [])
    goldfish_links = multi_sources.get("goldfish", [])
    cardmarket_links = multi_sources.get("cardmarket", [])
    pricecharting_links = multi_sources.get("pricecharting", [])
    tcgplayer_links = multi_sources.get("tcgplayer", [])
    web_mtg_links = multi_sources.get("web_mtg", [])

    def build_link_list(links):
        return "".join('<li><a href="{0}" target="_blank">{0}</a></li>'.format(l) for l in links)

    hero_bg = "radial-gradient(circle at top left, {0}33, {1}22 35%, {2} 70%)".format(
        ACCENT_COLOR, SECONDARY_COLOR, PRIMARY_COLOR
    )

    if mp4_path:
        video_embed_html = """
        <div class="video-short">
          <video src="{mp4}" autoplay muted loop playsinline controls></video>
        </div>
        """.format(mp4=os.path.basename(mp4_path))
    elif video_id:
        video_embed_html = """
        <div class="video-short">
          <iframe
            src="https://www.youtube.com/embed/{vid}?rel=0&modestbranding=1&playsinline=1&autoplay=1&mute=1&loop=1&playlist={vid}"
            title="YouTube video player"
            frameborder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen
          ></iframe>
        </div>
        """.format(vid=video_id)
    else:
        video_embed_html = ""

    if main_image:
        gallery_html = """
        <section class="panel gallery-panel">
          <div class="panel-header">
            <span class="panel-icon">🖼️</span>
            <h2>Card Gallery</h2>
          </div>
          <p class="panel-sub">Primary print and art view for this Magic: The Gathering card.</p>
          <div class="gallery-row">
            <div class="gallery-card">
              <img src="{main}" alt="{name} main image">
            </div>
            {alt_block}
          </div>
        </section>
        """.format(
            main=main_image,
            name=card_name,
            alt_block=(
                "<div class='gallery-card'><img src='{0}' alt='Art crop'></div>".format(art_crop)
                if art_crop and art_crop != main_image
                else ""
            ),
        )
    else:
        gallery_html = ""

    under_video_cta = """
      <section class="panel" style="margin-top:1rem;">
        <div class="panel-header">
          <span class="panel-icon">📡</span>
          <h2>Banking With Billy MTG Article</h2>
        </div>
        <p class="panel-sub">
          This card is featured in a Banking With Billy Magic: The Gathering market intelligence report,
          covering its role in formats, collector value, and trading signals.
        </p>
        <p><a href="#" onclick="location.reload();return false;">Refresh this report →</a></p>
      </section>

      <section class="panel">
        <div class="panel-header">
          <span class="panel-icon">▶️</span>
          <h2>Watch Full Videos</h2>
        </div>
        <p class="panel-sub">
          For full-length MTG videos, breakdowns, and live deck techs, watch the Banking With Billy Magic channel.
        </p>
        <p><a href="https://www.youtube.com/@BankingWithBillyMagic" target="_blank">Watch full videos here →</a></p>
      </section>

      <section class="panel">
        <div class="panel-header">
          <span class="panel-icon">🧙</span>
          <h2>Join the Community</h2>
        </div>
        <p class="panel-sub">
          Connect with MTG players, brewers, and traders in the Banking With Billy Discord. Share lists, discuss meta,
          and get live updates.
        </p>
        <p><a href="https://discord.gg/g7yFTuZ2" target="_blank">Join Magic →</a></p>
      </section>
    """

    verdict = build_billy_verdict(card_data)
    pulse_text = build_pulse_bar(card_data)
    timeline_text = build_timeline(card_data, video_meta)

    def verdict_bar(level):
        if level == "high":
            return '<div class="verdict-bar high"></div>'
        if level == "medium":
            return '<div class="verdict-bar medium"></div>'
        return '<div class="verdict-bar low"></div>'

    verdict_html = """
    <section class="panel">
      <div class="panel-header">
        <span class="panel-icon">🧭</span>
        <h2>Billy’s Verdict</h2>
      </div>
      <p class="panel-sub">Three-axis signal — not a rating, but a live intelligence read on this position.</p>
      <div class="verdict-grid">
        <div class="verdict-item">
          <div class="verdict-label">Competitive Signal</div>
          {comp_bar}
        </div>
        <div class="verdict-item">
          <div class="verdict-label">Collector Signal</div>
          {coll_bar}
        </div>
        <div class="verdict-item">
          <div class="verdict-label">Market Signal</div>
          {mkt_bar}
        </div>
      </div>
      <p class="panel-sub" style="margin-top:0.75rem;">{label}</p>
    </section>
    """.format(
        comp_bar=verdict_bar(verdict["comp"]),
        coll_bar=verdict_bar(verdict["coll"]),
        mkt_bar=verdict_bar(verdict["mkt"]),
        label=verdict["label"],
    )

    timeline_html = """
    <section class="panel">
      <div class="panel-header">
        <span class="panel-icon">⏱️</span>
        <h2>Card Timeline</h2>
      </div>
      <p class="panel-sub">Key moments in this card’s life inside the Magic: The Gathering ecosystem.</p>
      <pre>{timeline}</pre>
    </section>
    """.format(timeline=timeline_text)

    html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{card_name} — MTG Intelligence Report | {brand}</title>
<meta name="description" content="Banking With Billy provides real‑time Magic: The Gathering market intelligence, competitive analysis, and verified multi‑source card data.">
<meta property="og:title" content="{card_name} — MTG Intelligence Report">
<meta property="og:description" content="Real‑time MTG card intelligence, market prices, and cross‑source verification from Banking With Billy.">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Banking With Billy">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{card_name} — MTG Intelligence Report">
<meta name="twitter:description" content="Magic: The Gathering market intelligence and verified card data from Banking With Billy.">
<style>
body {{
  margin:0;
  padding:0;
  background:{primary};
  color:#e5e7eb;
  font-family:system-ui,-apple-system,BlinkMacSystemFont,"Inter",sans-serif;
}}
a {{ color:{accent}; text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
.page-wrap {{
  max-width:1200px;
  margin:0 auto;
  padding:2.5rem 1.5rem 3rem;
}}
.site-header {{
  margin-bottom:0.75rem;
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
.brand-mark span {{ color:{accent}; }}
.header-meta {{
  font-size:0.8rem;
  color:#9ca3af;
  text-align:right;
}}
.pulse-bar {{
  margin:0 0 1.5rem;
  padding:0.5rem 0.9rem;
  border-radius:999px;
  background:rgba(15,23,42,0.95);
  border:1px solid rgba(148,163,184,0.6);
  font-size:0.8rem;
  letter-spacing:0.08em;
  text-transform:uppercase;
  color:#e5e7eb;
  display:flex;
  align-items:center;
  gap:0.75rem;
  overflow:hidden;
  white-space:nowrap;
}}
.pulse-dot {{
  width:8px;
  height:8px;
  border-radius:999px;
  background:{accent};
  box-shadow:0 0 10px {accent};
  animation:pulseGlow 1.6s infinite ease-in-out;
}}
.pulse-text {{
  overflow:hidden;
  text-overflow:ellipsis;
}}
.pulse-session {{
  font-size:0.7rem;
  text-transform:uppercase;
  letter-spacing:0.16em;
  color:#9ca3af;
}}
.hero {{
  background:{hero_bg};
  border-radius:0 0 24px 24px;
  border:1px solid rgba(148,163,184,0.35);
  box-shadow:0 18px 45px rgba(0,0,0,0.65);
  padding:1.75rem;
  display:grid;
  grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);
  gap:1.75rem;
  position:relative;
  overflow:hidden;
}}
.hero::before {{
  content:"";
  position:absolute;
  inset:-40%;
  background:radial-gradient(circle at top, rgba(243,156,18,0.12), transparent 55%);
  opacity:0.9;
  pointer-events:none;
}}
.hero-title {{
  font-size:2.1rem;
  letter-spacing:0.06em;
  text-transform:uppercase;
  margin:0 0 0.5rem;
}}
.hero-sub {{
  margin:0 0 1rem;
  color:#d1d5db;
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
  background:rgba(5,3,10,0.7);
  color:#f9fafb;
}}
.hero-badge.type {{
  border-color:{accent};
  color:{accent};
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
.hero-right {{
  display:flex;
  justify-content:center;
  align-items:center;
  position:relative;
  z-index:1;
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
  position:relative;
  overflow:hidden;
}}
.card-frame::after {{
  content:"";
  position:absolute;
  inset:-40%;
  background:conic-gradient(from 180deg, rgba(243,156,18,0.0), rgba(243,156,18,0.35), rgba(142,68,173,0.0));
  opacity:0.0;
  mix-blend-mode:screen;
  animation:cardGlow 4s infinite linear;
  pointer-events:none;
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
  grid-template-columns:minmax(0,2.1fr) minmax(0,1.1fr);
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
.main-right {{
  position:sticky;
  top:1.5rem;
  display:flex;
  flex-direction:column;
  gap:1.25rem;
}}
.video-short {{
  width:100%;
  aspect-ratio:9/16;
  border-radius:12px;
  overflow:hidden;
  border:1px solid #1f2937;
  box-shadow:0 10px 24px rgba(0,0,0,0.7);
}}
.video-short iframe,
.video-short video {{
  width:100%;
  height:100%;
  object-fit:cover;
}}
.video-scroll {{
  display:flex;
  gap:1rem;
  overflow-x:auto;
  padding-bottom:0.5rem;
  scrollbar-width:thin;
}}
.video-scroll::-webkit-scrollbar {{
  height:6px;
}}
.video-scroll::-webkit-scrollbar-thumb {{
  background:#444;
  border-radius:3px;
}}
.gallery-panel {{
  margin-top:1.5rem;
}}
.gallery-row {{
  display:flex;
  flex-wrap:wrap;
  gap:0.75rem;
}}
.gallery-card {{
  flex:1 1 180px;
}}
.gallery-card img {{
  width:100%;
  border-radius:10px;
  border:1px solid #1f2937;
  box-shadow:0 10px 24px rgba(0,0,0,0.7);
}}
.panel-sub,
.ygo-list,
.ygo-list li,
.panel p,
pre {{
  overflow-wrap:anywhere;
  word-wrap:break-word;
}}
pre {{
  max-height:180px;
  overflow-y:auto;
}}
.cross-box {{
  white-space:pre-wrap;
  word-wrap:break-word;
  overflow-x:hidden;
  font-family:ui-monospace, Menlo, Monaco, Consolas, "Courier New", monospace;
  font-size:0.85rem;
  line-height:1.6;
  background:#020617;
  border:1px solid rgba(148,163,184,0.7);
  border-radius:10px;
  padding:0.75rem 0.9rem;
}}
.verdict-grid {{
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:0.75rem;
  margin-top:0.5rem;
}}
.verdict-item {{
  display:flex;
  flex-direction:column;
  gap:0.25rem;
}}
.verdict-label {{
  font-size:0.75rem;
  text-transform:uppercase;
  letter-spacing:0.12em;
  color:#9ca3af;
}}
.verdict-bar {{
  height:8px;
  border-radius:999px;
  background:#111827;
  position:relative;
  overflow:hidden;
}}
.verdict-bar::after {{
  content:"";
  position:absolute;
  left:0;
  top:0;
  bottom:0;
  border-radius:999px;
}}
.verdict-bar.high::after {{
  width:100%;
  background:linear-gradient(90deg,#22c55e,#4ade80);
  box-shadow:0 0 12px #22c55e;
}}
.verdict-bar.medium::after {{
  width:60%;
  background:linear-gradient(90deg,#facc15,#f97316);
  box-shadow:0 0 12px #f97316;
}}
.verdict-bar.low::after {{
  width:30%;
  background:linear-gradient(90deg,#6b7280,#4b5563);
  box-shadow:0 0 8px #4b5563;
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
.footer span {{ color:{accent}; }}
@keyframes pulseGlow {{
  0% {{ box-shadow:0 0 4px {accent}; opacity:0.7; }}
  50% {{ box-shadow:0 0 14px {accent}; opacity:1; }}
  100% {{ box-shadow:0 0 4px {accent}; opacity:0.7; }}
}}
@keyframes cardGlow {{
  0% {{ opacity:0.0; transform:rotate(0deg); }}
  50% {{ opacity:0.35; transform:rotate(180deg); }}
  100% {{ opacity:0.0; transform:rotate(360deg); }}
}}
@media (max-width:900px) {{
  .hero {{ grid-template-columns:minmax(0,1fr); }}
  .main-layout {{ grid-template-columns:minmax(0,1fr); }}
  .main-right {{ position:static; }}
  .verdict-grid {{ grid-template-columns:minmax(0,1fr); }}
}}
</style>
</head>
<body>
<div class="page-wrap">

<header class="site-header">
  <div class="brand-mark">
    <span>Banking With Billy · Magic: The Gathering Market Intelligence & Competitive Analysis</span>
  </div>
  <div class="header-meta">
    <div>Banking With Billy · The Global Authority in MTG Card Data & Market Research</div>
    <div>Real‑time MTG data reporting, competitive meta tracking, and verified multi‑source card intelligence</div>
  </div>
</header>

<div class="pulse-bar">
  <div class="pulse-dot"></div>
  <div class="pulse-text">{pulse_text}</div>
  <div class="pulse-session">Session: Live MTG Intelligence Capture</div>
</div>

<section class="hero">
  <div class="hero-left">
    <h1 class="hero-title">{card_name}</h1>
    <p class="hero-sub">
      A complete Magic: The Gathering market intelligence and competitive analysis report generated by the Banking With Billy Trading Card Intelligence Network.
    </p>
    <div class="hero-badge-row">
      <div class="hero-badge type">{type_line}</div>
      {rarity_badge}
      {set_badge}
    </div>
    <div class="hero-grid">
      <div>
        <div class="hero-grid-label">Color Identity</div>
        <div class="hero-grid-value">{color_identity}</div>
      </div>
      <div>
        <div class="hero-grid-label">Rarity</div>
        <div class="hero-grid-value">{rarity}</div>
      </div>
      <div>
        <div class="hero-grid-label">Set</div>
        <div class="hero-grid-value">{set_name}</div>
      </div>
      <div>
        <div class="hero-grid-label">Mana Cost</div>
        <div class="hero-grid-value">{mana_cost}</div>
      </div>
      <div>
        <div class="hero-grid-label">Stats</div>
        <div class="hero-grid-value">{stats}</div>
      </div>
      <div>
        <div class="hero-grid-label">Linked video metadata</div>
        <div class="hero-grid-value">{video_title}</div>
      </div>
    </div>
  </div>
  <div class="hero-right">
    <div class="card-frame">
      <div class="card-inner">
        {card_img}
        <div class="card-footer-strip">MAGIC: THE GATHERING · {card_name}</div>
      </div>
    </div>
  </div>
</section>

<div class="main-layout">
  <div class="main-left">
    <section class="panel">
      <div class="panel-header">
        <span class="panel-icon">⚡</span>
        <h2>Oracle Text & Rules</h2>
      </div>
      <div class="effect-box">{oracle_text}</div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <span class="panel-icon">📦</span>
        <h2>Set & Print Context</h2>
      </div>
      <p class="panel-sub">Where this card lives inside the Magic: The Gathering product ecosystem.</p>
      <p><strong>Set:</strong> {set_name}</p>
      <p><strong>Rarity:</strong> {rarity}</p>
    </section>

    {timeline_html}

    <section class="panel">
      <div class="panel-header">
        <span class="panel-icon">💰</span>
        <h2>Price & Market Snapshot</h2>
      </div>
      <p class="panel-sub">Scryfall baseline pricing with external market references.</p>
      <div class="market-widget">
        <div class="market-row"><span class="label">Scryfall USD</span><span class="value">{usd}</span></div>
        <div class="market-row"><span class="label">Scryfall USD Foil</span><span class="value">{usd_foil}</span></div>
        <div class="market-row"><span class="label">Scryfall EUR / EUR Foil</span><span class="value">{eur} / {eur_foil}</span></div>
        <div class="market-row"><span class="label">Scryfall Tix (MTGO)</span><span class="value">{tix}</span></div>
      </div>
      <p class="panel-sub" style="margin-top:0.75rem;">External snapshots:</p>
      <ul class="ygo-list">
        <li>TCGPlayer snapshot: {tcg_snapshot}</li>
        <li>Cardmarket snapshot: {cm_snapshot}</li>
        <li>PriceCharting snapshot: {pc_snapshot}</li>
      </ul>
    </section>

    <section class="panel">
      <div class="panel-header">
        <span class="panel-icon">📖</span>
        <h2>Overview & Roles</h2>
      </div>
      <h3>Overview</h3>
      <p>{overview}</p>
      <h3>For Players</h3>
      <p>{players}</p>
      <h3>For Collectors</h3>
      <p>{collectors}</p>
      <h3>For Traders</h3>
      <p>{traders}</p>
      <h3>Format Impact</h3>
      <p>{formats}</p>
      <h3>Risk & Reprint Profile</h3>
      <p>{risk}</p>
      <h3>Final Verdict</h3>
      <p>{verdict_text}</p>
    </section>

    <section class="panel">
      <div class="panel-header">
        <span class="panel-icon">🧠</span>
        <h2>Cross-Site Correlation & Insights</h2>
      </div>
      <p class="panel-sub">How this card is tracked across the MTG data network.</p>
      <div class="cross-box">{cross}</div>
    </section>

    {gallery_html}
  </div>

  <div class="main-right">
    <section class="panel">
      <div class="panel-header">
        <span class="panel-icon">🎬</span>
        <h2>Video, News & Community</h2>
      </div>
      <div class="video-scroll">
        {video_embed_html}
      </div>
    </section>

    {verdict_html}

    <section class="panel">
      <div class="panel-header">
        <span class="panel-icon">🌐</span>
        <h2>Primary Data Sources</h2>
      </div>
      <p class="panel-sub">Core MTG data endpoints used to anchor this report.</p>
      <h3>Scryfall</h3>
      <ul class="ygo-list">
        {scryfall_list}
      </ul>
      <h3>Gatherer / Wizards</h3>
      <ul class="ygo-list">
        {gatherer_list}
      </ul>
      <h3>EDHREC</h3>
      <ul class="ygo-list">
        {edhrec_list}
      </ul>
      <h3>MTGGoldfish</h3>
      <ul class="ygo-list">
        {goldfish_list}
      </ul>
    </section>

    <section class="panel">
      <div class="panel-header">
        <span class="panel-icon">📊</span>
        <h2>Market & Price Feeds</h2>
      </div>
      <p class="panel-sub">External price and market references for deeper financial context.</p>
      <h3>Cardmarket</h3>
      <ul class="ygo-list">
        {cardmarket_list}
      </ul>
      <h3>PriceCharting</h3>
      <ul class="ygo-list">
        {pricecharting_list}
      </ul>
      <h3>TCGPlayer</h3>
      <ul class="ygo-list">
        {tcgplayer_list}
      </ul>
    </section>

    <section class="panel">
      <div class="panel-header">
        <span class="panel-icon">🔗</span>
        <h2>Web MTG Links</h2>
      </div>
      <p class="panel-sub">Filtered MTG‑relevant links discovered from the wider web for this video and card focus.</p>
      <ul class="ygo-list">
        {web_mtg_list}
      </ul>
    </section>

    {under_video_cta}
  </div>
</div>

<div class="footer">
  © {year} Banking With Billy. Published by the Banking With Billy Trading Card Intelligence Network — independent MTG market analysis, competitive insights, and real‑time TCG reporting.
</div>

</div>
</body>
</html>
""".format(
        card_name=card_name,
        brand=BRAND_NAME,
        primary=PRIMARY_COLOR,
        accent=ACCENT_COLOR,
        hero_bg=hero_bg,
        type_line=type_line,
        rarity_badge=("<div class='hero-badge'>Rarity: {0}</div>".format(rarity) if rarity else ""),
        set_badge=("<div class='hero-badge'>Set: {0}</div>".format(set_name) if set_name else ""),
        mana_cost=(mana_cost or "N/A"),
        video_title=title,
        card_img=("<img src='{0}' alt='{1} card'>".format(main_image, card_name) if main_image else ""),
        oracle_text=oracle_text,
        usd=usd,
        usd_foil=usd_foil,
        eur=eur,
        eur_foil=eur_foil,
        tix=tix,
        overview=analysis["overview"],
        players=analysis["players"],
        collectors=analysis["collectors"],
        traders=analysis["traders"],
        formats=analysis["formats"],
        risk=analysis["risk"],
        verdict_text=analysis["verdict"],
        cross=analysis["cross"],
        gallery_html=gallery_html,
        video_embed_html=video_embed_html,
        scryfall_list=build_link_list(scryfall_links),
        gatherer_list=build_link_list(gatherer_links),
        edhrec_list=build_link_list(edhrec_links),
        goldfish_list=build_link_list(goldfish_links),
        cardmarket_list=build_link_list(cardmarket_links),
        pricecharting_list=build_link_list(pricecharting_links),
        tcgplayer_list=build_link_list(tcgplayer_links),
        web_mtg_list=build_link_list(web_mtg_links),
        under_video_cta=under_video_cta,
        year=year,
        set_name=set_name,
        rarity=rarity,
        color_identity=color_identity_str,
        stats=stats_str,
        tcg_snapshot=("N/A" if not tcgplayer_links else "See TCGPlayer links below"),
        cm_snapshot=("N/A" if not cardmarket_links else "See Cardmarket links below"),
        pc_snapshot=("N/A" if not pricecharting_links else "See PriceCharting links below"),
        pulse_text=pulse_text,
        verdict_html=verdict_html,
        timeline_html=timeline_html,
    )

    return html


# ---------------------------------------------------------
# MAIN ENGINE — ONLY LAST VIDEO
# ---------------------------------------------------------
def run():
    log("Fetching latest video...\n")
    video_meta = get_latest_video()
    if not video_meta:
        log("No videos found.")
        return

    title = video_meta["title"]
    video_url = video_meta["url"]
    log(f"PROCESSING LATEST VIDEO: {title}\n")

    card_name = extract_card_name(title)
    card_data = get_card_data(card_name)

    global_results = search_web(title)
    mtg_results = filter_mtg_links(global_results)

    multi_sources = build_multi_source_links(card_name, card_data, mtg_results)

    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base_name = clean_name(card_name if card_data else title)
    filename = f"{base_name}_{now}.html"
    path = os.path.join(ARTICLES_DIR, filename)

    mp4_path = download_video_mp4(video_url, ARTICLES_DIR, base_name)

    html = build_article_html(card_data, multi_sources, video_meta, mp4_path)

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

    log_data = {
        "timestamp": now,
        "video": video_meta,
        "video_mp4": os.path.basename(mp4_path) if mp4_path else None,
        "card_name": card_name,
        "card_found": bool(card_data),
        "card_data_core": {
            "name": safe_get(card_data, "name", None),
            "set_name": safe_get(card_data, "set_name", None),
            "rarity": safe_get(card_data, "rarity", None),
            "type_line": safe_get(card_data, "type_line", None),
            "prices": safe_get(card_data, "prices", {}),
        },
        "multi_sources": multi_sources,
        "article_path": path,
    }
    log_file = os.path.join(LOGS_DIR, f"{base_name}_{now}.json")
    with open(log_file, "w", encoding="utf-8") as jf:
        json.dump(log_data, jf, indent=2)

    log("============================================================")
    log("ARTICLE GENERATED")
    log(path)
    log("LOG WRITTEN")
    log(log_file)
    log("MP4 PATH")
    log(str(mp4_path))
    log("============================================================")


# ---------------------------------------------------------
# RUN
# ---------------------------------------------------------
if __name__ == "__main__":
    run()

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Banking With Billy Cards – The TCG News Engine</title>
<meta name="viewport" content="width=device-width, initial-scale=1">

<meta name="description" content="The TCG news engine for Yu-Gi-Oh, Pokémon, and Magic: live signals, market moves, set leaks, meta shifts, and premium editorial coverage.">
<meta property="og:title" content="Banking With Billy Cards – The TCG News Engine">
<meta property="og:description" content="Live TCG news, market signals, set leaks, and competitive insights across Yu-Gi-Oh, Pokémon, and Magic.">
<meta property="og:type" content="website">

<style>
:root{
  --bg:#05070b;
  --panel:#0d1117;
  --panel-soft:#111827;
  --border:#1f2933;
  --accent:#f97316;
  --accent-soft:#fbbf24;
  --text:#e5e7eb;
  --muted:#9ca3af;
  --danger:#ef4444;
  --success:#22c55e;
  --info:#3b82f6;
}
*{box-sizing:border-box;margin:0;padding:0;}
body{
  margin:0;
  font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  background:radial-gradient(circle at top,#020617 0,#020617 40%,#020617 60%,#020617 100%),var(--bg);
  color:var(--text);
}
a{text-decoration:none;color:inherit;}
img{max-width:100%;display:block;border-radius:.6rem;}
.wrap{max-width:1400px;margin:auto;padding:1.5rem;}
.header{
  background:rgba(5,7,11,.96);
  border-bottom:1px solid var(--border);
  backdrop-filter:blur(12px);
  position:sticky;top:0;z-index:20;
}
.header-inner{
  max-width:1400px;margin:auto;
  padding:.8rem 1.5rem;
  display:flex;justify-content:space-between;align-items:center;gap:1rem;
}
.logo-block{display:flex;align-items:center;gap:.7rem;}
.logo-icon{
  width:32px;height:32px;border-radius:10px;
  background:conic-gradient(from 140deg,var(--accent),var(--accent-soft),var(--success),var(--info),var(--accent));
  box-shadow:0 0 18px rgba(249,115,22,.6);
}
.logo-title{
  font-weight:800;font-size:1.1rem;
  text-transform:uppercase;letter-spacing:.08em;
  color:var(--accent);
}
.logo-tag{font-size:.75rem;color:var(--muted);margin-top:-3px;}
.nav a{margin-left:1.4rem;color:var(--muted);font-size:.9rem;}
.nav a:hover{color:var(--accent);}
.indexbar{background:#050814;border-bottom:1px solid var(--border);}
.index-inner{
  max-width:1400px;margin:auto;
  padding:.6rem 1.5rem;
  display:flex;gap:2rem;font-size:.85rem;
}
.index-item{display:flex;flex-direction:column;}
.index-label{
  color:var(--muted);font-size:.7rem;
  text-transform:uppercase;letter-spacing:.08em;
}
.index-value{font-weight:600;}
.index-up{color:var(--success);}
.index-down{color:var(--danger);}
.breaking{
  background:var(--accent);color:#020617;
  padding:.55rem 0;font-weight:600;font-size:.9rem;
}
.breaking-inner{
  max-width:1400px;margin:auto;
  padding:0 1.5rem;overflow:hidden;white-space:nowrap;
}
.breaking-track{display:inline-block;animation:scroll 22s linear infinite;}
@keyframes scroll{0%{transform:translateX(0);}100%{transform:translateX(-50%);}}
.hero{
  max-width:1400px;margin:2rem auto;
  padding:2.5rem;border-radius:1.4rem;
  border:1px solid rgba(148,163,184,.3);
  background:
    radial-gradient(circle at top left,rgba(249,115,22,.25),transparent 55%),
    radial-gradient(circle at top right,rgba(59,130,246,.25),transparent 55%),
    linear-gradient(145deg,#020617,#020617 40%,#020617 100%);
  display:grid;grid-template-columns:2fr 1.2fr;gap:2rem;
}
.hero-tag{
  display:inline-block;padding:.25rem .7rem;
  border-radius:999px;background:rgba(15,23,42,.9);
  border:1px solid rgba(249,115,22,.7);
  color:var(--accent-soft);font-size:.75rem;
  font-weight:700;text-transform:uppercase;letter-spacing:.08em;
  margin-bottom:.6rem;
}
.hero h1{font-size:2.4rem;margin-bottom:.7rem;color:var(--accent-soft);}
.hero p{color:#cbd5e1;font-size:1.05rem;line-height:1.7;margin-bottom:1rem;}
.hero-meta{font-size:.8rem;color:var(--muted);}
.hero-image{
  border-radius:1.1rem;
  background:
    radial-gradient(circle at top left,rgba(249,115,22,.7),transparent 60%),
    radial-gradient(circle at bottom right,rgba(59,130,246,.6),transparent 60%),
    #020617;
  display:flex;align-items:flex-end;justify-content:flex-start;
  padding:1.1rem;position:relative;overflow:hidden;
}
.hero-image::before{
  content:"";position:absolute;inset:0;
  background:radial-gradient(circle at center,rgba(15,23,42,.3),transparent 60%);
}
.hero-image span{
  position:relative;background:rgba(15,23,42,.9);
  padding:.45rem .8rem;border-radius:.7rem;
  font-size:.85rem;font-weight:600;color:#e5e7eb;
  border:1px solid rgba(148,163,184,.6);
}
.pulse{
  max-width:1400px;margin:2rem auto;
  padding:1rem 1.5rem;border-radius:1rem;
  border:1px solid var(--border);
  background:rgba(15,23,42,.9);
  display:flex;gap:1.2rem;overflow-x:auto;
}
.pulse-item{
  min-width:220px;background:var(--panel-soft);
  padding:1rem;border-radius:.8rem;
  border:1px solid rgba(31,41,55,.9);
}
.pulse-item h4{color:var(--accent-soft);margin-bottom:.4rem;font-size:.95rem;}
.pulse-item p{font-size:.85rem;color:#cbd5e1;}
.main-grid{
  max-width:1400px;margin:2rem auto;
  padding:0 1.5rem;
  display:grid;grid-template-columns:2fr 1fr;gap:2rem;
}
.left-col{display:flex;flex-direction:column;gap:1.4rem;}
.story{
  background:var(--panel);
  border:1px solid var(--border);
  padding:1.2rem 1.3rem;border-radius:1rem;
  transition:.15s;
}
.story:hover{
  background:#111827;
  border-color:var(--accent);
  transform:translateY(-2px);
}
.story-label{
  font-size:.75rem;text-transform:uppercase;
  letter-spacing:.08em;color:var(--muted);
  margin-bottom:.4rem;
}
.story h2{font-size:1.25rem;margin-bottom:.5rem;color:var(--accent-soft);}
.story p{color:#cbd5e1;font-size:.95rem;line-height:1.6;}
.story-meta{margin-top:.5rem;font-size:.8rem;color:var(--muted);}
.sidebar{display:flex;flex-direction:column;gap:1.4rem;}
.sidebar-block{
  background:var(--panel);
  border:1px solid var(--border);
  padding:1rem 1.1rem;border-radius:1rem;
}
.sidebar-block h3{color:var(--accent-soft);margin-bottom:.7rem;font-size:1.05rem;}
.sidebar-block div{margin-bottom:.45rem;color:#cbd5e1;font-size:.9rem;}
.sidebar-block div:last-child{margin-bottom:0;}
.badge{
  font-size:.7rem;text-transform:uppercase;
  letter-spacing:.08em;color:var(--muted);
  margin-bottom:.4rem;
}
.section{
  max-width:1400px;margin:3rem auto 0;
  padding:0 1.5rem;
}
.section h2{color:var(--accent-soft);font-size:1.5rem;margin-bottom:.7rem;}
.section-sub{font-size:.9rem;color:var(--muted);margin-bottom:1rem;}
.channel-grid{
  display:grid;grid-template-columns:repeat(3,1fr);gap:1.2rem;
}
.channel-card{
  background:var(--panel);
  border:1px solid var(--border);
  padding:1rem;border-radius:1rem;
  transition:.15s;
}
.channel-card:hover{
  background:#111827;
  border-color:var(--accent);
  transform:translateY(-2px);
}
.channel-thumb{
  width:100%;height:130px;border-radius:.8rem;
  margin-bottom:.8rem;display:flex;
  align-items:center;justify-content:center;
  font-size:.85rem;color:var(--muted);
}
.thumb-ygo{background:radial-gradient(circle at top,#f97316,transparent 60%),#020617;}
.thumb-pkm{background:radial-gradient(circle at top,#22c55e,transparent 60%),#020617;}
.thumb-mtg{background:radial-gradient(circle at top,#3b82f6,transparent 60%),#020617;}
.channel-title{color:var(--accent-soft);font-size:1.05rem;margin-bottom:.25rem;}
.channel-meta{font-size:.85rem;color:var(--muted);}
.news-list{
  max-width:1400px;margin:3rem auto 0;
  padding:0 1.5rem;
}
.news-header{
  display:flex;justify-content:space-between;
  align-items:center;margin-bottom:.6rem;
}
.news-header-title{font-size:1.1rem;color:var(--accent-soft);}
.news-header-link{font-size:.85rem;color:var(--muted);}
.news-header-link:hover{color:var(--accent);}
.news-item{
  padding:.7rem 0;border-bottom:1px solid var(--border);
  font-size:.9rem;display:flex;
  justify-content:space-between;gap:1rem;
}
.news-item a{color:var(--text);}
.news-item a:hover{color:var(--accent);}
.news-tag{font-size:.75rem;color:var(--muted);}
footer{
  background:#05070b;
  border-top:1px solid var(--border);
  margin-top:3rem;padding:2rem 0;
}
.footer-inner{
  max-width:1400px;margin:auto;
  padding:0 1.5rem;
  display:grid;grid-template-columns:repeat(3,1fr);gap:2rem;
}
.footer-col h4{
  color:var(--accent-soft);
  margin-bottom:.6rem;font-size:1rem;
}
.footer-col a{
  display:block;color:var(--muted);
  margin-bottom:.4rem;font-size:.85rem;
}
.footer-col a:hover{color:var(--accent);}
.footer-bottom{
  text-align:center;margin-top:1.5rem;
  color:var(--muted);font-size:.8rem;
}
@media(max-width:900px){
  .header-inner{padding:.8rem 1rem;}
  .index-inner{padding:.6rem 1rem;}
  .breaking-inner{padding:0 1rem;}
  .hero{grid-template-columns:1fr;padding:1.8rem 1.4rem;}
  .main-grid{grid-template-columns:1fr;padding:0 1rem;}
  .section,.news-list{padding:0 1rem;}
  .channel-grid{grid-template-columns:1fr;}
  .footer-inner{grid-template-columns:1fr;padding:0 1rem;}
}
</style>
</head>
<body>

<div class="header">
  <div class="header-inner">
    <div class="logo-block">
      <div class="logo-icon"></div>
      <div>
        <div class="logo-title">Banking With Billy Cards</div>
        <div class="logo-tag">The TCG News Engine</div>
      </div>
    </div>
    <div class="nav">
      <a href="/">Home</a>
      <a href="/NEWS.html">News</a>
      <a href="/channels/yugioh/">Yu‑Gi‑Oh</a>
      <a href="/channels/pokemon/">Pokémon</a>
      <a href="/channels/magic/">Magic</a>
    </div>
  </div>
</div>

<div class="indexbar">
  <div class="index-inner">
    <div class="index-item">
      <div class="index-label">Yu‑Gi‑Oh Index</div>
      <div class="index-value index-up">+3.2%</div>
    </div>
    <div class="index-item">
      <div class="index-label">Pokémon Index</div>
      <div class="index-value index-down">‑1.1%</div>
    </div>
    <div class="index-item">
      <div class="index-label">Magic Index</div>
      <div class="index-value index-up">+0.8%</div>
    </div>
  </div>
</div>

<div class="breaking">
  <div class="breaking-inner">
    <div class="breaking-track">
      {BREAKING_NEWS}
    </div>
  </div>
</div>

<div class="hero">
  <div>
    <div class="hero-tag">Live TCG Coverage</div>
    <h1>{HERO_TITLE}</h1>
    <p>{HERO_SUMMARY}</p>
    <div class="hero-meta">{HERO_META}</div>
  </div>
  <div class="hero-image">
    <span>{HERO_BADGE}</span>
  </div>
</div>

<div class="pulse">
{DAILY_PULSE}
</div>

<div class="main-grid">
  <div class="left-col">
{FEATURED_STORIES}
  </div>
  <div class="sidebar">
    <div class="sidebar-block">
      <div class="badge">Signals</div>
      <h3>Quick Signals</h3>
{QUICK_SIGNALS}
    </div>
    <div class="sidebar-block">
      <div class="badge">Engagement</div>
      <h3>Card of the Day</h3>
      <div>Which card is most likely to spike next?</div>
      <div>• A: A staple hand trap</div>
      <div>• B: A mid‑tier Pokémon chase</div>
      <div>• C: A Commander‑only mythic</div>
      <div style="margin-top:.4rem;font-size:.8rem;color:var(--muted);">Come back tomorrow for a new pick and recap.</div>
    </div>
    <div class="sidebar-block">
      <div class="badge">Trending</div>
      <h3>Most Read Today</h3>
{TRENDING_LIST}
    </div>
  </div>
</div>

<div class="section">
  <h2>Explore Channels</h2>
  <div class="section-sub">Focused coverage for each game — pulls, prices, deck tech, and live reactions from Billy’s channels.</div>
  <div class="channel-grid">
    <div class="channel-card">
      <div class="channel-thumb thumb-ygo">Yu‑Gi‑Oh highlights, staples, and meta shifts.</div>
      <div class="channel-title"><a href="channels/yugioh/">Yu‑Gi‑Oh Channel</a></div>
      <div class="channel-meta">From Billy’s Yu‑Gi‑Oh Deck — openings, staples, and format‑defining cards.</div>
    </div>
    <div class="channel-card">
      <div class="channel-thumb thumb-pkm">Pokémon chase cards, hits, and long‑term holds.</div>
      <div class="channel-title"><a href="channels/pokemon/">Pokémon Channel</a></div>
      <div class="channel-meta">From Billy Breaks Pokémon — hits, hype, and collector‑grade plays.</div>
    </div>
    <div class="channel-card">
      <div class="channel-thumb thumb-mtg">Magic Commander bombs, staples, and reprints.</div>
      <div class="channel-title"><a href="channels/magic/">Magic Channel</a></div>
      <div class="channel-meta">From Billy’s SpellBook — EDH bombs, staples, and price memory.</div>
    </div>
  </div>
</div>

<div class="news-list">
  <div class="news-header">
    <div class="news-header-title">Latest Articles</div>
    <a class="news-header-link" href="/NEWS.html">View full news feed →</a>
  </div>
{LATEST_NEWS}
</div>

<footer>
  <div class="footer-inner">
    <div class="footer-col">
      <h4>Banking With Billy Cards</h4>
      <a href="/">Home</a>
      <a href="/NEWS.html">News</a>
    </div>
    <div class="footer-col">
      <h4>Channels</h4>
      <a href="/channels/yugioh/">Yu‑Gi‑Oh</a>
      <a href="/channels/pokemon/">Pokémon</a>
      <a href="/channels/magic/">Magic</a>
    </div>
    <div class="footer-col">
      <h4>About</h4>
      <a href="#">About the project</a>
      <a href="#">Contact</a>
      <a href="#">Terms</a>
      <a href="#">Privacy</a>
    </div>
  </div>
  <div class="footer-bottom">© 2026 Banking With Billy. All rights reserved.</div>
</footer>

</body>
</html>
"""

def fetch_rss(url, limit=5):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        items = []
        for item in root.findall(".//item")[:limit]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()
            items.append({"title": title, "link": link, "pub": pub})
        return items
    except Exception:
        return []

def build_breaking_news(all_items):
    titles = [i["title"] for i in all_items[:6] if i["title"]]
    if not titles:
        return "Live TCG coverage across Yu‑Gi‑Oh, Pokémon, and Magic •"
    return " • ".join(titles) + " •"

def build_featured_stories(all_items):
    blocks = []
    for i, item in enumerate(all_items[:4]):
        label = "Feature" if i == 0 else "Update"
        blocks.append(f"""
  <div class="story">
    <div class="story-label">{label}</div>
    <h2><a href="{item['link']}" target="_blank" rel="noopener noreferrer">{item['title']}</a></h2>
    <p>Live coverage pulled from the TCG news stream. Click through for full details.</p>
    <div class="story-meta">{item.get('pub','').split('+')[0]}</div>
  </div>""")
    if not blocks:
        blocks.append("""
  <div class="story">
    <div class="story-label">Feature</div>
    <h2>No live stories available yet</h2>
    <p>Once the feed engine pulls in data, this block will fill with live TCG headlines.</p>
    <div class="story-meta">Waiting for first sync</div>
  </div>""")
    return "\n".join(blocks)

def build_quick_signals(all_items):
    if not all_items:
        return "      <div>• Live signals will appear here once feeds sync.</div>"
    return "\n".join([f"      <div>• {i['title']}</div>" for i in all_items[:4]])

def build_trending_list(all_items):
    if not all_items:
        return "      <div>• Most‑read stories will appear here once feeds sync.</div>"
    return "\n".join([f"      <div>• {i['title']}</div>" for i in all_items[:4]])

def build_daily_pulse():
    return """
  <div class="pulse-item">
    <h4>Market Movers</h4>
    <p>Yu‑Gi‑Oh staples up in early trading as players reposition ahead of the next list.</p>
  </div>
  <div class="pulse-item">
    <h4>Set Watch</h4>
    <p>Pokémon pre‑release singles showing real demand — not just hype — in early sales.</p>
  </div>
  <div class="pulse-item">
    <h4>Meta Shift</h4>
    <p>Magic Commander decks reshaping weekend events as new legends hit tables.</p>
  </div>
  <div class="pulse-item">
    <h4>Grading Trends</h4>
    <p>PSA 10 premiums widening across modern hits, especially alt‑arts and chase slots.</p>
  </div>
"""

def build_latest_news(all_items):
    if not all_items:
        return """
  <div class="news-item">
    <a href="#">Loading latest articles…</a>
    <span class="news-tag">Waiting for first sync</span>
  </div>"""
    blocks = []
    for item in all_items[:6]:
        blocks.append(f"""
  <div class="news-item">
    <a href="{item['link']}" target="_blank" rel="noopener noreferrer">{item['title']}</a>
    <span class="news-tag">{item.get('pub','').split('+')[0]}</span>
  </div>""")
    return "\n".join(blocks)

def main():
    feeds = [
        "https://ygorganization.com/feed/",
        "https://www.pokebeach.com/feed",
        "https://www.mtggoldfish.com/articles.rss"
    ]

    all_items = []
    for url in feeds:
        all_items.extend(fetch_rss(url, limit=6))

    def sort_key(item):
        return item.get("pub", "")
    all_items = sorted(all_items, key=sort_key, reverse=True)

    breaking = build_breaking_news(all_items)
    featured = build_featured_stories(all_items)
    quick = build_quick_signals(all_items)
    trending = build_trending_list(all_items)
    pulse = build_daily_pulse()
    latest = build_latest_news(all_items)

    now = datetime.now(timezone.utc).strftime("Updated %Y-%m-%d %H:%M UTC")

    hero_title = "Live Signals Across Yu‑Gi‑Oh, Pokémon, and Magic"
    hero_summary = "This homepage is powered by a live TCG feed engine pulling headlines from multiple open sources across the card gaming world."
    hero_meta = now
    hero_badge = "Powered by the Banking With Billy Cards feed engine."

    html = HTML_TEMPLATE
    html = html.replace("{BREAKING_NEWS}", breaking)
    html = html.replace("{FEATURED_STORIES}", featured)
    html = html.replace("{QUICK_SIGNALS}", quick)
    html = html.replace("{TRENDING_LIST}", trending)
    html = html.replace("{DAILY_PULSE}", pulse)
    html = html.replace("{LATEST_NEWS}", latest)
    html = html.replace("{HERO_TITLE}", hero_title)
    html = html.replace("{HERO_SUMMARY}", hero_summary)
    html = html.replace("{HERO_META}", hero_meta)
    html = html.replace("{HERO_BADGE}", hero_badge)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    main()

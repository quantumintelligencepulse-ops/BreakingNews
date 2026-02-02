import re
import requests
from dataclasses import dataclass, asdict
from typing import List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# ============================
# DATA MODEL
# ============================

@dataclass
class ArticleContent:
    url: str
    title: str
    main_image: str
    all_images: List[str]
    summary: str
    full_text: str


# ============================
# FETCH HTML
# ============================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

def fetch_html(url: str, timeout: int = 10) -> Optional[str]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception:
        return None


# ============================
# HELPERS
# ============================

def _absolute(src: str, base: str) -> str:
    return urljoin(base, src)


# ============================
# IMAGE EXTRACTION
# ============================

def extract_main_image(soup: BeautifulSoup, base_url: str) -> str:
    # 1) og:image
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        return _absolute(og["content"].strip(), base_url)

    # 2) twitter:image
    tw = soup.find("meta", attrs={"name": "twitter:image"})
    if tw and tw.get("content"):
        return _absolute(tw["content"].strip(), base_url)

    # 3) first large-ish <img>
    candidates = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        src = src.strip()
        if not src:
            continue
        src = _absolute(src, base_url)

        # skip logos/icons
        alt = (img.get("alt") or "").lower()
        cls = " ".join(img.get("class", [])).lower()
        if any(x in alt for x in ["logo", "icon"]) or any(
            x in cls for x in ["logo", "icon", "avatar"]
        ):
            continue

        candidates.append(src)

    return candidates[0] if candidates else ""


def extract_all_images(soup: BeautifulSoup, base_url: str, max_images: int = 20) -> List[str]:
    urls = []
    seen = set()
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or ""
        src = src.strip()
        if not src:
            continue
        src = _absolute(src, base_url)
        if src in seen:
            continue
        seen.add(src)
        urls.append(src)
        if len(urls) >= max_images:
            break
    return urls


# ============================
# TITLE EXTRACTION
# ============================

def extract_title(soup: BeautifulSoup) -> str:
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip()

    if soup.title and soup.title.string:
        return soup.title.string.strip()

    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)

    return ""


# ============================
# TEXT + SUMMARY EXTRACTION
# ============================

def extract_main_text(soup: BeautifulSoup, max_summary_len: int = 260) -> (str, str):
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    container = soup.find("article") or soup.find("main") or soup.body
    if not container:
        return "", ""

    for tag in container.find_all(["nav", "footer", "aside"]):
        tag.decompose()

    paragraphs = []
    for p in container.find_all("p"):
        text = p.get_text(" ", strip=True)
        if not text:
            continue
        if len(text) < 25:
            continue
        paragraphs.append(text)

    full_text = "\n\n".join(paragraphs)
    if not full_text:
        return "", ""

    summary = paragraphs[0]
    if len(summary) > max_summary_len:
        summary = summary[:max_summary_len].rsplit(" ", 1)[0] + "…"

    return summary, full_text


# ============================
# MAIN EXTRACTOR
# ============================

def extract_article_content(url: str) -> Optional[ArticleContent]:
    html = fetch_html(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    title = extract_title(soup)
    main_image = extract_main_image(soup, url)
    all_images = extract_all_images(soup, url)
    summary, full_text = extract_main_text(soup)

    return ArticleContent(
        url=url,
        title=title,
        main_image=main_image,
        all_images=all_images,
        summary=summary,
        full_text=full_text,
    )


# ============================
# TEST (optional)
# ============================

if __name__ == "__main__":
    test_url = "https://www.pokebeach.com/"  # replace with a real article URL
    content = extract_article_content(test_url)
    if content:
        print("=== ARTICLE CONTENT ===")
        print(asdict(content))
    else:
        print("Failed to extract content.")

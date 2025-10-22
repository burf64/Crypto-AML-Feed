# feedgen.py – multi-source RSS + scraper
from requests_html import HTMLSession
from bs4 import BeautifulSoup
import requests
import feedparser
from datetime import datetime
from email.utils import format_datetime
import xml.sax.saxutils as saxutils

OUT = "feed.xml"
MAX_ITEMS = 60

# --- dynamic sources (need scraping)
TRM_BLOG = "https://www.trmlabs.com/resources/blog"

# --- regular RSS feeds (easy)
SOURCES = {
    "Chainalysis": "https://www.chainalysis.com/blog/feed/",
    "Elliptic": "https://www.elliptic.co/blog/rss.xml",
    "Money Laundering News": "https://www.moneylaunderingnews.com/feed/",
    "ICIJ": "https://www.icij.org/feed/",
    "OFAC": "https://ofac.treasury.gov/rss/press-releases.xml",
}

def fetch_trm():
    session = HTMLSession()
    r = session.get(TRM_BLOG)
    r.html.render(timeout=25, sleep=3)
    soup = BeautifulSoup(r.html.html, "html.parser")
    items = []
    for a in soup.select("a[href^='/resources/blog/']"):
        href = "https://www.trmlabs.com" + a["href"] if a["href"].startswith("/") else a["href"]
        title_el = a.find(["h2","h3"])
        title = title_el.get_text(strip=True) if title_el else a.get_text(strip=True)
        if not title or len(title) < 5:
            continue
        desc_el = a.find_next("p")
        desc = desc_el.get_text(strip=True) if desc_el else ""
        items.append({
            "title": title.strip() + " (TRM Labs)",
            "link": href.strip(),
            "desc": desc.strip(),
            "date": datetime.utcnow()
        })
    return items

def fetch_rss(label, url):
    d = feedparser.parse(url)
    items = []
    for e in d.entries:
        title = e.title + f" ({label})"
        link = e.link
        desc = getattr(e, "summary", "")
        date = None
        if hasattr(e, "published_parsed"):
            try:
                date = datetime(*e.published_parsed[:6])
            except Exception:
                pass
        items.append({
            "title": title, "link": link, "desc": desc, "date": date or datetime.utcnow()
        })
    return items

def make_rss(items):
    items = sorted(items, key=lambda x: x["date"], reverse=True)[:MAX_ITEMS]
    now = format_datetime(datetime.utcnow())
    xml = [
        '<?xml version="1.0" encoding="utf-8"?>',
        "<rss version='2.0'>",
        "<channel>",
        "<title>Crypto-Sanctions / AML Feed</title>",
        "<link>https://github.com/</link>",
        "<description>Merged automated feed: TRM Labs + Chainalysis + Elliptic + AML sources</description>",
        f"<lastBuildDate>{now}</lastBuildDate>",
    ]
    for it in items:
        title = saxutils.escape(it["title"])
        link = saxutils.escape(it["link"])
        desc = saxutils.escape(it["desc"])
        pub = format_datetime(it["date"])
        xml.extend([
            "<item>",
            f"<title>{title}</title>",
            f"<link>{link}</link>",
            f"<description>{desc}</description>",
            f"<pubDate>{pub}</pubDate>",
            f"<guid isPermaLink='true'>{link}</guid>",
            "</item>",
        ])
    xml.append("</channel>")
    xml.append("</rss>")
    return "\n".join(xml)

def main():
    all_items = []
    try:
        all_items.extend(fetch_trm())
    except Exception as e:
        print("TRM Labs fetch failed:", e)
    for label, url in SOURCES.items():
        try:
            all_items.extend(fetch_rss(label, url))
        except Exception as e:
            print(f"{label} failed:", e)
    rss = make_rss(all_items)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(rss)
    print(f"Wrote {OUT} with {len(all_items)} total items")

if __name__ == "__main__":
    main()

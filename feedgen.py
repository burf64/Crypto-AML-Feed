# feedgen.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from email.utils import format_datetime
import xml.sax.saxutils as saxutils
import os

BASE = "https://www.trmlabs.com"
BLOG = "https://www.trmlabs.com/resources/blog"
OUT = "feed.xml"
MAX_ITEMS = 30

def fetch():
    r = requests.get(BLOG, timeout=20)
    r.raise_for_status()
    return r.text

def parse(html):
    soup = BeautifulSoup(html, "html.parser")
    items = []

    # TRM's blog lists posts — try find <article> or post card containers
    # We try several selectors to be robust.
    candidates = soup.select("article") or soup.select(".post") or soup.select(".blog-card") or soup.select(".resource-card") or soup.select(".col")
    seen = set()
    for el in candidates:
        # find link
        a = el.find("a", href=True)
        if not a:
            continue
        href = a["href"]
        # some hrefs are relative; make absolute
        if href.startswith("/"):
            href = BASE + href
        if href in seen:
            continue
        seen.add(href)
        # title
        title = a.get_text(strip=True) or (el.find(["h2","h3"]) and el.find(["h2","h3"]).get_text(strip=True)) or "TRM Lab post"
        # excerpt/desc
        p = el.find("p")
        desc = p.get_text(strip=True) if p else ""
        # try to find date element
        date_el = el.find(class_="date") or el.find("time") or el.find("span", {"class":"meta"})
        pubdate = None
        if date_el:
            txt = date_el.get("datetime") or date_el.get_text(strip=True)
            try:
                pubdate = datetime.fromisoformat(txt.strip())
            except Exception:
                try:
                    pubdate = datetime.strptime(txt.strip(), "%B %d, %Y")
                except Exception:
                    pubdate = None
        items.append({"title": title, "link": href, "desc": desc, "date": pubdate})
        if len(items) >= MAX_ITEMS:
            break
    # fallback: also parse main listing links if previous selector missed
    if not items:
        for a in soup.select("a[href]"):
            href = a["href"]
            if "/post/" in href or "/resources/" in href:
                if href.startswith("/"):
                    href = BASE + href
                title = a.get_text(strip=True) or href
                items.append({"title": title, "link": href, "desc": "", "date": None})
                if len(items) >= MAX_ITEMS:
                    break
    return items

def make_rss(items):
    now = format_datetime(datetime.utcnow())
    channel_title = "TRM Labs blog (auto RSS)"
    channel_link = BLOG
    channel_desc = "Automated RSS feed for TRM Labs blog (sanctions / AML related posts)."
    xml = []
    xml.append('<?xml version="1.0" encoding="utf-8"?>')
    xml.append("<rss version='2.0'>")
    xml.append("<channel>")
    xml.append(f"<title>{saxutils.escape(channel_title)}</title>")
    xml.append(f"<link>{saxutils.escape(channel_link)}</link>")
    xml.append(f"<description>{saxutils.escape(channel_desc)}</description>")
    xml.append(f"<lastBuildDate>{now}</lastBuildDate>")

    for it in items:
        title = saxutils.escape(it["title"])
        link = saxutils.escape(it["link"])
        desc = saxutils.escape(it["desc"] or "")
        pub = it["date"]
        pubstr = format_datetime(pub) if pub else format_datetime(datetime.utcnow())
        xml.append("<item>")
        xml.append(f"<title>{title}</title>")
        xml.append(f"<link>{link}</link>")
        xml.append(f"<description>{desc}</description>")
        xml.append(f"<pubDate>{pubstr}</pubDate>")
        xml.append(f"<guid isPermaLink='true'>{link}</guid>")
        xml.append("</item>")

    xml.append("</channel>")
    xml.append("</rss>")
    return "\n".join(xml)

def main():
    html = fetch()
    items = parse(html)
    rss = make_rss(items)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(rss)
    print(f"Wrote {OUT} with {len(items)} items")

if __name__ == "__main__":
    main()

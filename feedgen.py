# feedgen.py
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from email.utils import format_datetime
import xml.sax.saxutils as saxutils

BASE = "https://www.trmlabs.com"
BLOG = "https://www.trmlabs.com/resources/blog"
OUT = "feed.xml"
MAX_ITEMS = 30


def fetch():
    """Download the TRM Labs blog listing page."""
    r = requests.get(BLOG, timeout=20)
    r.raise_for_status()
    return r.text


def parse(html):
    """Extract blog post links, titles, and descriptions."""
    soup = BeautifulSoup(html, "html.parser")
    items = []

    # TRM Labs' blog uses <a class="resource-card"> for each article card
    cards = soup.select("a.resource-card[href]")
    for card in cards:
        href = card["href"]
        if href.startswith("/"):
            href = BASE + href

        # only include true blog posts (ignore webinars, guides, etc.)
        if not href.startswith(f"{BASE}/resources/blog/"):
            continue

        # title and description
        title_el = card.select_one("h2, h3, .card-title")
        title = title_el.get_text(strip=True) if title_el else card.get_text(strip=True)
        if not title:
            continue

        desc_el = card.select_one("p, .card-description, .text-sm")
        desc = desc_el.get_text(strip=True) if desc_el else ""

        items.append(
            {
                "title": title.strip(),
                "link": href.strip(),
                "desc": desc.strip(),
                "date": None,
            }
        )

    # deduplicate by link
    seen, cleaned = set(), []
    for i in items:
        if i["link"] not in seen:
            seen.add(i["link"])
            cleaned.append(i)
    return cleaned[:MAX_ITEMS]


def make_rss(items):
    """Build RSS XML string."""
    now = format_datetime(datetime.utcnow())
    channel_title = "TRM Labs Blog (auto RSS)"
    channel_link = BLOG
    channel_desc = (
        "Automated RSS feed for TRM Labs blog (sanctions / AML / crypto compliance)."
    )

    xml = [
        '<?xml version="1.0" encoding="utf-8"?>',
        "<rss version='2.0'>",
        "<channel>",
        f"<title>{saxutils.escape(channel_title)}</title>",
        f"<link>{saxutils.escape(channel_link)}</link>",
        f"<description>{saxutils.escape(channel_desc)}</description>",
        f"<lastBuildDate>{now}</lastBuildDate>",
    ]

    for it in items:
        title = saxutils.escape(it["title"] + " (TRM Labs)")
        link = saxutils.escape(it["link"])
        desc = saxutils.escape(it["desc"] or "")
        pub = it["date"] or datetime.utcnow()
        pubstr = format_datetime(pub)
        xml.extend(
            [
                "<item>",
                f"<title>{title}</title>",
                f"<link>{link}</link>",
                f"<description>{desc}</description>",
                f"<pubDate>{pubstr}</pubDate>",
                f"<guid isPermaLink='true'>{link}</guid>",
                "</item>",
            ]
        )

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

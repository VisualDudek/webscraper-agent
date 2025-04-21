#!/usr/bin/env python
"""
Scrape every 'main news' headline from https://lowcygier.pl
Falls back gracefully if the site blocks anonymous bots.
"""

from __future__ import annotations
from datetime import datetime
import json
import re
import requests
import cloudscraper
import feedparser
from bs4 import (
    BeautifulSoup,
)  # docs: https://www.crummy.com/software/BeautifulSoup/bs4/doc/

ROOT = "https://lowcygier.pl"
WP_API = f"{ROOT}/wp-json/wp/v2/posts"
WP_PARAMS = {
    "per_page": 100,  # max allowed by WP REST API v2
    "_fields": "link,title,excerpt,date",
}
RSS_FEED = f"{ROOT}/feed/"
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def session() -> requests.Session:
    """Return a Cloudflare‑aware session with modern headers."""
    s = cloudscraper.create_scraper(browser={"custom": "Scraper 1.0"})
    s.headers.update(
        {"User-Agent": UA, "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8"}
    )
    return s


def wp_rest(s: requests.Session):
    r = s.get(WP_API, params=WP_PARAMS, timeout=10)
    r.raise_for_status()
    return [
        {
            "title": item["title"]["rendered"],
            "url": item["link"],
            "excerpt": BeautifulSoup(
                item["excerpt"]["rendered"], "html.parser"
            ).get_text(" ", strip=True),
            "date": item["date"],
        }
        for item in r.json()
    ]


def rss(s: requests.Session):
    d = feedparser.parse(RSS_FEED, request_headers={"User-Agent": UA})
    return [
        {
            "title": entry.title,
            "url": entry.link,
            "excerpt": (
                BeautifulSoup(entry.summary, "html.parser").get_text(" ", strip=True)
                if "summary" in entry
                else ""
            ),
            "date": (
                datetime(*entry.published_parsed[:6]).isoformat()
                if "published_parsed" in entry
                else ""
            ),
        }
        for entry in d.entries
    ]


ARTICLE_SEL = "article, div.post, div[class*='entry']"


def html_scrape(s: requests.Session):
    r = s.get(ROOT, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for art in soup.select(ARTICLE_SEL):
        h = art.find(re.compile("^h[12]$"))
        a = h and h.find("a", href=True)
        if not a:
            continue
        excerpt_tag = art.find("div", class_=re.compile("excerpt|summary")) or art.find(
            "p"
        )
        results.append(
            {
                "title": a.get_text(strip=True),
                "url": a["href"],
                "excerpt": excerpt_tag.get_text(" ", strip=True) if excerpt_tag else "",
                "date": "",
            }
        )
    return results


def get_news(limit: int | None = None):
    s = session()
    # for fn in (wp_rest, rss, html_scrape):
    for fn in [rss]:
        try:
            data = fn(s)
            if data:
                return data[:limit] if limit else data
        except Exception:
            continue
    return []


def get_news_and_save(filepath: str, limit: int | None = None):
    """
    Get news and save the results to a JSON file.

    Args:
        filepath: Path where the JSON file will be saved
        limit: Optional limit for the number of news items

    Returns:
        The news data that was saved
    """
    news = get_news(limit)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(news, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(news)} news items to {filepath}")
    return news


# CLI usage ---------------------------------------------------------------
if __name__ == "__main__":
    # news = get_news()
    # print(json.dumps(news, indent=2, ensure_ascii=False))

    get_news_and_save("output.json")

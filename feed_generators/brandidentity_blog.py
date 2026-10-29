"""Generate a feed using the public API behind The Brand Identity's features page."""

import logging
from datetime import datetime, timezone
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from utils import get_feeds_dir, setup_feed_links, sort_posts_for_feed

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

SITE_URL = "https://the-brandidentity.com"
BLOG_URL = f"{SITE_URL}/features"
FEED_NAME = "brandidentity"
FEED_FILE = get_feeds_dir() / f"feed_{FEED_NAME}.xml"
POST_LIMIT = 20
QUERY = """
query ($limit: Int) {
  entries(section: "articles", limit: $limit, orderBy: "postDate DESC") {
    title
    slug
    categoryHandle
    postDate
    authorName
    content
  }
}
"""


def fetch_recent_posts():
    """Fetch the latest articles from the public API used by the features page."""
    response = requests.post(
        f"{SITE_URL}/api",
        headers={"User-Agent": "Mozilla/5.0 (compatible; RSSFeedGenerator)"},
        json={"query": QUERY, "variables": {"limit": POST_LIMIT}},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise ValueError(f"Article API returned errors: {payload['errors']}")
    posts = parse_posts(payload["data"]["entries"])
    if not posts:
        raise ValueError("No articles found; preserving the existing feed")
    return posts


def text_content(node):
    """Extract text from the site's rich text nodes without losing inline spaces."""
    if isinstance(node, list):
        return "".join(text_content(child) for child in node)
    if isinstance(node, dict):
        return node.get("text", "") + text_content(node.get("content", []))
    return ""


def article_summary(content):
    """Use the first prose block as the RSS description."""
    if isinstance(content, str):
        return BeautifulSoup(content, "html.parser").get_text(" ", strip=True)
    for block in content or []:
        if block.get("type") in {"heading", "paragraph"}:
            text = text_content(block).strip()
            if text:
                return text
    return ""


def parse_posts(entries):
    """Normalize article URLs and real publication dates for RSS."""
    posts = []
    for entry in entries:
        date = datetime.fromisoformat(entry["postDate"])
        if date.tzinfo is None:
            raise ValueError(f"Publication date has no timezone: {entry['postDate']}")
        posts.append(
            {
                "title": entry["title"],
                "link": f"{SITE_URL}/{entry['categoryHandle']}/{quote(entry['slug'], safe='')}",
                "date": date.astimezone(timezone.utc).isoformat(),
                "author": entry.get("authorName") or "The Brand Identity",
                "category": entry["categoryHandle"],
                "description": article_summary(entry.get("content")),
            }
        )
    return posts


def generate_rss_feed(posts):
    fg = FeedGenerator()
    fg.load_extension("dc")
    fg.title("The Brand Identity – Features")
    fg.description("Graphic and brand design projects, interviews, and insights.")
    fg.language("en")
    setup_feed_links(fg, blog_url=BLOG_URL, feed_name=FEED_NAME)
    for post in sort_posts_for_feed(posts):
        entry = fg.add_entry()
        entry.id(post["link"])
        entry.title(post["title"])
        entry.link(href=post["link"])
        entry.published(datetime.fromisoformat(post["date"]))
        entry.description(post["description"])
        entry.dc.dc_creator(post["author"])
        if post["category"]:
            entry.category(term=post["category"])
    return fg


def main():
    posts = fetch_recent_posts()
    feed = generate_rss_feed(posts)
    feed.rss_file(str(FEED_FILE), pretty=True)
    logger.info("Saved %s posts to %s", len(posts), FEED_FILE)


if __name__ == "__main__":
    main()

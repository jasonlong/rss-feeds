import argparse
import json
import logging
from datetime import datetime

import pytz
import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from utils import (get_cache_dir, get_feeds_dir, setup_feed_links,
                   sort_posts_for_feed)

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BLOG_URL = "https://www.creativeapplications.net/"
FEED_NAME = "creativeapplications"
CACHE_FILE = get_cache_dir() / "creativeapplications_posts.json"


def fetch_blog_content(url):
    """Fetch blog content from the given URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.text


def parse_blog_posts(html_content):
    """Parse the blog HTML content and extract post information."""
    soup = BeautifulSoup(html_content, "html.parser")
    posts = []

    items = soup.select("div.griditem")
    for item in items:
        # Get link from the first anchor tag (image link)
        link_tag = item.select_one("div.gridmedia a")
        if not link_tag or not link_tag.get("href"):
            continue
        link = link_tag["href"]

        # Get title
        title_tag = item.select_one("div.gridtitle")
        title = title_tag.get_text(strip=True) if title_tag else ""
        if not title:
            continue

        # Get excerpt
        excerpt_tag = item.select_one("div.gridexcerpt")
        excerpt = excerpt_tag.get_text(strip=True) if excerpt_tag else None

        # Get date from metadata (D label followed by date)
        pub_date = None
        meta = item.select_one("div.gridmeta")
        if meta:
            meta_items = meta.select("li")
            for li in meta_items:
                spans = li.select("span")
                if len(spans) >= 2 and spans[0].get_text(strip=True) == "D":
                    date_str = spans[1].get_text(strip=True)
                    try:
                        pub_date = datetime.strptime(date_str, "%d/%m/%Y")
                        pub_date = pub_date.replace(tzinfo=pytz.UTC)
                    except ValueError:
                        logger.warning(f"Could not parse date: {date_str}")

        # Get author from metadata (A label)
        author = None
        if meta:
            meta_items = meta.select("li")
            for li in meta_items:
                spans = li.select("span")
                if len(spans) >= 2 and spans[0].get_text(strip=True) == "A":
                    author = spans[1].get_text(strip=True).lstrip("@")

        posts.append(
            {
                "title": title,
                "date": pub_date.isoformat() if pub_date else None,
                "link": link,
                "description": excerpt,
                "author": author,
            }
        )

    return posts


def get_next_page_url(html_content):
    """Extract the next page URL from pagination."""
    soup = BeautifulSoup(html_content, "html.parser")
    next_link = soup.select_one("a.next.page-numbers")
    if next_link:
        return next_link.get("href")
    return None


def fetch_all_pages(max_pages=None):
    """Fetch posts from all pages."""
    all_posts = []
    url = BLOG_URL
    page = 1

    while url:
        if max_pages and page > max_pages:
            break

        logger.info(f"Fetching page {page}: {url}")
        html = fetch_blog_content(url)
        posts = parse_blog_posts(html)

        if not posts:
            break

        all_posts.extend(posts)
        url = get_next_page_url(html)
        page += 1

    logger.info(f"Fetched {len(all_posts)} posts from {page - 1} pages")
    return all_posts


def load_cache():
    """Load cached posts from disk."""
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    return []


def save_cache(posts):
    """Save posts to cache file."""
    with open(CACHE_FILE, "w") as f:
        json.dump(posts, f, indent=2)
    logger.info(f"Saved {len(posts)} posts to cache")


def merge_posts(new_posts, cached_posts):
    """Merge new posts with cached posts, deduplicating by URL."""
    seen = {}
    for post in cached_posts:
        seen[post["link"]] = post
    for post in new_posts:
        seen[post["link"]] = post
    merged = list(seen.values())
    merged.sort(key=lambda x: x.get("date") or "", reverse=True)
    return merged


def generate_rss_feed(posts):
    """Generate RSS feed from blog posts."""
    fg = FeedGenerator()
    fg.title("Creative Applications Network")
    fg.description("Technology, Society, and Critical Making")
    fg.language("en")
    fg.author({"name": "Creative Applications Network"})

    setup_feed_links(fg, blog_url=BLOG_URL, feed_name=FEED_NAME)

    sorted_posts = sort_posts_for_feed(posts)

    for post in sorted_posts:
        fe = fg.add_entry()
        fe.title(post["title"])
        fe.link(href=post["link"])
        fe.id(post["link"])

        if post.get("date"):
            pub_date = datetime.fromisoformat(post["date"])
            fe.published(pub_date)

        if post.get("description"):
            fe.description(post["description"])

        if post.get("author"):
            fe.author({"name": post["author"]})

    logger.info("Successfully generated RSS feed")
    return fg


def save_rss_feed(feed_generator):
    """Save the RSS feed to a file in the feeds directory."""
    feeds_dir = get_feeds_dir()
    output_filename = feeds_dir / f"feed_{FEED_NAME}.xml"
    feed_generator.rss_file(str(output_filename), pretty=True)
    logger.info(f"Successfully saved RSS feed to {output_filename}")
    return output_filename


def main():
    """Main function to generate RSS feed for Creative Applications Network."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--full", action="store_true", help="Fetch all pages (not just page 1)"
    )
    args = parser.parse_args()

    cached_posts = load_cache()

    if args.full or not cached_posts:
        new_posts = fetch_all_pages(max_pages=5)
    else:
        logger.info("Incremental mode: fetching page 1 only")
        html = fetch_blog_content(BLOG_URL)
        new_posts = parse_blog_posts(html)

    all_posts = merge_posts(new_posts, cached_posts)
    save_cache(all_posts)

    feed = generate_rss_feed(all_posts)
    save_rss_feed(feed)
    return True


if __name__ == "__main__":
    main()

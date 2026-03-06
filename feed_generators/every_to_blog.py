import argparse
import json
import logging
import re
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

BLOG_URL = "https://every.to/"
FEED_NAME = "every_to"
CACHE_FILE = get_cache_dir() / "every_to_posts.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def fetch_page(url):
    """Fetch a page and return its HTML."""
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    return response.text


def parse_homepage_articles(html):
    """Extract article URLs, titles, and authors from the homepage."""
    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    articles = []

    for h3 in soup.find_all("h3"):
        a = h3.find_parent("a")
        if not a:
            continue
        href = a.get("href", "")

        # Only internal article paths (skip external links, section pages, podcasts)
        if not href.startswith("/"):
            continue
        if href.startswith(("/c/", "/studio", "/columnists", "/podcast")):
            continue
        # Skip section index pages (single path segment, no sub-path)
        if re.match(r"^/[^/]+$", href) and not href.startswith("/p/"):
            continue
        if href in seen:
            continue
        seen.add(href)

        title = re.sub(r"\s+", " ", h3.get_text(" ", strip=True))
        if not title:
            continue

        # Find author from nearby /@handle link
        author = ""
        container = a.parent
        if container:
            for author_link in container.find_all("a", href=re.compile(r"^/@")):
                author = author_link.get_text(strip=True)
                break

        articles.append(
            {
                "title": title,
                "link": f"https://every.to{href}",
                "author": author,
            }
        )

    return articles


def fetch_article_metadata(url):
    """Fetch an article page and extract title, publish date, and description."""
    try:
        html = fetch_page(url)
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None, None, None

    soup = BeautifulSoup(html, "html.parser")

    # Get clean title from og:title (homepage titles have decorative spans)
    title = None
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()

    # Get publish date from meta tag
    pub_date = None
    og_date = soup.find("meta", attrs={"property": "article:published_time"})
    if og_date and og_date.get("content"):
        try:
            date_str = og_date["content"]
            if "T" in date_str:
                pub_date = datetime.fromisoformat(date_str)
            else:
                pub_date = datetime.strptime(date_str, "%Y-%m-%d")
                pub_date = pub_date.replace(tzinfo=pytz.UTC)
        except ValueError:
            logger.warning(f"Could not parse date: {og_date['content']}")

    # Get description from meta tag
    description = None
    og_desc = soup.find("meta", attrs={"property": "og:description"})
    if og_desc and og_desc.get("content"):
        description = og_desc["content"]

    return title, pub_date, description


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
    fg.title("Every")
    fg.description(
        "The only subscription you need to stay at the edge of AI. Ideas, apps, and training."
    )
    fg.language("en")
    fg.author({"name": "Every"})

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
    """Main function to generate RSS feed for Every."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--full",
        action="store_true",
        help="Re-fetch metadata for all articles (not just new ones)",
    )
    args = parser.parse_args()

    cached_posts = load_cache()
    cached_urls = {p["link"] for p in cached_posts}

    # Scrape homepage for article links
    logger.info("Fetching homepage for article links")
    html = fetch_page(BLOG_URL)
    homepage_articles = parse_homepage_articles(html)
    logger.info(f"Found {len(homepage_articles)} articles on homepage")

    # Determine which articles need metadata fetched
    if args.full or not cached_posts:
        to_fetch = homepage_articles
    else:
        to_fetch = [a for a in homepage_articles if a["link"] not in cached_urls]
        logger.info(
            f"Incremental mode: {len(to_fetch)} new articles to fetch metadata for"
        )

    # Fetch metadata for each article
    new_posts = []
    for article in to_fetch:
        logger.info(f"Fetching metadata: {article['link']}")
        title, pub_date, description = fetch_article_metadata(article["link"])

        post = {
            "title": title or article["title"],
            "link": article["link"],
            "author": article.get("author", ""),
            "date": pub_date.isoformat() if pub_date else None,
            "description": description,
        }
        new_posts.append(post)

    all_posts = merge_posts(new_posts, cached_posts)
    save_cache(all_posts)

    feed = generate_rss_feed(all_posts)
    save_rss_feed(feed)
    return True


if __name__ == "__main__":
    main()

import json
import logging
import re
from datetime import datetime

import pytz
import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from utils import get_feeds_dir, setup_feed_links, sort_posts_for_feed

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def fetch_blog_content(url):
    """Fetch blog content from the given URL."""
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    return response.text


def parse_date_from_permalink(link):
    """Parse YYYY/MM/DD date segments from Athletic article permalinks."""
    match = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", link)
    if not match:
        return None

    try:
        parsed = datetime(
            int(match.group(1)), int(match.group(2)), int(match.group(3))
        ).replace(tzinfo=pytz.UTC)
        return parsed.isoformat()
    except ValueError:
        logger.warning(f"Could not parse permalink date from: {link}")
        return None


def extract_author_name(author_obj):
    """Build author name from Athletic author object."""
    if not isinstance(author_obj, dict):
        return None

    first = (author_obj.get("first_name") or "").strip()
    last = (author_obj.get("last_name") or "").strip()
    full = f"{first} {last}".strip()
    return full or None


def extract_article_posts(next_data):
    """Walk __NEXT_DATA__ JSON and extract article consumables."""
    posts = []
    stack = [next_data]

    while stack:
        current = stack.pop()

        if isinstance(current, dict):
            if (
                current.get("__typename") == "ArticleConsumable"
                and current.get("title")
                and current.get("permalink")
            ):
                link = current["permalink"]
                if link.startswith("/"):
                    link = f"https://www.nytimes.com{link}"

                excerpt = current.get("excerpt")
                if excerpt:
                    excerpt = BeautifulSoup(excerpt, "html.parser").get_text(
                        " ", strip=True
                    )

                posts.append(
                    {
                        "title": current["title"].strip(),
                        "link": link,
                        "date": parse_date_from_permalink(link),
                        "description": excerpt,
                        "author": extract_author_name(current.get("author")),
                    }
                )

            for value in current.values():
                if isinstance(value, (dict, list)):
                    stack.append(value)

        elif isinstance(current, list):
            for item in current:
                if isinstance(item, (dict, list)):
                    stack.append(item)

    return posts


def parse_blog_posts(html_content):
    """Parse Athletic page HTML and extract article metadata."""
    soup = BeautifulSoup(html_content, "html.parser")
    next_data_script = soup.find("script", id="__NEXT_DATA__")

    if not next_data_script or not next_data_script.string:
        logger.warning("Could not locate __NEXT_DATA__ script")
        return []

    try:
        next_data = json.loads(next_data_script.string)
    except json.JSONDecodeError as err:
        logger.warning(f"Could not parse __NEXT_DATA__ JSON: {err}")
        return []

    raw_posts = extract_article_posts(next_data)

    # Deduplicate by permalink while preserving latest seen article payload.
    deduped = {}
    for post in raw_posts:
        deduped[post["link"]] = post

    return list(deduped.values())


def generate_rss_feed(posts, feed_title, feed_description, blog_url, feed_name):
    """Generate RSS feed from article posts."""
    fg = FeedGenerator()
    fg.title(feed_title)
    fg.description(feed_description)
    fg.language("en")
    fg.author({"name": "The Athletic"})

    setup_feed_links(fg, blog_url=blog_url, feed_name=feed_name)

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


def save_rss_feed(feed_generator, feed_name):
    """Save the RSS feed to a file in the feeds directory."""
    feeds_dir = get_feeds_dir()
    output_filename = feeds_dir / f"feed_{feed_name}.xml"
    feed_generator.rss_file(str(output_filename), pretty=True)
    logger.info(f"Successfully saved RSS feed to {output_filename}")
    return output_filename

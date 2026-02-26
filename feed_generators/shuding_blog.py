import logging
from datetime import datetime

import pytz
import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from utils import get_feeds_dir, setup_feed_links

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BLOG_URL = "https://shud.in/thoughts"
FEED_NAME = "shuding"


def fetch_blog_content(url):
    """Fetch blog content from the given URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.text


def parse_blog_posts(html_content):
    """Parse the blog HTML content and extract post information."""
    soup = BeautifulSoup(html_content, "html.parser")
    posts = []

    links = soup.select('li a[href*="/thoughts/"]')
    for a in links:
        href = a.get("href", "")
        if not href.startswith("/thoughts/"):
            continue

        link = f"https://shud.in{href}"

        title_span = a.select_one("span")
        title = title_span.get_text(strip=True) if title_span else ""
        if not title:
            continue

        time_tag = a.select_one("time")
        pub_date = None
        if time_tag:
            date_str = time_tag.get_text(strip=True)
            try:
                pub_date = datetime.strptime(date_str, "%Y.%m.%d")
                pub_date = pub_date.replace(tzinfo=pytz.UTC)
            except ValueError:
                logger.warning(f"Could not parse date: {date_str}")

        posts.append(
            {
                "title": title,
                "date": pub_date.isoformat() if pub_date else None,
                "link": link,
            }
        )

    return posts


def generate_rss_feed(posts):
    """Generate RSS feed from blog posts."""
    fg = FeedGenerator()
    fg.title("Shu Ding – Thoughts")
    fg.description("Thoughts by Shu Ding")
    fg.language("en")
    fg.author({"name": "Shu Ding"})

    setup_feed_links(fg, blog_url=BLOG_URL, feed_name=FEED_NAME)

    for post in posts:
        fe = fg.add_entry()
        fe.title(post["title"])
        fe.link(href=post["link"])
        fe.id(post["link"])

        if post.get("date"):
            pub_date = datetime.fromisoformat(post["date"])
            fe.published(pub_date)

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
    """Main function to generate RSS feed for Shu Ding's blog."""
    html = fetch_blog_content(BLOG_URL)
    posts = parse_blog_posts(html)
    logger.info(f"Found {len(posts)} posts")

    feed = generate_rss_feed(posts)
    save_rss_feed(feed)
    return True


if __name__ == "__main__":
    main()

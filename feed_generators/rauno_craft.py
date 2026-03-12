import logging
from datetime import datetime

import pytz
import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from utils import get_feeds_dir, setup_feed_links, sort_posts_for_feed

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BLOG_URL = "https://rauno.me/craft"
FEED_NAME = "rauno_craft"


def fetch_blog_content(url):
    """Fetch blog content from the given URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.text


def parse_blog_posts(html_content):
    """Parse the blog HTML content and extract craft entries."""
    soup = BeautifulSoup(html_content, "html.parser")
    posts = []

    grid = soup.find("div", class_="grid")
    if not grid:
        logger.warning("Could not find grid container")
        return posts

    columns = grid.find_all("div", class_="column")
    for col in columns:
        children = col.find_all(recursive=False)
        for child in children:
            if "c-dFdHYY" not in child.get("class", []):
                continue

            # Extract title and date from leaf text divs
            text_divs = []
            for d in child.find_all("div", recursive=True):
                text = d.get_text(strip=True)
                if text and not d.find("div"):
                    text_divs.append(text)

            if not text_divs:
                continue

            title = text_divs[0]
            date_str = text_divs[1] if len(text_divs) > 1 else None

            # Build link
            href = child.get("href", "") if child.name == "a" else ""
            if href and href.startswith("/"):
                link = f"https://rauno.me{href}"
            elif href:
                link = href
            else:
                link = BLOG_URL

            # Parse date (format: "Month YYYY")
            pub_date = None
            if date_str:
                try:
                    pub_date = datetime.strptime(date_str, "%B %Y")
                    pub_date = pub_date.replace(day=1, tzinfo=pytz.UTC)
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
    """Generate RSS feed from craft entries."""
    fg = FeedGenerator()
    fg.title("Rauno – Craft")
    fg.description("Craft by Rauno Freiberg")
    fg.language("en")
    fg.author({"name": "Rauno Freiberg"})

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
    """Main function to generate RSS feed for Rauno's craft page."""
    html = fetch_blog_content(BLOG_URL)
    posts = parse_blog_posts(html)
    logger.info(f"Found {len(posts)} entries")

    posts = sort_posts_for_feed(posts)
    feed = generate_rss_feed(posts)
    save_rss_feed(feed)
    return True


if __name__ == "__main__":
    main()

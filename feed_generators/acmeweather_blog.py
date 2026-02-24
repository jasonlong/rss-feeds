import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
from feedgen.feed import FeedGenerator
import logging
from pathlib import Path

from utils import get_feeds_dir, setup_feed_links

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BLOG_URL = "https://acmeweather.com/blog"
FEED_NAME = "acmeweather"


def fetch_blog_content(url):
    """Fetch blog content from the given URL."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"Error fetching blog content: {str(e)}")
        raise


def parse_blog_posts(html_content):
    """Parse the blog HTML content and extract post information.

    Currently the /blog page renders posts inline (no index page).
    We extract the title from <h1>, the date from <p class="byline">,
    and construct the post URL from the slug.
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        blog_posts = []

        # Find all posts on the page. Currently there's one post rendered inline.
        # Each post has an <h1> title and a <p class="byline"> with author and date.
        titles = soup.find_all("h1")

        for title_tag in titles:
            title = title_tag.get_text(strip=True)
            if not title:
                continue

            # Look for the byline that follows the title
            byline = title_tag.find_next_sibling("p", class_="byline")
            if not byline:
                continue

            # Extract date from byline text (e.g. "Adam Grossman February 16, 2026")
            byline_text = byline.get_text(strip=True)
            pub_date = None

            # Try common date formats found in bylines
            date_formats = ["%B %d, %Y", "%b %d, %Y"]
            for fmt in date_formats:
                # Search for a date pattern at the end of the byline
                import re
                # Match month name followed by day and year
                pattern = r"([A-Z][a-z]+ \d{1,2},? \d{4})"
                match = re.search(pattern, byline_text)
                if match:
                    try:
                        pub_date = datetime.strptime(match.group(1), fmt)
                        pub_date = pub_date.replace(tzinfo=pytz.UTC)
                        break
                    except ValueError:
                        continue

            if not pub_date:
                logger.warning(f"Could not parse date from byline: {byline_text}")
                continue

            # Derive the post slug from the title
            slug = title.lower().replace("\xa0", " ")
            slug = re.sub(r"[^a-z0-9\s-]", "", slug)
            slug = re.sub(r"\s+", "-", slug.strip())
            link = f"https://acmeweather.com/blog/{slug}"

            # Extract description from the first paragraph of the post content
            first_section = title_tag.find_next("section")
            description = ""
            if first_section:
                first_p = first_section.find("p")
                if first_p:
                    description = first_p.get_text(strip=True)

            blog_posts.append({
                "title": title,
                "date": pub_date,
                "description": description,
                "link": link,
            })

        logger.info(f"Successfully parsed {len(blog_posts)} blog posts")
        return blog_posts

    except Exception as e:
        logger.error(f"Error parsing HTML content: {str(e)}")
        raise


def generate_rss_feed(blog_posts):
    """Generate RSS feed from blog posts."""
    try:
        fg = FeedGenerator()
        fg.title("Acme Weather Blog")
        fg.description("Updates from the Acme Weather team")
        fg.language("en")

        fg.author({"name": "Acme Weather"})
        fg.subtitle("Latest updates from Acme Weather")

        setup_feed_links(fg, blog_url=BLOG_URL, feed_name=FEED_NAME)

        for post in blog_posts:
            fe = fg.add_entry()
            fe.title(post["title"])
            fe.description(post["description"])
            fe.link(href=post["link"])
            fe.published(post["date"])
            fe.id(post["link"])

        logger.info("Successfully generated RSS feed")
        return fg

    except Exception as e:
        logger.error(f"Error generating RSS feed: {str(e)}")
        raise


def save_rss_feed(feed_generator):
    """Save the RSS feed to a file in the feeds directory."""
    try:
        feeds_dir = get_feeds_dir()
        output_filename = feeds_dir / f"feed_{FEED_NAME}.xml"
        feed_generator.rss_file(str(output_filename), pretty=True)
        logger.info(f"Successfully saved RSS feed to {output_filename}")
        return output_filename

    except Exception as e:
        logger.error(f"Error saving RSS feed: {str(e)}")
        raise


def main():
    """Main function to generate RSS feed for Acme Weather blog."""
    try:
        html_content = fetch_blog_content(BLOG_URL)
        blog_posts = parse_blog_posts(html_content)
        feed = generate_rss_feed(blog_posts)
        save_rss_feed(feed)
        return True

    except Exception as e:
        logger.error(f"Failed to generate RSS feed: {str(e)}")
        return False


if __name__ == "__main__":
    main()

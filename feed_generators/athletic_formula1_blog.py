import logging

from athletic_utils import (
    fetch_blog_content,
    generate_rss_feed,
    parse_blog_posts,
    save_rss_feed,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BLOG_URL = "https://www.nytimes.com/athletic/formula-1/"
FEED_NAME = "athletic_formula1"
FEED_TITLE = "The Athletic - Formula 1"
FEED_DESCRIPTION = "Formula 1 news from The Athletic (NYTimes)."


def main():
    """Main function to generate RSS feed for The Athletic Formula 1 page."""
    html = fetch_blog_content(BLOG_URL)
    posts = parse_blog_posts(html)
    logger.info(f"Found {len(posts)} posts")

    if not posts:
        logger.warning("No posts found; feed will not be written")
        return False

    feed = generate_rss_feed(
        posts=posts,
        feed_title=FEED_TITLE,
        feed_description=FEED_DESCRIPTION,
        blog_url=BLOG_URL,
        feed_name=FEED_NAME,
    )
    save_rss_feed(feed_generator=feed, feed_name=FEED_NAME)
    return True


if __name__ == "__main__":
    main()

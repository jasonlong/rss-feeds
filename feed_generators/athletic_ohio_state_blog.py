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

BLOG_URL = (
    "https://www.nytimes.com/athletic/college-football/team/"
    "ohio-state-buckeyes-college-football/"
)
FEED_NAME = "athletic_ohio_state"
FEED_TITLE = "The Athletic - Ohio State Buckeyes (College Football)"
FEED_DESCRIPTION = (
    "Ohio State Buckeyes college football news from The Athletic (NYTimes)."
)


def main():
    """Main function to generate RSS feed for The Athletic Ohio State page."""
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

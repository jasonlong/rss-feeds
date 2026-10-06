"""Generate RSS for Rauno's numbered, undated field notes."""

import logging
import re
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from utils import get_feeds_dir, setup_feed_links

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BLOG_URL = "https://rauno.me/notes"
FEED_NAME = "rauno_notes"


def fetch_blog_content(url):
    response = requests.get(
        url, headers={"User-Agent": "Mozilla/5.0 (RSS Feed Generator)"}, timeout=20
    )
    response.raise_for_status()
    return response.text


def parse_blog_posts(html_content):
    """Use numbered note URLs, independent of presentation classes or SVG text."""
    soup = BeautifulSoup(html_content, "html.parser")
    posts = {}
    for anchor in soup.select("main a[href]"):
        link = urlsplit(urljoin(BLOG_URL, anchor["href"]))
        match = re.fullmatch(r"/notes/([1-9]\d*)/?", link.path)
        if link.scheme != "https" or link.netloc != "rauno.me" or not match:
            continue
        number = int(match[1])
        url = f"{BLOG_URL}/{number}"
        posts[url] = {
            "title": f"Field note #{number}",
            "link": url,
            "number": number,
        }

    if not posts:
        # Do not overwrite an existing feed when the source layout changes.
        raise ValueError("No field notes found on Rauno's notes index")
    return sorted(posts.values(), key=lambda post: post["number"])


def parse_note_summary(html_content):
    """Extract an opening paragraph; the site does not publish note dates."""
    soup = BeautifulSoup(html_content, "html.parser")
    paragraph = soup.select_one('main[data-route^="notes"] p')
    if paragraph is None or not paragraph.get_text(" ", strip=True):
        raise ValueError("Could not find field note content")
    return paragraph.get_text(" ", strip=True)


def generate_rss_feed(posts):
    fg = FeedGenerator()
    fg.title("Rauno – Field Notes")
    fg.description("Field notes by Rauno Freiberg")
    fg.language("en")
    fg.author({"name": "Rauno Freiberg"})
    setup_feed_links(fg, blog_url=BLOG_URL, feed_name=FEED_NAME)

    # feedgen prepends entries. Number order gives newest first without inventing
    # publication dates or assigning a changing retrieval time to every note.
    for post in sorted(posts, key=lambda post: post["number"]):
        entry = fg.add_entry()
        entry.title(post["title"])
        entry.link(href=post["link"])
        entry.guid(post["link"], permalink=True)
        entry.description(post.get("description", post["title"]))
    return fg


def save_rss_feed(feed_generator):
    output = get_feeds_dir() / f"feed_{FEED_NAME}.xml"
    feed_generator.rss_file(str(output), pretty=True)
    logger.info("Saved RSS feed to %s", output)
    return output


def main():
    posts = parse_blog_posts(fetch_blog_content(BLOG_URL))
    for post in posts:
        post["description"] = parse_note_summary(fetch_blog_content(post["link"]))
    save_rss_feed(generate_rss_feed(posts))
    logger.info("Generated %s field notes", len(posts))
    return True


if __name__ == "__main__":
    main()

import logging
import re
from datetime import datetime

import pytz
import requests
from feedgen.feed import FeedGenerator
from utils import get_feeds_dir, setup_feed_links

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

STORE_URL = "https://store.tomsachs.com"
PRODUCTS_JSON_URL = f"{STORE_URL}/products.json"
FEED_NAME = "tomsachs"
MAX_PRODUCTS = 50


def fetch_products():
    """Fetch recent products from the Shopify JSON API."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(
            PRODUCTS_JSON_URL,
            params={"limit": MAX_PRODUCTS},
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("products", [])
    except requests.RequestException as e:
        logger.error(f"Error fetching products: {str(e)}")
        raise


def parse_products(products):
    """Parse Shopify product JSON into feed entries."""
    entries = []

    for product in products:
        title = product.get("title", "")
        handle = product.get("handle", "")
        published_at = product.get("published_at")
        body_html = product.get("body_html", "") or ""

        if not title or not published_at:
            continue

        # Parse the published date
        try:
            pub_date = datetime.fromisoformat(published_at)
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=pytz.UTC)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse date for product: {title}")
            continue

        link = f"{STORE_URL}/products/{handle}"

        # Build description from body HTML (strip tags) and price
        description = re.sub(r"<[^>]+>", "", body_html).strip()
        description = re.sub(r"\s+", " ", description)
        if len(description) > 500:
            description = description[:500] + "..."

        # Add price info
        variants = product.get("variants", [])
        if variants:
            price = variants[0].get("price")
            if price:
                description = (
                    f"${price} — {description}" if description else f"${price}"
                )

        # Get first image for enclosure
        images = product.get("images", [])
        image_url = images[0].get("src") if images else None

        entries.append(
            {
                "title": title,
                "link": link,
                "description": description,
                "pub_date": pub_date,
                "image_url": image_url,
            }
        )

    # Sort by date descending (newest first)
    entries.sort(key=lambda x: x["pub_date"], reverse=True)
    logger.info(f"Parsed {len(entries)} products")
    return entries


def generate_rss_feed(entries):
    """Generate RSS feed from product entries."""
    try:
        fg = FeedGenerator()
        fg.title("Tom Sachs Store")
        fg.description("New products from the Tom Sachs Store")
        fg.language("en")

        fg.author({"name": "Tom Sachs"})
        fg.subtitle("Latest drops from the Tom Sachs Store")

        setup_feed_links(fg, blog_url=STORE_URL, feed_name=FEED_NAME)

        for entry in entries:
            fe = fg.add_entry()
            fe.title(entry["title"])
            fe.description(entry["description"])
            fe.link(href=entry["link"])
            fe.published(entry["pub_date"])
            fe.id(entry["link"])

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
    """Main function to generate RSS feed for Tom Sachs Store."""
    try:
        products = fetch_products()
        entries = parse_products(products)
        feed = generate_rss_feed(entries)
        save_rss_feed(feed)
        return True

    except Exception as e:
        logger.error(f"Failed to generate RSS feed: {str(e)}")
        return False


if __name__ == "__main__":
    main()

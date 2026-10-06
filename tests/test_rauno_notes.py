"""Regression checks for SVG-only titles, canonical IDs and undated notes."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "feed_generators"))
import rauno_notes


class RaunoNotesTests(unittest.TestCase):
    def test_links_are_unique_and_numeric(self):
        posts = rauno_notes.parse_blog_posts(
            '<main><a href="/notes/10"><svg/></a>'
            '<a href="/notes/2" aria-label="Field note #2"></a>'
            '<a href="https://rauno.me/notes/2/?ref=home#top"></a>'
            '<a href="https://example.com/notes/3"></a>'
            '<a href="/notes"></a><a href="/craft"></a></main>'
        )
        self.assertEqual([post["number"] for post in posts], [2, 10])
        self.assertEqual(posts[1]["title"], "Field note #10")
        xml = ElementTree.fromstring(rauno_notes.generate_rss_feed(posts).rss_str())
        channel = xml.find("channel")
        self.assertEqual(channel.findtext("link"), rauno_notes.BLOG_URL)
        self.assertEqual(
            channel.find("{http://www.w3.org/2005/Atom}link").get("href"),
            "https://jasonlong.github.io/rss-feeds/feeds/feed_rauno_notes.xml",
        )
        items = channel.findall("item")
        self.assertEqual(
            [item.findtext("title") for item in items],
            ["Field note #10", "Field note #2"],
        )
        for item in items:
            self.assertEqual(item.findtext("guid"), item.findtext("link"))
            self.assertIsNone(item.find("pubDate"))

    def test_item_content_stays_stable(self):
        posts = rauno_notes.parse_blog_posts('<main><a href="/notes/1"></a></main>')
        first = ElementTree.fromstring(rauno_notes.generate_rss_feed(posts).rss_str())
        second = ElementTree.fromstring(rauno_notes.generate_rss_feed(posts).rss_str())
        self.assertEqual(
            ElementTree.tostring(first.find("channel/item")),
            ElementTree.tostring(second.find("channel/item")),
        )

    def test_summary_and_source_failure(self):
        self.assertEqual(
            rauno_notes.parse_note_summary(
                '<main data-route="notes-dark"><p>Dark theme note.</p></main>'
            ),
            "Dark theme note.",
        )
        self.assertEqual(
            rauno_notes.parse_note_summary(
                '<main data-route="notes"><p>Some <a>linked</a> text.</p></main>'
            ),
            "Some linked text.",
        )
        with self.assertRaises(ValueError):
            rauno_notes.parse_note_summary("<main>Missing</main>")
        with patch.object(
            rauno_notes, "fetch_blog_content", return_value="<main/>"
        ), patch.object(rauno_notes, "save_rss_feed") as save:
            with self.assertRaises(ValueError):
                rauno_notes.main()
            save.assert_not_called()


if __name__ == "__main__":
    unittest.main()

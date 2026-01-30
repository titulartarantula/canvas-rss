#!/usr/bin/env python3
"""Canvas RSS Aggregator - Main Entry Point."""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from utils.logger import setup_logger
from utils.database import Database
from scrapers.instructure_community import InstructureScraper
from scrapers.reddit_client import RedditMonitor
from scrapers.status_page import StatusPageMonitor
from processor.content_processor import ContentProcessor
from generator.rss_builder import RSSBuilder


def main():
    """Main aggregation workflow."""

    # Setup logger
    logger = setup_logger(
        log_file=os.getenv("LOG_FILE", "logs/aggregator.log")
    )

    logger.info("=" * 50)
    logger.info(f"Canvas RSS Aggregator started at {datetime.now()}")
    logger.info("=" * 50)

    # Initialize components
    db = Database()
    processor = ContentProcessor(gemini_api_key=os.getenv("GEMINI_API_KEY"))
    rss_builder = RSSBuilder()

    # Collect content from all sources
    all_items = []

    try:
        # 1. Scrape Instructure Community (all sources: release notes, changelog, Q&A, blog)
        logger.info("Scraping Instructure Community...")
        with InstructureScraper() as instructure:
            try:
                community_posts = instructure.scrape_all()
                all_items.extend(community_posts)
                logger.info(f"  -> Found {len(community_posts)} community posts")
            except NotImplementedError:
                logger.warning("  -> Instructure scraper not yet implemented")

        # 2. Monitor Reddit
        logger.info("Monitoring Reddit...")
        reddit = RedditMonitor(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT")
        )
        try:
            reddit_posts = reddit.search_canvas_discussions()
            all_items.extend(reddit_posts)
            logger.info(f"  -> Found {len(reddit_posts)} relevant Reddit posts")
        except NotImplementedError:
            logger.warning("  -> Reddit monitor not yet implemented")

        # 3. Check Status Page
        logger.info("Checking Canvas Status Page...")
        status = StatusPageMonitor()
        try:
            incidents = status.get_recent_incidents()
            all_items.extend(incidents)
            logger.info(f"  -> Found {len(incidents)} status incidents")
        except NotImplementedError:
            logger.warning("  -> Status page monitor not yet implemented")

        # 4. Process all content
        logger.info("Processing content...")
        try:
            new_items = processor.deduplicate(all_items, db)
            logger.info(f"  -> {len(new_items)} new items after deduplication")

            enriched_items = processor.enrich_with_llm(new_items)
            logger.info(f"  -> Enriched {len(enriched_items)} items with summaries and sentiment")
        except NotImplementedError:
            logger.warning("  -> Content processor not yet implemented")
            enriched_items = all_items

        # 5. Generate RSS feed
        logger.info("Generating RSS feed...")
        try:
            feed_xml = rss_builder.create_feed(enriched_items)
            output_path = Path("output/feed.xml")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(feed_xml)
            logger.info(f"  -> RSS feed written to {output_path}")
        except NotImplementedError:
            logger.warning("  -> RSS builder not yet implemented")

        # 6. Store in database
        try:
            for item in enriched_items:
                db.insert_item(item)
            db.record_feed_generation(len(enriched_items), feed_xml if 'feed_xml' in dir() else "")
        except NotImplementedError:
            logger.warning("  -> Database storage not yet implemented")

        logger.info("=" * 50)
        logger.info(f"Aggregation complete! {len(all_items)} items collected")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"Error during aggregation: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

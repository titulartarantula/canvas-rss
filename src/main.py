#!/usr/bin/env python3
"""Canvas RSS Aggregator - Main Entry Point."""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Union

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from utils.logger import setup_logger
from utils.database import Database
from scrapers.instructure_community import (
    InstructureScraper,
    CommunityPost,
    ReleaseNote,
    ChangeLogEntry,
)
from scrapers.reddit_client import RedditMonitor, RedditPost
from scrapers.status_page import StatusPageMonitor, Incident
from processor.content_processor import ContentProcessor, ContentItem
from generator.rss_builder import RSSBuilder


def community_post_to_content_item(post: Union[CommunityPost, ReleaseNote, ChangeLogEntry]) -> ContentItem:
    """Convert a community post to ContentItem format.

    Args:
        post: A CommunityPost, ReleaseNote, or ChangeLogEntry from Instructure scraper.

    Returns:
        ContentItem ready for processing.
    """
    # Calculate engagement score from likes + comments (if available)
    engagement = 0
    if hasattr(post, 'likes'):
        engagement += post.likes
    if hasattr(post, 'comments'):
        engagement += post.comments

    # Map post_type to content_type for content-specific summarization
    # post_type values: 'release_note', 'deploy_note', 'changelog', 'blog', 'question'
    content_type = getattr(post, 'post_type', 'release_note')
    # ChangeLogEntry doesn't have post_type, so detect it by class
    if isinstance(post, ChangeLogEntry):
        content_type = 'changelog'

    return ContentItem(
        source=post.source,
        source_id=post.source_id,
        title=post.title,
        url=post.url,
        content=post.content,
        content_type=content_type,
        published_date=post.published_date,
        engagement_score=engagement,
    )


def reddit_post_to_content_item(post: RedditPost) -> ContentItem:
    """Convert a Reddit post to ContentItem format.

    Args:
        post: A RedditPost from Reddit monitor.

    Returns:
        ContentItem ready for processing.
    """
    # Anonymize Reddit posts before converting
    anonymized = post.anonymize()

    return ContentItem(
        source=anonymized.source,
        source_id=anonymized.source_id,
        title=anonymized.title,
        url=anonymized.url,
        content=anonymized.content,
        content_type="reddit",
        published_date=anonymized.published_date,
        engagement_score=anonymized.score + anonymized.num_comments,
    )


def incident_to_content_item(incident: Incident) -> ContentItem:
    """Convert a status incident to ContentItem format.

    Args:
        incident: An Incident from status page monitor.

    Returns:
        ContentItem ready for processing.
    """
    # Prefix title with impact level for visibility
    title = incident.title
    if incident.impact and incident.impact != "none":
        title = f"[{incident.impact.upper()}] {title}"

    return ContentItem(
        source=incident.source,
        source_id=incident.source_id,
        title=title,
        url=incident.url,
        content=incident.content,
        content_type="status",
        published_date=incident.created_at,
        engagement_score=0,  # Status incidents don't have engagement metrics
    )


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
    all_items: List[ContentItem] = []

    try:
        # 1. Scrape Instructure Community
        logger.info("Scraping Instructure Community...")
        with InstructureScraper() as instructure:
            community_posts = instructure.scrape_all()
            for post in community_posts:
                all_items.append(community_post_to_content_item(post))
            logger.info(f"  -> Found {len(community_posts)} community posts")

        # 2. Monitor Reddit
        logger.info("Monitoring Reddit...")
        reddit = RedditMonitor(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT")
        )
        reddit_posts = reddit.search_canvas_discussions()
        for post in reddit_posts:
            all_items.append(reddit_post_to_content_item(post))
        logger.info(f"  -> Found {len(reddit_posts)} relevant Reddit posts")

        # 3. Check Status Page
        logger.info("Checking Canvas Status Page...")
        status = StatusPageMonitor()
        incidents = status.get_recent_incidents()
        for incident in incidents:
            all_items.append(incident_to_content_item(incident))
        logger.info(f"  -> Found {len(incidents)} status incidents")

        # 4. Process all content (deduplicate and enrich)
        logger.info("Processing content...")
        new_items = processor.deduplicate(all_items, db)
        logger.info(f"  -> {len(new_items)} new items after deduplication")

        enriched_items = processor.enrich_with_llm(new_items)
        logger.info(f"  -> Enriched {len(enriched_items)} items with summaries and sentiment")

        # 5. Generate RSS feed
        logger.info("Generating RSS feed...")
        feed_xml = rss_builder.create_feed(enriched_items)
        output_path = Path("output/feed.xml")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(feed_xml, encoding="utf-8")
        logger.info(f"  -> RSS feed written to {output_path}")

        # 6. Store in database for future deduplication
        logger.info("Storing items in database...")
        stored_count = 0
        for item in enriched_items:
            item_id = db.insert_item(item)
            if item_id > 0:
                stored_count += 1
        db.record_feed_generation(len(enriched_items), feed_xml)
        logger.info(f"  -> Stored {stored_count} new items in database")

        logger.info("=" * 50)
        logger.info(f"Aggregation complete! {len(all_items)} items collected, {len(enriched_items)} new")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"Error during aggregation: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

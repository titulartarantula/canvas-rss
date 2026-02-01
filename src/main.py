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
from __init__ import __version__


def community_post_to_content_item(post: Union[CommunityPost, ReleaseNote, ChangeLogEntry]) -> ContentItem:
    """Convert a community post to ContentItem format.

    Args:
        post: A CommunityPost, ReleaseNote, or ChangeLogEntry from Instructure scraper.

    Returns:
        ContentItem ready for processing.
    """
    # Calculate engagement score from likes + comments (if available)
    engagement = 0
    comment_count = 0
    if hasattr(post, 'likes'):
        engagement += post.likes
    if hasattr(post, 'comments'):
        engagement += post.comments
        comment_count = post.comments

    # Map post_type to content_type for content-specific summarization
    # post_type values: 'release_note', 'deploy_note', 'changelog', 'blog', 'question'
    content_type = getattr(post, 'post_type', 'release_note')
    # ChangeLogEntry doesn't have post_type, so detect it by class
    if isinstance(post, ChangeLogEntry):
        content_type = 'changelog'

    # Check for is_latest flag (for release/deploy notes)
    is_latest = getattr(post, 'is_latest', False)

    return ContentItem(
        source=post.source,
        source_id=post.source_id,
        title=post.title,
        url=post.url,
        content=post.content,
        content_type=content_type,
        published_date=post.published_date,
        engagement_score=engagement,
        comment_count=comment_count,
        is_latest=is_latest,
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
    logger.info(f"Canvas RSS Aggregator v{__version__} started at {datetime.now()}")
    logger.info("=" * 50)

    # Initialize components
    db = Database()
    processor = ContentProcessor(gemini_api_key=os.getenv("GEMINI_API_KEY"))
    rss_builder = RSSBuilder()

    # Detect first run (empty database) - skip date filtering to capture history
    is_first_run = len(db.get_recent_items(days=30)) == 0
    if is_first_run:
        logger.info("First run detected - will skip date filtering to capture history")

    # Collect content from all sources
    all_items: List[ContentItem] = []

    try:
        # 1. Scrape Instructure Community
        logger.info("Scraping Instructure Community...")
        with InstructureScraper() as instructure:
            community_posts = instructure.scrape_all(skip_date_filter=is_first_run)
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

        # 4. Process all content (deduplicate and check for new comments)
        logger.info("Processing content...")

        # Types that should be included if they have new comments (discussion-focused content)
        COMMENT_TRACKED_TYPES = {"blog", "question"}

        # Separate deduplication: check for new items AND items with new comments
        new_items = []
        updated_items = []
        new_item_ids = set()  # Track source_ids of new items

        for item in all_items:
            if item is None:
                continue

            if not db.item_exists(item.source_id):
                # New item - include it
                new_items.append(item)
                new_item_ids.add(item.source_id)
            elif item.content_type in COMMENT_TRACKED_TYPES:
                # Existing item of tracked type - check for new comments
                prev_count = db.get_comment_count(item.source_id)
                if prev_count is not None and item.comment_count > prev_count:
                    logger.info(
                        f"  -> New comments detected on {item.content_type}: "
                        f"{item.title[:50]}... ({prev_count} -> {item.comment_count})"
                    )
                    # Mark as updated for different summarization prompt
                    item.content_type = f"{item.content_type}_updated"
                    # Update the comment count in DB and include in feed
                    db.update_comment_count(item.source_id, item.comment_count)
                    updated_items.append(item)

        # Combine new items and items with new comments
        items_to_process = new_items + updated_items
        logger.info(
            f"  -> {len(new_items)} new items, {len(updated_items)} items with new comments"
        )

        enriched_items = processor.enrich_with_llm(items_to_process)
        logger.info(f"  -> Enriched {len(enriched_items)} items with summaries and topics")

        # 5. Generate RSS feed
        logger.info("Generating RSS feed...")
        feed_xml = rss_builder.create_feed(enriched_items)
        output_path = Path("output/feed.xml")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(feed_xml, encoding="utf-8")
        logger.info(f"  -> RSS feed written to {output_path}")

        # 6. Store new items in database for future deduplication
        # (Updated items already exist in DB, just had their comment_count updated)
        logger.info("Storing new items in database...")
        stored_count = 0
        for item in enriched_items:
            if item.source_id in new_item_ids:  # Only store genuinely new items
                item_id = db.insert_item(item)
                if item_id > 0:
                    stored_count += 1
        db.record_feed_generation(len(enriched_items), feed_xml)
        logger.info(f"  -> Stored {stored_count} new items in database")

        logger.info("=" * 50)
        logger.info(
            f"Aggregation complete! {len(all_items)} items collected, "
            f"{len(new_items)} new, {len(updated_items)} updated"
        )
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"Error during aggregation: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

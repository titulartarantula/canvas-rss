#!/usr/bin/env python3
"""Canvas RSS Aggregator - Main Entry Point.

Scrapes Canvas LMS sources and stores content in the database.
Website presentation is handled separately.
"""

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
    classify_discussion_posts,
    classify_release_features,
    classify_deploy_changes,
)
from scrapers.reddit_client import RedditMonitor, RedditPost
from scrapers.status_page import StatusPageMonitor, Incident
from processor.content_processor import ContentProcessor, ContentItem

# Read version from VERSION file
_version_file = Path(__file__).parent.parent / "VERSION"
__version__ = _version_file.read_text().strip() if _version_file.exists() else "0.0.0"


def community_post_to_content_item(post: Union[CommunityPost, ReleaseNote, ChangeLogEntry]) -> ContentItem:
    """Convert a community post to ContentItem format.

    Args:
        post: A CommunityPost, ReleaseNote, or ChangeLogEntry from Instructure scraper.

    Returns:
        ContentItem ready for database storage.
    """
    engagement = 0
    comment_count = 0
    if hasattr(post, 'likes'):
        engagement += post.likes
    if hasattr(post, 'comments'):
        engagement += post.comments
        comment_count = post.comments

    content_type = getattr(post, 'post_type', 'release_note')
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
        comment_count=comment_count,
        first_posted=getattr(post, 'first_posted', None),
        last_edited=getattr(post, 'last_edited', None),
        last_comment_at=getattr(post, 'last_comment_at', None),
    )


def reddit_post_to_content_item(post: RedditPost) -> ContentItem:
    """Convert a Reddit post to ContentItem format.

    Args:
        post: A RedditPost from Reddit monitor.

    Returns:
        ContentItem ready for database storage.
    """
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
        ContentItem ready for database storage.
    """
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
        engagement_score=0,
    )


def store_discussion_posts(
    posts: List[CommunityPost],
    db: Database,
    scraper: InstructureScraper,
    processor: ContentProcessor,
) -> int:
    """Process and store Q&A and blog posts with tracking.

    Args:
        posts: Combined list of question and blog posts.
        db: Database for tracking.
        scraper: Scraper instance for fetching latest comments.
        processor: ContentProcessor for LLM enrichment.

    Returns:
        Number of items stored.
    """
    import logging
    logger = logging.getLogger("canvas_rss")

    updates = classify_discussion_posts(posts, db, first_run_limit=5, scraper=scraper)
    stored = 0

    for update in updates:
        post = update.post
        item = community_post_to_content_item(post)

        # Enrich with LLM
        item.content = processor.sanitize_html(item.content)
        item.content = processor.redact_pii(item.content)
        item.title = processor.redact_pii(item.title)
        item.summary = processor.summarize_with_llm(item.content, item.content_type)
        primary, secondary = processor.classify_topic(item.content)
        item.primary_topic = primary
        item.topics = secondary

        # Store in database
        item_id = db.insert_item(item)
        if item_id > 0:
            stored += 1

            # Create content_feature_refs for this item
            for feature_id, option_id, mention_type in update.feature_refs:
                try:
                    db.add_content_feature_ref(
                        content_id=item.source_id,
                        feature_id=feature_id,
                        feature_option_id=option_id,
                        mention_type=mention_type,
                    )
                except Exception as e:
                    logger.warning(f"Failed to add feature ref for {item.source_id}: {e}")

    logger.debug(f"Stored {stored} discussion posts")
    return stored


def store_release_notes(
    notes: List[ReleaseNote],
    db: Database,
    scraper: InstructureScraper,
    processor: ContentProcessor,
    is_first_run: bool = False,
    first_run_limit: int = 3,
) -> int:
    """Process and store release notes with feature tracking.

    Args:
        notes: List of release note posts (post_type='release_note').
        db: Database for feature tracking.
        scraper: Scraper instance for parsing pages.
        processor: ContentProcessor for generating summaries.
        is_first_run: Whether this is the first run.
        first_run_limit: Max items to include on first run.

    Returns:
        Number of items stored.
    """
    import logging
    logger = logging.getLogger("canvas_rss")

    stored = 0
    new_page_count = 0

    for note in notes:
        page = scraper.parse_release_note_page(note.url)
        if page is None:
            logger.warning(f"Failed to parse release note page: {note.url}")
            continue

        is_new_page, new_anchors = classify_release_features(page, db, first_run_limit=3)

        if not is_new_page and not new_anchors:
            continue

        if is_new_page:
            new_page_count += 1
            if is_first_run and new_page_count > first_run_limit:
                continue

        # Generate summaries for features
        for feature in page.features:
            try:
                feature.summary = processor.summarize_feature(feature)
            except Exception as e:
                logger.warning(f"Failed to summarize feature '{feature.name}': {e}")

        # Store the content item
        item = community_post_to_content_item(note)
        item.content = processor.sanitize_html(item.content)
        item.content = processor.redact_pii(item.content)
        item.title = processor.redact_pii(item.title)

        item_id = db.insert_item(item)
        if item_id > 0:
            stored += 1

            # Store upcoming changes from this release note
            if page.upcoming_changes:
                for change in page.upcoming_changes:
                    if not db.upcoming_change_exists(
                        item.source_id,
                        change.date.isoformat() if change.date else None,
                        change.description
                    ):
                        db.insert_upcoming_change(
                            content_id=item.source_id,
                            change_date=change.date.isoformat() if change.date else None,
                            description=change.description,
                        )
                logger.debug(f"Stored {len(page.upcoming_changes)} upcoming changes")

    logger.debug(f"Stored {stored} release notes")
    return stored


def store_deploy_notes(
    notes: List[ReleaseNote],
    db: Database,
    scraper: InstructureScraper,
    processor: ContentProcessor,
    is_first_run: bool = False,
    first_run_limit: int = 3,
) -> int:
    """Process and store deploy notes with change tracking.

    Args:
        notes: List of deploy note posts (post_type='deploy_note').
        db: Database for change tracking.
        scraper: Scraper instance for parsing pages.
        processor: ContentProcessor for generating summaries.
        is_first_run: Whether this is the first run.
        first_run_limit: Max items to include on first run.

    Returns:
        Number of items stored.
    """
    import logging
    logger = logging.getLogger("canvas_rss")

    stored = 0
    new_page_count = 0

    for note in notes:
        page = scraper.parse_deploy_note_page(note.url)
        if page is None:
            logger.warning(f"Failed to parse deploy note page: {note.url}")
            continue

        is_new_page, new_anchors = classify_deploy_changes(page, db, first_run_limit=3)

        if not is_new_page and not new_anchors:
            continue

        if is_new_page:
            new_page_count += 1
            if is_first_run and new_page_count > first_run_limit:
                continue

        # Generate summaries for changes
        for change in page.changes:
            try:
                change.summary = processor.summarize_deploy_change(change)
            except Exception as e:
                logger.warning(f"Failed to summarize change '{change.name}': {e}")

        # Store the content item
        item = community_post_to_content_item(note)
        item.content = processor.sanitize_html(item.content)
        item.content = processor.redact_pii(item.content)
        item.title = processor.redact_pii(item.title)

        item_id = db.insert_item(item)
        if item_id > 0:
            stored += 1

    logger.debug(f"Stored {stored} deploy notes")
    return stored


def main():
    """Main aggregation workflow - scrape and store in database."""

    logger = setup_logger(
        log_file=os.getenv("LOG_FILE", "logs/aggregator.log")
    )

    logger.info("=" * 50)
    logger.info(f"Canvas Aggregator v{__version__} started at {datetime.now()}")
    logger.info("=" * 50)

    db = Database()
    processor = ContentProcessor(gemini_api_key=os.getenv("GEMINI_API_KEY"))

    # Seed canonical features on startup
    seeded = db.seed_features()
    if seeded > 0:
        logger.info(f"Seeded {seeded} canonical Canvas features")

    # First run detection
    recent_items = db.get_recent_items(days=30)
    is_first_run = len(recent_items) == 0
    if is_first_run:
        logger.info("First run detected - applying item limits to avoid flooding")

    total_stored = 0

    try:
        # 1. Scrape Instructure Community
        logger.info("Scraping Instructure Community...")
        with InstructureScraper() as scraper:
            # Q&A forum
            questions = scraper.scrape_question_forum(hours=24)
            q_stored = store_discussion_posts(questions, db, scraper, processor)
            logger.info(f"  -> {q_stored} Q&A items stored")
            total_stored += q_stored

            # Blog
            blogs = scraper.scrape_blog(hours=24)
            b_stored = store_discussion_posts(blogs, db, scraper, processor)
            logger.info(f"  -> {b_stored} blog items stored")
            total_stored += b_stored

            # Release notes
            all_notes = scraper.scrape_release_notes(hours=24, skip_date_filter=is_first_run)
            release_notes = [n for n in all_notes if n.post_type == "release_note"]
            r_stored = store_release_notes(
                release_notes, db, scraper, processor,
                is_first_run=is_first_run, first_run_limit=3
            )
            logger.info(f"  -> {r_stored} release notes stored")
            total_stored += r_stored

            # Deploy notes
            deploy_notes = [n for n in all_notes if n.post_type == "deploy_note"]
            d_stored = store_deploy_notes(
                deploy_notes, db, scraper, processor,
                is_first_run=is_first_run, first_run_limit=3
            )
            logger.info(f"  -> {d_stored} deploy notes stored")
            total_stored += d_stored

        # 2. Monitor Reddit
        logger.info("Monitoring Reddit...")
        reddit = RedditMonitor(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT")
        )
        reddit_posts = reddit.search_canvas_discussions()
        reddit_stored = 0
        for post in reddit_posts:
            item = reddit_post_to_content_item(post)
            if not db.item_exists(item.source_id):
                # Enrich
                item.content = processor.sanitize_html(item.content)
                item.content = processor.redact_pii(item.content)
                item.title = processor.redact_pii(item.title)
                item.summary = processor.summarize_with_llm(item.content, "reddit")
                primary, secondary = processor.classify_topic(item.content)
                item.primary_topic = primary
                item.topics = secondary

                item_id = db.insert_item(item)
                if item_id > 0:
                    reddit_stored += 1
        logger.info(f"  -> {reddit_stored} Reddit posts stored (of {len(reddit_posts)} found)")
        total_stored += reddit_stored

        # 3. Check Status Page
        logger.info("Checking Canvas Status Page...")
        status = StatusPageMonitor()
        incidents = status.get_recent_incidents()
        status_stored = 0
        for incident in incidents:
            item = incident_to_content_item(incident)
            if not db.item_exists(item.source_id):
                item.content = processor.sanitize_html(item.content)
                item.content = processor.redact_pii(item.content)
                item.summary = processor.summarize_with_llm(item.content, "status")

                item_id = db.insert_item(item)
                if item_id > 0:
                    status_stored += 1
        logger.info(f"  -> {status_stored} status incidents stored (of {len(incidents)} found)")
        total_stored += status_stored

        logger.info("=" * 50)
        logger.info(f"Aggregation complete! {total_stored} items stored")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"Error during aggregation: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

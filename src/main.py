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
    DiscussionUpdate,
    ReleaseNotePage,
    DeployNotePage,
    classify_discussion_posts,
    classify_release_features,
    classify_deploy_changes,
)
from scrapers.reddit_client import RedditMonitor, RedditPost
from scrapers.status_page import StatusPageMonitor, Incident
from processor.content_processor import ContentProcessor, ContentItem
from generator.rss_builder import (
    RSSBuilder,
    build_discussion_title,
    format_discussion_description,
    build_release_note_entry,
    build_deploy_note_entry,
)
# Read version from VERSION file (avoid import issues when running as script)
_version_file = Path(__file__).parent.parent / "VERSION"
__version__ = _version_file.read_text().strip() if _version_file.exists() else "0.0.0"


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


def process_discussion_posts(
    posts: List[CommunityPost],
    db: "Database",
    scraper: InstructureScraper
) -> List[ContentItem]:
    """Process Q&A and blog posts with v1.3.0 [NEW]/[UPDATE] tracking.

    Args:
        posts: Combined list of question and blog posts.
        db: Database for tracking.
        scraper: Scraper instance for fetching latest comments.

    Returns:
        List of ContentItems with [NEW]/[UPDATE] badges.
    """
    import logging
    logger = logging.getLogger("canvas_rss")

    # Use classify_discussion_posts for proper tracking
    updates = classify_discussion_posts(posts, db, first_run_limit=5, scraper=scraper)

    items = []
    for update in updates:
        post = update.post

        # Build title with [NEW]/[UPDATE] badge
        title = build_discussion_title(post.post_type, post.title, update.is_new)

        # Create ContentItem with v1.3.0 metadata (description built after LLM enrichment)
        item = ContentItem(
            source="community",
            source_id=post.source_id,
            title=title,
            url=post.url,
            content=post.content,  # Keep original for LLM enrichment
            content_type=post.post_type,
            published_date=post.published_date,
            engagement_score=post.likes + post.comments,
            comment_count=post.comments,
            has_v130_badge=True,
            # v1.3.0 metadata for building description after enrichment
            is_new_post=update.is_new,
            previous_comment_count=update.previous_comment_count,
            new_comment_count=update.new_comment_count,
            latest_comment_preview=update.latest_comment or "",
        )
        items.append(item)

    logger.debug(f"Processed {len(items)} discussion posts with v1.3.0 tracking")
    return items


def process_release_notes(
    notes: List[ReleaseNote],
    db: "Database",
    scraper: InstructureScraper,
    processor: ContentProcessor = None,
    is_first_run: bool = False,
    first_run_limit: int = 3
) -> List[ContentItem]:
    """Process release notes with feature-level [NEW]/[UPDATE] tracking.

    Args:
        notes: List of release note posts (post_type='release_note').
        db: Database for feature tracking.
        scraper: Scraper instance for parsing pages.
        processor: ContentProcessor for generating per-feature summaries.
        is_first_run: Whether this is the first run (applies item limit).
        first_run_limit: Max items to include on first run.

    Returns:
        List of ContentItems with [NEW]/[UPDATE] badges.
    """
    import logging
    logger = logging.getLogger("canvas_rss")

    items = []
    new_page_count = 0
    for note in notes:
        # Parse page to get individual features
        page = scraper.parse_release_note_page(note.url)
        if page is None:
            logger.warning(f"Failed to parse release note page: {note.url}")
            continue

        # Classify features (this also tracks them in the database)
        is_new_page, new_anchors = classify_release_features(page, db, first_run_limit=3)

        # Skip if no new content
        if not is_new_page and not new_anchors:
            continue

        # On first run, limit how many new pages we include in the feed
        if is_new_page:
            new_page_count += 1
            if is_first_run and new_page_count > first_run_limit:
                continue  # Tracked in DB but not added to feed

        # Generate summaries for each feature (Task 17)
        if processor is not None:
            for feature in page.features:
                try:
                    feature.summary = processor.summarize_feature(feature)
                except Exception as e:
                    logger.warning(f"Failed to summarize feature '{feature.name}': {e}")
                    feature.summary = ""

        # Determine badge: [NEW] if page is new, [UPDATE] if features added
        badge = "[NEW]" if is_new_page else "[UPDATE]"

        # Build description with feature details (now uses feature.summary)
        description = build_release_note_entry(
            page=page,
            is_update=not is_new_page,
            new_features=new_anchors if not is_new_page else None
        )

        item = ContentItem(
            source="community",
            source_id=note.source_id,
            title=f"{badge} {note.title}",
            url=note.url,
            content=note.content,  # Keep original for LLM enrichment
            structured_description=description,  # Store formatted version for RSS
            content_type="release_note",
            published_date=note.published_date,
            engagement_score=note.likes + note.comments,
            is_latest=note.is_latest,
            has_v130_badge=True,
        )
        items.append(item)

    logger.debug(f"Processed {len(items)} release notes with v1.3.0 tracking")
    return items


def process_deploy_notes(
    notes: List[ReleaseNote],
    db: "Database",
    scraper: InstructureScraper,
    processor: ContentProcessor = None,
    is_first_run: bool = False,
    first_run_limit: int = 3
) -> List[ContentItem]:
    """Process deploy notes with change-level [NEW]/[UPDATE] tracking.

    Args:
        notes: List of deploy note posts (post_type='deploy_note').
        db: Database for change tracking.
        scraper: Scraper instance for parsing pages.
        processor: ContentProcessor for generating per-change summaries.
        is_first_run: Whether this is the first run (applies item limit).
        first_run_limit: Max items to include on first run.

    Returns:
        List of ContentItems with [NEW]/[UPDATE] badges.
    """
    import logging
    logger = logging.getLogger("canvas_rss")

    items = []
    new_page_count = 0
    for note in notes:
        # Parse page to get individual changes
        page = scraper.parse_deploy_note_page(note.url)
        if page is None:
            logger.warning(f"Failed to parse deploy note page: {note.url}")
            continue

        # Classify changes (this also tracks them in the database)
        is_new_page, new_anchors = classify_deploy_changes(page, db, first_run_limit=3)

        # Skip if no new content
        if not is_new_page and not new_anchors:
            continue

        # On first run, limit how many new pages we include in the feed
        if is_new_page:
            new_page_count += 1
            if is_first_run and new_page_count > first_run_limit:
                continue  # Tracked in DB but not added to feed

        # Generate summaries for each change (Task 17)
        if processor is not None:
            for change in page.changes:
                try:
                    change.summary = processor.summarize_deploy_change(change)
                except Exception as e:
                    logger.warning(f"Failed to summarize change '{change.name}': {e}")
                    change.summary = ""

        # Determine badge: [NEW] if page is new, [UPDATE] if changes added
        badge = "[NEW]" if is_new_page else "[UPDATE]"

        # Build description with change details (now uses change.summary)
        description = build_deploy_note_entry(
            page=page,
            is_update=not is_new_page,
            new_changes=new_anchors if not is_new_page else None
        )

        item = ContentItem(
            source="community",
            source_id=note.source_id,
            title=f"{badge} {note.title}",
            url=note.url,
            content=note.content,  # Keep original for LLM enrichment
            structured_description=description,  # Store formatted version for RSS
            content_type="deploy_note",
            published_date=note.published_date,
            engagement_score=note.likes + note.comments,
            is_latest=note.is_latest,
            has_v130_badge=True,
        )
        items.append(item)

    logger.debug(f"Processed {len(items)} deploy notes with v1.3.0 tracking")
    return items


def main():
    """Main aggregation workflow with v1.3.0 [NEW]/[UPDATE] tracking."""

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

    # Detect first run using v1.3.0 tracking tables
    is_first_run = db.is_discussion_tracking_empty() and db.is_feature_tracking_empty()
    if is_first_run:
        logger.info("First run detected - will apply flood prevention limits")

    # Collect content from all sources
    all_items: List[ContentItem] = []

    try:
        # 1. Scrape Instructure Community with v1.3.0 tracking
        logger.info("Scraping Instructure Community...")
        with InstructureScraper() as scraper:
            # 1a. Discussion posts (Q&A + Blog) - v1.3.0 tracking
            # Process Q&A and Blog separately to apply 5-item limit to each
            questions = scraper.scrape_question_forum(hours=24)
            question_items = process_discussion_posts(questions, db, scraper)
            all_items.extend(question_items)
            logger.info(f"  -> {len(question_items)} Q&A items")

            blogs = scraper.scrape_blog(hours=24)
            blog_items = process_discussion_posts(blogs, db, scraper)
            all_items.extend(blog_items)
            logger.info(f"  -> {len(blog_items)} blog items")

            # 1b. Release notes - feature tracking with per-feature summaries
            all_notes = scraper.scrape_release_notes(hours=24, skip_date_filter=is_first_run)
            release_notes = [n for n in all_notes if n.post_type == "release_note"]
            release_items = process_release_notes(
                release_notes, db, scraper, processor,
                is_first_run=is_first_run, first_run_limit=3
            )
            all_items.extend(release_items)
            logger.info(f"  -> {len(release_items)} release note items")

            # 1c. Deploy notes - change tracking with per-change summaries
            deploy_notes = [n for n in all_notes if n.post_type == "deploy_note"]
            deploy_items = process_deploy_notes(
                deploy_notes, db, scraper, processor,
                is_first_run=is_first_run, first_run_limit=3
            )
            all_items.extend(deploy_items)
            logger.info(f"  -> {len(deploy_items)} deploy note items")

        # 2. Monitor Reddit (no v1.3.0 tracking - keep existing deduplication)
        logger.info("Monitoring Reddit...")
        reddit = RedditMonitor(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT")
        )
        reddit_posts = reddit.search_canvas_discussions()
        reddit_count = 0
        for post in reddit_posts:
            item = reddit_post_to_content_item(post)
            if not db.item_exists(item.source_id):
                all_items.append(item)
                reddit_count += 1
        logger.info(f"  -> {reddit_count} new Reddit posts (of {len(reddit_posts)} found)")

        # 3. Check Status Page (no v1.3.0 tracking - keep existing deduplication)
        logger.info("Checking Canvas Status Page...")
        status = StatusPageMonitor()
        incidents = status.get_recent_incidents()
        status_count = 0
        for incident in incidents:
            item = incident_to_content_item(incident)
            if not db.item_exists(item.source_id):
                all_items.append(item)
                status_count += 1
        logger.info(f"  -> {status_count} new status incidents (of {len(incidents)} found)")

        # 4. Enrich all items with LLM summaries
        logger.info("Enriching content with LLM...")
        enriched_items = processor.enrich_with_llm(all_items)
        logger.info(f"  -> Enriched {len(enriched_items)} items with summaries and topics")

        # 5. Generate RSS feed
        logger.info("Generating RSS feed...")
        feed_xml = rss_builder.create_feed(enriched_items)
        output_path = Path("output/feed.xml")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(feed_xml, encoding="utf-8")
        logger.info(f"  -> RSS feed written to {output_path}")

        # 6. Store Reddit/Status items in database for future deduplication
        # (Discussion and release/deploy items use separate change tracking tables)
        logger.info("Storing items in database...")
        stored_count = 0
        for item in enriched_items:
            # Only store Reddit/Status items in content_items table
            if not getattr(item, 'has_v130_badge', False):
                item_id = db.insert_item(item)
                if item_id > 0:
                    stored_count += 1
        db.record_feed_generation(len(enriched_items), feed_xml)
        logger.info(f"  -> Stored {stored_count} new Reddit/Status items in content_items table")

        # Log change tracking statistics (used for [NEW]/[UPDATE] badge detection)
        stats = db.get_tracking_stats()
        logger.info(f"  -> Change tracking: "
                    f"{stats['discussion_total']} discussions "
                    f"({stats['question_count']} Q&A, {stats['blog_count']} blog), "
                    f"{stats['feature_total']} features "
                    f"({stats['release_feature_count']} release, {stats['deploy_change_count']} deploy)")

        logger.info("=" * 50)
        logger.info(f"Aggregation complete! {len(enriched_items)} items in feed")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"Error during aggregation: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

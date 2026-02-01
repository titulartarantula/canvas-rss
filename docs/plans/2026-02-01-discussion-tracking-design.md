# Discussion Tracking Design (Q&A Forum & Blog)

**Date:** 2026-02-01
**Version:** v1.3.0
**Status:** Ready for implementation

## Problem Statement

The current Q&A and blog scraping treats all posts uniformly. Educational technologists can't distinguish between brand new questions vs. active discussions that just received helpful answers.

## Solution

Add `[NEW]`/`[UPDATE]` badges matching the Deploy Notes convention, where `[UPDATE]` indicates new comments since last scrape.

## Design Decisions

### 1. Update Trigger

`[UPDATE]` is triggered by **new comments/replies** on an existing post. This surfaces evolving discussions and answered questions.

### 2. RSS Entry Format

Single RSS entry with badge when activity is detected. The entry includes:
- Activity summary ("3 new replies")
- Preview of the latest comment

### 3. Badge Both States

Both new and updated posts receive badges:
- `[NEW]` - First time this post was scraped
- `[UPDATE]` - Existing post with new comments

### 4. Same Treatment for Q&A and Blog

Both content types use identical logic - no different thresholds or special handling.

### 5. Source ID Format

Extract numeric ID from URL path:
```
question_664587    (from /discussion/664587/...)
blog_664587        (from /blog/664587/...)
```

### 6. Database Tracking

Separate `discussion_tracking` table to store comment counts:
```sql
CREATE TABLE discussion_tracking (
    source_id TEXT PRIMARY KEY,
    post_type TEXT,           -- 'question' or 'blog'
    comment_count INTEGER,
    first_seen TEXT,          -- ISO timestamp
    last_checked TEXT         -- ISO timestamp
);
```

### 7. Fetch Latest Comment on Update

Only fetch the latest comment content when an update is detected (comment count increased). This minimizes page loads during normal runs.

### 8. First-Run Limits

Prevent initial feed flood by limiting new posts on first run:

| Type | First-run limit |
|------|-----------------|
| Q&A | 5 |
| Blog | 5 |
| Release Notes | 3 |
| Deploy Notes | 3 |

Posts beyond the limit are still tracked in the database (so they show as `[UPDATE]` if comments increase later), just not emitted to the initial feed.

## Data Model

### New Dataclass

```python
@dataclass
class DiscussionUpdate:
    post: CommunityPost
    is_new: bool                    # True = [NEW], False = [UPDATE]
    previous_comment_count: int     # 0 if new
    new_comment_count: int          # delta
    latest_comment: Optional[str]   # preview text (for updates)
```

### Source ID Extraction

```python
def extract_source_id(url: str, post_type: str) -> str:
    """Extract numeric ID from Instructure Community URL."""
    # URL format: /discussion/664587/... or /blog/664587/...
    match = re.search(r'/(discussion|blog)/(\d+)', url)
    if match:
        return f"{post_type}_{match.group(2)}"
    return f"{post_type}_{hash(url)}"
```

## Detection Logic

```python
def classify_posts(
    posts: List[CommunityPost],
    db: Database,
    first_run_limit: int = 5
) -> List[DiscussionUpdate]:

    results = []
    new_count = 0

    for post in posts:
        source_id = extract_source_id(post.url, post.post_type)
        tracked = db.get_discussion_tracking(source_id)

        if tracked is None:
            # Brand new post - apply first-run limit
            new_count += 1
            if new_count > first_run_limit:
                # Still track it, but don't emit to feed
                db.upsert_discussion_tracking(source_id, post.post_type, post.comments)
                continue

            results.append(DiscussionUpdate(
                post=post, is_new=True,
                previous_comment_count=0,
                new_comment_count=post.comments,
                latest_comment=None
            ))

        elif post.comments > tracked["comment_count"]:
            # Existing post with new comments
            latest_comment = scrape_latest_comment(post.url)
            results.append(DiscussionUpdate(
                post=post, is_new=False,
                previous_comment_count=tracked["comment_count"],
                new_comment_count=post.comments - tracked["comment_count"],
                latest_comment=latest_comment
            ))

        # Always update tracking
        db.upsert_discussion_tracking(source_id, post.post_type, post.comments)

    return results
```

## RSS Entry Format

### Title Format

| Type | Title Format |
|------|--------------|
| Q&A | `[NEW] - Question Forum - {title}` |
| Blog | `[NEW] - Blog - {title}` |
| Release Notes | `[NEW] {title}` |
| Deploy Notes | `[NEW] {title}` |

**Examples:**
```
[NEW] - Question Forum - How do I configure SSO for Canvas?
[UPDATE] - Question Forum - How do I configure SSO for Canvas?
[NEW] - Blog - Canvas Studio Updates for Spring 2026
[NEW] Canvas Release Notes (2026-02-01)
[UPDATE] Canvas Deploy Notes (2026-02-11)
```

### Title Construction

```python
SOURCE_LABELS = {
    "question": "Question Forum",
    "blog": "Blog",
    "release_note": "Release Notes",
    "deploy_note": "Deploy Notes",
}

def build_title(post: CommunityPost, is_new: bool) -> str:
    badge = "[NEW]" if is_new else "[UPDATE]"

    if post.post_type in ("question", "blog"):
        source = SOURCE_LABELS[post.post_type]
        return f"{badge} - {source} - {post.title}"
    else:
        # Release/Deploy notes are self-describing
        return f"{badge} {post.title}"
```

### [NEW] Entry Description

```
━━━ NEW QUESTION ━━━

[Original post content, truncated to ~500 chars]

Posted: 2026-02-01 | 0 comments
```

### [UPDATE] Entry Description

```
━━━ DISCUSSION UPDATE ━━━

+3 new comments (8 total)

▸ Latest reply:
"You need to enable the SIS integration first, then navigate
to Admin > Authentication and select SAML 2.0..."

───
Original question: "We're trying to set up SSO with Azure AD
but keep getting redirect errors..."
```

### Section Headers

```python
SECTION_HEADERS = {
    "question_new": "NEW QUESTION",
    "question_update": "DISCUSSION UPDATE",
    "blog_new": "NEW BLOG POST",
    "blog_update": "BLOG UPDATE",
}
```

## Latest Comment Scraping

```python
def scrape_latest_comment(url: str) -> Optional[str]:
    """Navigate to post page and extract most recent comment."""

    comment_selectors = [
        "[class*='comment']:last-child",
        "[class*='reply']:last-of-type",
        "[class*='message']:last-child",
        "[data-testid*='comment']:last-child",
    ]

    for selector in comment_selectors:
        element = page.query_selector(selector)
        if element:
            text = element.inner_text().strip()
            return text[:500] if len(text) > 500 else text

    return None

def format_latest_comment(comment: str, max_length: int = 300) -> str:
    """Format comment for RSS description."""
    if not comment:
        return ""

    if len(comment) > max_length:
        comment = comment[:max_length].rsplit(' ', 1)[0] + "..."

    return f'▸ Latest reply:\n"{comment}"'
```

**Edge cases:**
- Comment deleted before scrape → Return `None`, show "New activity" instead
- Comment is just emoji/reaction → Include as-is
- Very long code block → Truncate at 300 chars

## Implementation Plan

### Step 1: Database (`src/utils/database.py`)
- Add `discussion_tracking` table creation in schema
- Add `get_discussion_tracking(source_id) -> Optional[dict]`
- Add `upsert_discussion_tracking(source_id, post_type, comment_count)`
- Add `is_first_run() -> bool` (check if tracking table is empty)

### Step 2: Scraper (`src/scrapers/instructure_community.py`)
- Add `extract_source_id(url, post_type) -> str` helper
- Add `scrape_latest_comment(url) -> Optional[str]` method
- Add `DiscussionUpdate` dataclass

### Step 3: Content Processor (`src/processor/content_processor.py`)
- Add `classify_discussion_posts(posts, db, first_run_limit) -> List[DiscussionUpdate]`
- Reuse existing `sanitize_html()` and `redact_pii()` for comment content

### Step 4: RSS Builder (`src/generator/rss_builder.py`)
- Add `SOURCE_LABELS` constant
- Add `build_discussion_title(post, is_new) -> str`
- Add `format_discussion_entry(update: DiscussionUpdate) -> str`
- Update `CONTENT_TYPE_BADGES` for new types

### Step 5: Main Orchestration (`src/main.py`)
- Update Q&A/Blog scraping to use new classification flow
- Pass `first_run_limit` based on content type (5 for Q&A/Blog, 3 for Release/Deploy)
- Apply same pattern to Release/Deploy notes

## Testing Strategy

### Unit Tests
- `extract_source_id()` with various URL formats
- `classify_posts()` with new posts, updates, and no-change scenarios
- `build_title()` for all content types
- `format_latest_comment()` truncation
- First-run limit enforcement
- Database tracking operations

### Integration Tests
- Full flow with mock database (first run + subsequent run)
- Update detection with comment count changes
- RSS output format verification

## Summary of Key Decisions

| Decision | Choice |
|----------|--------|
| Update trigger | New comments |
| RSS format | Single entry with badge |
| Update content | Activity summary + latest reply preview |
| Badging | Both [NEW] and [UPDATE] |
| Q&A vs Blog | Same treatment |
| Source ID | `{type}_{numeric_id}` from URL |
| Tracking | Separate `discussion_tracking` table |
| Comment fetch | Only on update detection |
| First-run limits | Q&A/Blog: 5, Release/Deploy: 3 |
| Title format | `[BADGE] - Source - Title` (Q&A/Blog only) |

## Reference

- Related design: `docs/plans/2026-02-01-deploy-notes-parsing.md`
- Related design: `docs/plans/2026-02-01-release-notes-enhanced-parsing.md`
- Full spec: `specs/canvas-rss.md`

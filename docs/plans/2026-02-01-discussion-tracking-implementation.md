# Discussion Tracking Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `[NEW]`/`[UPDATE]` badges to Q&A and blog posts based on comment activity, with first-run limits to prevent feed flooding.

**Architecture:** Separate `discussion_tracking` table stores comment counts. On each run, compare current counts to stored values. New posts get `[NEW]` badge, posts with increased comments get `[UPDATE]` badge with latest reply preview.

**Tech Stack:** SQLite (tracking table), Playwright (comment scraping), Python dataclasses

---

## Task 1: Database - Add Discussion Tracking Table

**Files:**
- Modify: `src/utils/database.py:30-92` (schema section)
- Test: `tests/test_database.py`

**Step 1: Write the failing test for table creation**

Add to `tests/test_database.py`:

```python
class TestDiscussionTracking:
    """Tests for discussion tracking functionality."""

    def test_discussion_tracking_table_created(self, temp_db):
        """Test that discussion_tracking table is created on init."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='discussion_tracking'"
        )
        assert cursor.fetchone() is not None

    def test_discussion_tracking_schema(self, temp_db):
        """Test that discussion_tracking has correct columns."""
        conn = temp_db._get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(discussion_tracking)")
        columns = {row[1] for row in cursor.fetchall()}
        expected = {"source_id", "post_type", "comment_count", "first_seen", "last_checked"}
        assert expected == columns
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py::TestDiscussionTracking -v`
Expected: FAIL with "AssertionError" (table doesn't exist)

**Step 3: Add discussion_tracking table to schema**

In `src/utils/database.py`, add after the `feed_history` table creation (around line 90):

```python
        # Discussion tracking table for [NEW]/[UPDATE] badges
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS discussion_tracking (
                source_id TEXT PRIMARY KEY,
                post_type TEXT NOT NULL,
                comment_count INTEGER DEFAULT 0,
                first_seen TEXT NOT NULL,
                last_checked TEXT NOT NULL
            )
        """)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py::TestDiscussionTracking -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/utils/database.py tests/test_database.py
git commit -m "feat(db): add discussion_tracking table for [NEW]/[UPDATE] badges"
```

---

## Task 2: Database - Add get_discussion_tracking Method

**Files:**
- Modify: `src/utils/database.py`
- Test: `tests/test_database.py`

**Step 1: Write the failing test**

Add to `tests/test_database.py` in `TestDiscussionTracking`:

```python
    def test_get_discussion_tracking_returns_none_for_unknown(self, temp_db):
        """Test that get_discussion_tracking returns None for unknown source_id."""
        result = temp_db.get_discussion_tracking("unknown-id")
        assert result is None

    def test_get_discussion_tracking_returns_dict_after_upsert(self, temp_db):
        """Test that get_discussion_tracking returns data after upsert."""
        temp_db.upsert_discussion_tracking("question_123", "question", 5)
        result = temp_db.get_discussion_tracking("question_123")
        assert result is not None
        assert result["source_id"] == "question_123"
        assert result["post_type"] == "question"
        assert result["comment_count"] == 5
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py::TestDiscussionTracking::test_get_discussion_tracking_returns_none_for_unknown -v`
Expected: FAIL with "AttributeError: 'Database' object has no attribute 'get_discussion_tracking'"

**Step 3: Implement get_discussion_tracking**

Add to `src/utils/database.py` after `update_comment_count` method:

```python
    def get_discussion_tracking(self, source_id: str) -> Optional[dict]:
        """Get tracking data for a discussion post.

        Args:
            source_id: The unique source ID (e.g., 'question_664587').

        Returns:
            Dict with source_id, post_type, comment_count, first_seen, last_checked
            or None if not found.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT source_id, post_type, comment_count, first_seen, last_checked "
            "FROM discussion_tracking WHERE source_id = ?",
            (source_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py::TestDiscussionTracking::test_get_discussion_tracking_returns_none_for_unknown -v`
Expected: PASS (but the second test still fails - needs upsert)

**Step 5: Commit**

```bash
git add src/utils/database.py tests/test_database.py
git commit -m "feat(db): add get_discussion_tracking method"
```

---

## Task 3: Database - Add upsert_discussion_tracking Method

**Files:**
- Modify: `src/utils/database.py`
- Test: `tests/test_database.py`

**Step 1: Write the failing tests**

Add to `tests/test_database.py` in `TestDiscussionTracking`:

```python
    def test_upsert_discussion_tracking_creates_new_record(self, temp_db):
        """Test that upsert creates a new tracking record."""
        temp_db.upsert_discussion_tracking("blog_456", "blog", 3)
        result = temp_db.get_discussion_tracking("blog_456")
        assert result["comment_count"] == 3
        assert result["first_seen"] is not None
        assert result["last_checked"] is not None

    def test_upsert_discussion_tracking_updates_existing(self, temp_db):
        """Test that upsert updates comment_count but preserves first_seen."""
        temp_db.upsert_discussion_tracking("question_789", "question", 2)
        first_result = temp_db.get_discussion_tracking("question_789")
        first_seen = first_result["first_seen"]

        # Update with new comment count
        temp_db.upsert_discussion_tracking("question_789", "question", 5)
        updated = temp_db.get_discussion_tracking("question_789")

        assert updated["comment_count"] == 5
        assert updated["first_seen"] == first_seen  # Preserved
        assert updated["last_checked"] >= first_result["last_checked"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py::TestDiscussionTracking::test_upsert_discussion_tracking_creates_new_record -v`
Expected: FAIL with "AttributeError: 'Database' object has no attribute 'upsert_discussion_tracking'"

**Step 3: Implement upsert_discussion_tracking**

Add to `src/utils/database.py` after `get_discussion_tracking`:

```python
    def upsert_discussion_tracking(
        self, source_id: str, post_type: str, comment_count: int
    ) -> None:
        """Insert or update tracking data for a discussion post.

        On insert: Sets first_seen and last_checked to now.
        On update: Updates comment_count and last_checked, preserves first_seen.

        Args:
            source_id: The unique source ID (e.g., 'question_664587').
            post_type: Type of post ('question' or 'blog').
            comment_count: Current comment count.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        # Check if record exists
        existing = self.get_discussion_tracking(source_id)

        if existing:
            # Update: preserve first_seen, update comment_count and last_checked
            cursor.execute(
                "UPDATE discussion_tracking "
                "SET comment_count = ?, last_checked = ? "
                "WHERE source_id = ?",
                (comment_count, now, source_id)
            )
        else:
            # Insert: set both first_seen and last_checked to now
            cursor.execute(
                "INSERT INTO discussion_tracking "
                "(source_id, post_type, comment_count, first_seen, last_checked) "
                "VALUES (?, ?, ?, ?, ?)",
                (source_id, post_type, comment_count, now, now)
            )

        conn.commit()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py::TestDiscussionTracking -v`
Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add src/utils/database.py tests/test_database.py
git commit -m "feat(db): add upsert_discussion_tracking method"
```

---

## Task 4: Database - Add is_discussion_tracking_empty Method

**Files:**
- Modify: `src/utils/database.py`
- Test: `tests/test_database.py`

**Step 1: Write the failing tests**

Add to `tests/test_database.py` in `TestDiscussionTracking`:

```python
    def test_is_discussion_tracking_empty_returns_true_initially(self, temp_db):
        """Test that is_discussion_tracking_empty returns True for empty table."""
        assert temp_db.is_discussion_tracking_empty() is True

    def test_is_discussion_tracking_empty_returns_false_after_insert(self, temp_db):
        """Test that is_discussion_tracking_empty returns False after insert."""
        temp_db.upsert_discussion_tracking("question_123", "question", 0)
        assert temp_db.is_discussion_tracking_empty() is False
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py::TestDiscussionTracking::test_is_discussion_tracking_empty_returns_true_initially -v`
Expected: FAIL with "AttributeError"

**Step 3: Implement is_discussion_tracking_empty**

Add to `src/utils/database.py` after `upsert_discussion_tracking`:

```python
    def is_discussion_tracking_empty(self) -> bool:
        """Check if the discussion_tracking table is empty.

        Used to detect first run for first-run limits.

        Returns:
            True if table has no records, False otherwise.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM discussion_tracking")
        count = cursor.fetchone()[0]
        return count == 0
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py::TestDiscussionTracking -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/utils/database.py tests/test_database.py
git commit -m "feat(db): add is_discussion_tracking_empty for first-run detection"
```

---

## Task 5: Scraper - Add extract_source_id Helper

**Files:**
- Modify: `src/scrapers/instructure_community.py`
- Test: `tests/test_scrapers.py`

**Step 1: Write the failing tests**

Add new test class to `tests/test_scrapers.py`:

```python
class TestExtractSourceId:
    """Tests for extract_source_id helper function."""

    def test_extract_source_id_from_discussion_url(self):
        """Test extracting ID from discussion URL."""
        from scrapers.instructure_community import extract_source_id
        url = "https://community.instructure.com/en/discussion/664587/how-to-configure-sso"
        result = extract_source_id(url, "question")
        assert result == "question_664587"

    def test_extract_source_id_from_blog_url(self):
        """Test extracting ID from blog URL."""
        from scrapers.instructure_community import extract_source_id
        url = "https://community.instructure.com/en/blog/664752/canvas-studio-updates"
        result = extract_source_id(url, "blog")
        assert result == "blog_664752"

    def test_extract_source_id_fallback_to_hash(self):
        """Test fallback to hash for non-matching URL."""
        from scrapers.instructure_community import extract_source_id
        url = "https://example.com/some/other/path"
        result = extract_source_id(url, "question")
        assert result.startswith("question_")
        assert len(result) > 10  # Has hash suffix
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_scrapers.py::TestExtractSourceId -v`
Expected: FAIL with "ImportError: cannot import name 'extract_source_id'"

**Step 3: Implement extract_source_id**

Add to `src/scrapers/instructure_community.py` after the imports (around line 18):

```python
def extract_source_id(url: str, post_type: str) -> str:
    """Extract numeric ID from Instructure Community URL.

    Args:
        url: Full URL to a community post.
        post_type: Type of post ('question' or 'blog').

    Returns:
        Source ID in format '{post_type}_{numeric_id}' or '{post_type}_{hash}'.
    """
    # URL formats:
    # /discussion/664587/... or /blog/664587/...
    match = re.search(r'/(discussion|blog)/(\d+)', url)
    if match:
        return f"{post_type}_{match.group(2)}"
    # Fallback to hash
    return f"{post_type}_{abs(hash(url))}"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_scrapers.py::TestExtractSourceId -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/scrapers/instructure_community.py tests/test_scrapers.py
git commit -m "feat(scraper): add extract_source_id helper function"
```

---

## Task 6: Scraper - Add DiscussionUpdate Dataclass

**Files:**
- Modify: `src/scrapers/instructure_community.py`
- Test: `tests/test_scrapers.py`

**Step 1: Write the failing tests**

Add to `tests/test_scrapers.py`:

```python
class TestDiscussionUpdate:
    """Tests for DiscussionUpdate dataclass."""

    def test_discussion_update_new_post(self):
        """Test creating a DiscussionUpdate for a new post."""
        from scrapers.instructure_community import DiscussionUpdate, CommunityPost
        from datetime import datetime

        post = CommunityPost(
            title="Test Question",
            url="https://example.com/discussion/123",
            content="Content",
            published_date=datetime.now(),
            post_type="question"
        )

        update = DiscussionUpdate(
            post=post,
            is_new=True,
            previous_comment_count=0,
            new_comment_count=0,
            latest_comment=None
        )

        assert update.is_new is True
        assert update.previous_comment_count == 0
        assert update.latest_comment is None

    def test_discussion_update_existing_post_with_new_comments(self):
        """Test creating a DiscussionUpdate for an updated post."""
        from scrapers.instructure_community import DiscussionUpdate, CommunityPost
        from datetime import datetime

        post = CommunityPost(
            title="Test Question",
            url="https://example.com/discussion/123",
            content="Content",
            published_date=datetime.now(),
            comments=8,
            post_type="question"
        )

        update = DiscussionUpdate(
            post=post,
            is_new=False,
            previous_comment_count=5,
            new_comment_count=3,
            latest_comment="This is the latest reply text..."
        )

        assert update.is_new is False
        assert update.previous_comment_count == 5
        assert update.new_comment_count == 3
        assert "latest reply" in update.latest_comment
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_scrapers.py::TestDiscussionUpdate -v`
Expected: FAIL with "ImportError: cannot import name 'DiscussionUpdate'"

**Step 3: Implement DiscussionUpdate dataclass**

Add to `src/scrapers/instructure_community.py` after `CommunityPost` dataclass (around line 45):

```python
@dataclass
class DiscussionUpdate:
    """Represents a discussion post that is new or has new comments."""

    post: CommunityPost
    is_new: bool  # True = [NEW], False = [UPDATE]
    previous_comment_count: int  # 0 if new
    new_comment_count: int  # Number of new comments (delta)
    latest_comment: Optional[str]  # Preview text for updates, None for new posts
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_scrapers.py::TestDiscussionUpdate -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/scrapers/instructure_community.py tests/test_scrapers.py
git commit -m "feat(scraper): add DiscussionUpdate dataclass"
```

---

## Task 7: Scraper - Add scrape_latest_comment Method

**Files:**
- Modify: `src/scrapers/instructure_community.py`
- Test: `tests/test_scrapers.py`

**Step 1: Write the failing tests**

Add to `tests/test_scrapers.py`:

```python
class TestScrapeLatestComment:
    """Tests for scrape_latest_comment method."""

    def test_scrape_latest_comment_returns_none_when_browser_unavailable(self):
        """Test that scrape_latest_comment returns None without browser."""
        from scrapers.instructure_community import InstructureScraper

        # Create scraper without browser
        scraper = InstructureScraper.__new__(InstructureScraper)
        scraper.page = None

        result = scraper.scrape_latest_comment("https://example.com/discussion/123")
        assert result is None

    def test_scrape_latest_comment_truncates_long_comments(self, mocker):
        """Test that long comments are truncated to 500 chars."""
        from scrapers.instructure_community import InstructureScraper

        scraper = InstructureScraper.__new__(InstructureScraper)
        scraper.rate_limit_seconds = 0

        # Mock page with long comment
        mock_page = mocker.MagicMock()
        mock_element = mocker.MagicMock()
        mock_element.inner_text.return_value = "A" * 600  # 600 char comment
        mock_page.query_selector.return_value = mock_element
        mock_page.goto = mocker.MagicMock()
        mock_page.wait_for_load_state = mocker.MagicMock()
        scraper.page = mock_page

        result = scraper.scrape_latest_comment("https://example.com/discussion/123")
        assert result is not None
        assert len(result) == 500
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_scrapers.py::TestScrapeLatestComment -v`
Expected: FAIL with "AttributeError: 'InstructureScraper' object has no attribute 'scrape_latest_comment'"

**Step 3: Implement scrape_latest_comment method**

Add to `src/scrapers/instructure_community.py` in `InstructureScraper` class, after `_get_post_content`:

```python
    def scrape_latest_comment(self, url: str) -> Optional[str]:
        """Navigate to a post and extract the most recent comment.

        Args:
            url: URL of the community post.

        Returns:
            Text of the latest comment (max 500 chars), or None if unavailable.
        """
        if not self.page:
            logger.warning("Browser not available for scraping latest comment")
            return None

        try:
            self._rate_limit()
            self.page.goto(url, timeout=30000)
            self.page.wait_for_load_state("networkidle", timeout=15000)

            # Selectors for comment elements (last one = most recent)
            comment_selectors = [
                "[class*='comment']:last-child",
                "[class*='reply']:last-of-type",
                "[class*='message']:last-child",
                "[data-testid*='comment']:last-child",
                "[class*='Comment']:last-child",
                "[class*='Reply']:last-child",
            ]

            for selector in comment_selectors:
                try:
                    element = self.page.query_selector(selector)
                    if element:
                        text = element.inner_text().strip()
                        if text and len(text) > 10:  # Ignore empty/tiny elements
                            # Truncate to 500 chars
                            return text[:500] if len(text) > 500 else text
                except Exception:
                    continue

            logger.debug(f"Could not find comment on {url}")
            return None

        except PlaywrightTimeout:
            logger.warning(f"Timeout scraping latest comment from: {url}")
            return None
        except Exception as e:
            logger.error(f"Error scraping latest comment from {url}: {e}")
            return None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_scrapers.py::TestScrapeLatestComment -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/scrapers/instructure_community.py tests/test_scrapers.py
git commit -m "feat(scraper): add scrape_latest_comment method"
```

---

## Task 8: RSS Builder - Add SOURCE_LABELS and build_discussion_title

**Files:**
- Modify: `src/generator/rss_builder.py`
- Test: `tests/test_rss_builder.py`

**Step 1: Write the failing tests**

Add to `tests/test_rss_builder.py`:

```python
class TestDiscussionTitle:
    """Tests for discussion title formatting with [NEW]/[UPDATE] badges."""

    def test_build_discussion_title_new_question(self):
        """Test [NEW] badge for question forum posts."""
        from generator.rss_builder import build_discussion_title

        title = build_discussion_title("question", "How do I configure SSO?", is_new=True)
        assert title == "[NEW] - Question Forum - How do I configure SSO?"

    def test_build_discussion_title_update_question(self):
        """Test [UPDATE] badge for question forum posts."""
        from generator.rss_builder import build_discussion_title

        title = build_discussion_title("question", "How do I configure SSO?", is_new=False)
        assert title == "[UPDATE] - Question Forum - How do I configure SSO?"

    def test_build_discussion_title_new_blog(self):
        """Test [NEW] badge for blog posts."""
        from generator.rss_builder import build_discussion_title

        title = build_discussion_title("blog", "Canvas Studio Updates", is_new=True)
        assert title == "[NEW] - Blog - Canvas Studio Updates"

    def test_build_discussion_title_release_note_no_source_label(self):
        """Test release notes don't get source label (self-describing)."""
        from generator.rss_builder import build_discussion_title

        title = build_discussion_title("release_note", "Canvas Release Notes (2026-02-01)", is_new=True)
        assert title == "[NEW] Canvas Release Notes (2026-02-01)"

    def test_build_discussion_title_deploy_note_no_source_label(self):
        """Test deploy notes don't get source label (self-describing)."""
        from generator.rss_builder import build_discussion_title

        title = build_discussion_title("deploy_note", "Canvas Deploy Notes (2026-02-11)", is_new=False)
        assert title == "[UPDATE] Canvas Deploy Notes (2026-02-11)"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_rss_builder.py::TestDiscussionTitle -v`
Expected: FAIL with "ImportError: cannot import name 'build_discussion_title'"

**Step 3: Add SOURCE_LABELS and build_discussion_title**

Add to `src/generator/rss_builder.py` after the class constants (around line 100):

```python
# Source labels for title formatting (Q&A and Blog only)
SOURCE_LABELS = {
    "question": "Question Forum",
    "blog": "Blog",
    "release_note": "Release Notes",
    "deploy_note": "Deploy Notes",
}


def build_discussion_title(post_type: str, title: str, is_new: bool) -> str:
    """Build title with [NEW]/[UPDATE] badge and optional source label.

    Args:
        post_type: Type of post ('question', 'blog', 'release_note', 'deploy_note').
        title: Original post title.
        is_new: True for [NEW] badge, False for [UPDATE] badge.

    Returns:
        Formatted title string.
    """
    badge = "[NEW]" if is_new else "[UPDATE]"

    # Q&A and Blog get source labels; Release/Deploy notes are self-describing
    if post_type in ("question", "blog"):
        source = SOURCE_LABELS.get(post_type, "")
        return f"{badge} - {source} - {title}"
    else:
        return f"{badge} {title}"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_rss_builder.py::TestDiscussionTitle -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/generator/rss_builder.py tests/test_rss_builder.py
git commit -m "feat(rss): add SOURCE_LABELS and build_discussion_title function"
```

---

## Task 9: RSS Builder - Add format_discussion_description

**Files:**
- Modify: `src/generator/rss_builder.py`
- Test: `tests/test_rss_builder.py`

**Step 1: Write the failing tests**

Add to `tests/test_rss_builder.py`:

```python
class TestDiscussionDescription:
    """Tests for discussion description formatting."""

    def test_format_discussion_description_new_question(self):
        """Test description for new question."""
        from generator.rss_builder import format_discussion_description

        desc = format_discussion_description(
            post_type="question",
            is_new=True,
            content="How do I configure SSO with Azure AD?",
            comment_count=0,
            previous_comment_count=0,
            new_comment_count=0,
            latest_comment=None
        )

        assert "NEW QUESTION" in desc
        assert "How do I configure SSO" in desc

    def test_format_discussion_description_update_with_comment(self):
        """Test description for updated question with latest comment."""
        from generator.rss_builder import format_discussion_description

        desc = format_discussion_description(
            post_type="question",
            is_new=False,
            content="Original question content",
            comment_count=8,
            previous_comment_count=5,
            new_comment_count=3,
            latest_comment="You need to enable SIS integration first..."
        )

        assert "DISCUSSION UPDATE" in desc
        assert "+3 new comments" in desc
        assert "8 total" in desc
        assert "Latest reply" in desc
        assert "SIS integration" in desc

    def test_format_discussion_description_truncates_content(self):
        """Test that original content is truncated to 300 chars."""
        from generator.rss_builder import format_discussion_description

        long_content = "A" * 500

        desc = format_discussion_description(
            post_type="blog",
            is_new=True,
            content=long_content,
            comment_count=0,
            previous_comment_count=0,
            new_comment_count=0,
            latest_comment=None
        )

        # Content should be truncated
        assert len(desc) < 600  # Header + truncated content
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_rss_builder.py::TestDiscussionDescription -v`
Expected: FAIL with "ImportError"

**Step 3: Implement format_discussion_description**

Add to `src/generator/rss_builder.py` after `build_discussion_title`:

```python
# Section headers for RSS descriptions
SECTION_HEADERS = {
    "question_new": "NEW QUESTION",
    "question_update": "DISCUSSION UPDATE",
    "blog_new": "NEW BLOG POST",
    "blog_update": "BLOG UPDATE",
}


def format_discussion_description(
    post_type: str,
    is_new: bool,
    content: str,
    comment_count: int,
    previous_comment_count: int,
    new_comment_count: int,
    latest_comment: Optional[str]
) -> str:
    """Format RSS description for a discussion post.

    Args:
        post_type: Type of post ('question' or 'blog').
        is_new: True for new post, False for update.
        content: Original post content.
        comment_count: Current total comment count.
        previous_comment_count: Comment count from last check.
        new_comment_count: Number of new comments.
        latest_comment: Preview of latest comment (for updates).

    Returns:
        Formatted description string.
    """
    key = f"{post_type}_{'new' if is_new else 'update'}"
    header = SECTION_HEADERS.get(key, "UPDATE")

    parts = [f"━━━ {header} ━━━", ""]

    if is_new:
        # New post: show truncated content
        truncated = content[:300] if len(content) > 300 else content
        if len(content) > 300:
            truncated = truncated.rsplit(' ', 1)[0] + "..."
        parts.append(truncated)
        parts.append("")
        parts.append(f"Posted: {comment_count} comments")
    else:
        # Update: show activity summary + latest comment
        parts.append(f"+{new_comment_count} new comments ({comment_count} total)")
        parts.append("")

        if latest_comment:
            # Truncate latest comment to 300 chars
            comment_preview = latest_comment[:300]
            if len(latest_comment) > 300:
                comment_preview = comment_preview.rsplit(' ', 1)[0] + "..."
            parts.append(f"▸ Latest reply:")
            parts.append(f'"{comment_preview}"')
            parts.append("")

        # Show truncated original content
        parts.append("───")
        truncated = content[:200] if len(content) > 200 else content
        if len(content) > 200:
            truncated = truncated.rsplit(' ', 1)[0] + "..."
        parts.append(f"Original: {truncated}")

    return "\n".join(parts)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_rss_builder.py::TestDiscussionDescription -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/generator/rss_builder.py tests/test_rss_builder.py
git commit -m "feat(rss): add format_discussion_description function"
```

---

## Task 10: Content Processor - Add classify_discussion_posts

**Files:**
- Modify: `src/processor/content_processor.py`
- Test: `tests/test_processor.py`

**Step 1: Write the failing tests**

Add to `tests/test_processor.py`:

```python
class TestClassifyDiscussionPosts:
    """Tests for classify_discussion_posts function."""

    def test_classify_new_post(self, temp_db):
        """Test that unknown posts are classified as new."""
        from processor.content_processor import ContentItem
        from scrapers.instructure_community import CommunityPost, classify_discussion_posts
        from datetime import datetime

        posts = [
            CommunityPost(
                title="New Question",
                url="https://community.instructure.com/en/discussion/999/test",
                content="Content",
                published_date=datetime.now(),
                comments=3,
                post_type="question"
            )
        ]

        results = classify_discussion_posts(posts, temp_db, first_run_limit=5)

        assert len(results) == 1
        assert results[0].is_new is True
        assert results[0].new_comment_count == 3

    def test_classify_updated_post(self, temp_db):
        """Test that posts with new comments are classified as updates."""
        from scrapers.instructure_community import CommunityPost, classify_discussion_posts
        from datetime import datetime

        # Pre-populate tracking with lower comment count
        temp_db.upsert_discussion_tracking("question_888", "question", 5)

        posts = [
            CommunityPost(
                title="Existing Question",
                url="https://community.instructure.com/en/discussion/888/test",
                content="Content",
                published_date=datetime.now(),
                comments=8,  # 3 new comments
                post_type="question"
            )
        ]

        results = classify_discussion_posts(posts, temp_db, first_run_limit=5)

        assert len(results) == 1
        assert results[0].is_new is False
        assert results[0].previous_comment_count == 5
        assert results[0].new_comment_count == 3

    def test_classify_no_change_skipped(self, temp_db):
        """Test that posts with no comment change are skipped."""
        from scrapers.instructure_community import CommunityPost, classify_discussion_posts
        from datetime import datetime

        # Pre-populate with same comment count
        temp_db.upsert_discussion_tracking("question_777", "question", 5)

        posts = [
            CommunityPost(
                title="Unchanged Question",
                url="https://community.instructure.com/en/discussion/777/test",
                content="Content",
                published_date=datetime.now(),
                comments=5,  # No change
                post_type="question"
            )
        ]

        results = classify_discussion_posts(posts, temp_db, first_run_limit=5)

        assert len(results) == 0  # Skipped

    def test_first_run_limit_enforced(self, temp_db):
        """Test that first-run limit caps new posts."""
        from scrapers.instructure_community import CommunityPost, classify_discussion_posts
        from datetime import datetime

        posts = [
            CommunityPost(
                title=f"Question {i}",
                url=f"https://community.instructure.com/en/discussion/{i}/test",
                content="Content",
                published_date=datetime.now(),
                comments=0,
                post_type="question"
            )
            for i in range(10)  # 10 new posts
        ]

        results = classify_discussion_posts(posts, temp_db, first_run_limit=3)

        # Only 3 should be in results, but all 10 should be tracked
        assert len(results) == 3
        # Verify all are tracked
        for i in range(10):
            tracked = temp_db.get_discussion_tracking(f"question_{i}")
            assert tracked is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_processor.py::TestClassifyDiscussionPosts -v`
Expected: FAIL with "ImportError"

**Step 3: Implement classify_discussion_posts**

Add to `src/scrapers/instructure_community.py` at module level, after `extract_source_id`:

```python
def classify_discussion_posts(
    posts: List[CommunityPost],
    db: "Database",
    first_run_limit: int = 5,
    scraper: Optional["InstructureScraper"] = None
) -> List[DiscussionUpdate]:
    """Classify posts as new or updated based on comment tracking.

    Args:
        posts: List of CommunityPost objects to classify.
        db: Database instance for tracking.
        first_run_limit: Max new posts to include on first run.
        scraper: Optional InstructureScraper for fetching latest comments.

    Returns:
        List of DiscussionUpdate objects for posts to include in feed.
    """
    from utils.database import Database  # Import here to avoid circular

    results = []
    new_count = 0

    for post in posts:
        source_id = extract_source_id(post.url, post.post_type)
        tracked = db.get_discussion_tracking(source_id)

        if tracked is None:
            # Brand new post
            new_count += 1
            if new_count > first_run_limit:
                # Track but don't emit to feed
                db.upsert_discussion_tracking(source_id, post.post_type, post.comments)
                logger.debug(f"Tracking (over limit): {source_id}")
                continue

            results.append(DiscussionUpdate(
                post=post,
                is_new=True,
                previous_comment_count=0,
                new_comment_count=post.comments,
                latest_comment=None
            ))
            logger.info(f"[NEW] {post.post_type}: {post.title[:50]}...")

        elif post.comments > tracked["comment_count"]:
            # Existing post with new comments
            new_comments = post.comments - tracked["comment_count"]

            # Fetch latest comment if scraper available
            latest_comment = None
            if scraper:
                latest_comment = scraper.scrape_latest_comment(post.url)

            results.append(DiscussionUpdate(
                post=post,
                is_new=False,
                previous_comment_count=tracked["comment_count"],
                new_comment_count=new_comments,
                latest_comment=latest_comment
            ))
            logger.info(
                f"[UPDATE] {post.post_type}: {post.title[:50]}... "
                f"(+{new_comments} comments)"
            )

        # Always update tracking
        db.upsert_discussion_tracking(source_id, post.post_type, post.comments)

    return results
```

Also add the TYPE_CHECKING import at the top of the file:

```python
if TYPE_CHECKING:
    from utils.database import Database
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_processor.py::TestClassifyDiscussionPosts -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/scrapers/instructure_community.py tests/test_processor.py
git commit -m "feat(scraper): add classify_discussion_posts function"
```

---

## Task 11: Main - Integrate Discussion Tracking

**Files:**
- Modify: `src/main.py`
- Test: `tests/test_main.py`

**Step 1: Write the failing tests**

Add to `tests/test_main.py`:

```python
class TestDiscussionTracking:
    """Tests for discussion tracking integration in main."""

    def test_first_run_limits_applied(self, temp_db, mocker):
        """Test that first-run limits are applied correctly."""
        from scrapers.instructure_community import CommunityPost, classify_discussion_posts
        from datetime import datetime

        # Simulate 10 Q&A posts
        posts = [
            CommunityPost(
                title=f"Question {i}",
                url=f"https://community.instructure.com/en/discussion/{i}/test",
                content="Content",
                published_date=datetime.now(),
                comments=0,
                post_type="question"
            )
            for i in range(10)
        ]

        # Q&A limit is 5
        results = classify_discussion_posts(posts, temp_db, first_run_limit=5)
        assert len(results) == 5

    def test_updates_detected_on_subsequent_run(self, temp_db):
        """Test that updates are detected on subsequent runs."""
        from scrapers.instructure_community import CommunityPost, classify_discussion_posts
        from datetime import datetime

        # First run: add a post
        posts = [
            CommunityPost(
                title="Question",
                url="https://community.instructure.com/en/discussion/100/test",
                content="Content",
                published_date=datetime.now(),
                comments=2,
                post_type="question"
            )
        ]
        results1 = classify_discussion_posts(posts, temp_db, first_run_limit=5)
        assert len(results1) == 1
        assert results1[0].is_new is True

        # Second run: same post with more comments
        posts[0].comments = 5
        results2 = classify_discussion_posts(posts, temp_db, first_run_limit=5)
        assert len(results2) == 1
        assert results2[0].is_new is False
        assert results2[0].new_comment_count == 3
```

**Step 2: Run test to verify it passes (should pass with existing implementation)**

Run: `pytest tests/test_main.py::TestDiscussionTracking -v`
Expected: PASS

**Step 3: Update main.py to use classify_discussion_posts**

Modify `src/main.py` to integrate the new tracking. Add import:

```python
from scrapers.instructure_community import (
    InstructureScraper,
    CommunityPost,
    ReleaseNote,
    ChangeLogEntry,
    classify_discussion_posts,
    DiscussionUpdate,
)
```

Then update the main processing section (around line 178-215) to use classification:

```python
        # 4. Process discussion content (Q&A and Blog) with tracking
        logger.info("Processing discussion content...")

        # Filter to discussion types
        discussion_items = [
            item for item in all_items
            if item.content_type in ("question", "blog")
        ]
        other_items = [
            item for item in all_items
            if item.content_type not in ("question", "blog")
        ]

        # Convert back to CommunityPost for classification
        discussion_posts = []
        for item in discussion_items:
            # Recreate CommunityPost from ContentItem
            post = CommunityPost(
                title=item.title,
                url=item.url,
                content=item.content,
                published_date=item.published_date,
                comments=item.comment_count,
                post_type=item.content_type
            )
            discussion_posts.append(post)

        # Determine first-run limits
        qa_limit = 5
        blog_limit = 5

        # Classify Q&A posts
        qa_posts = [p for p in discussion_posts if p.post_type == "question"]
        qa_updates = classify_discussion_posts(qa_posts, db, first_run_limit=qa_limit)

        # Classify Blog posts
        blog_posts = [p for p in discussion_posts if p.post_type == "blog"]
        blog_updates = classify_discussion_posts(blog_posts, db, first_run_limit=blog_limit)

        # Convert DiscussionUpdate back to ContentItem with proper badges
        items_to_process = list(other_items)  # Start with non-discussion items

        for update in qa_updates + blog_updates:
            item = community_post_to_content_item(update.post)
            if not update.is_new:
                # Mark as updated type for different summarization
                item.content_type = f"{update.post.post_type}_updated"
            items_to_process.append(item)

        logger.info(
            f"  -> {len(qa_updates)} Q&A items, {len(blog_updates)} blog items "
            f"({len([u for u in qa_updates + blog_updates if u.is_new])} new, "
            f"{len([u for u in qa_updates + blog_updates if not u.is_new])} updated)"
        )
```

**Step 4: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests pass

**Step 5: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat(main): integrate discussion tracking with [NEW]/[UPDATE] badges"
```

---

## Task 12: Integration Test - Full Flow

**Files:**
- Test: `tests/test_main.py`

**Step 1: Write integration test**

Add to `tests/test_main.py`:

```python
class TestDiscussionTrackingIntegration:
    """Integration tests for full discussion tracking flow."""

    def test_full_flow_first_run_then_update(self, temp_db):
        """Test complete flow: first run captures new, second run detects updates."""
        from scrapers.instructure_community import (
            CommunityPost, classify_discussion_posts, DiscussionUpdate
        )
        from datetime import datetime

        # Simulate first run with 7 Q&A posts (limit 5)
        qa_posts = [
            CommunityPost(
                title=f"Question {i}",
                url=f"https://community.instructure.com/en/discussion/{i}/test",
                content=f"Content for question {i}",
                published_date=datetime.now(),
                comments=i,  # Different comment counts
                post_type="question"
            )
            for i in range(7)
        ]

        # First run
        results1 = classify_discussion_posts(qa_posts, temp_db, first_run_limit=5)

        assert len(results1) == 5  # Limited to 5
        assert all(r.is_new for r in results1)  # All marked as new

        # Verify all 7 are tracked
        for i in range(7):
            tracked = temp_db.get_discussion_tracking(f"question_{i}")
            assert tracked is not None
            assert tracked["comment_count"] == i

        # Second run: posts 0, 1, 2 have new comments
        qa_posts[0].comments = 5  # Was 0, now 5
        qa_posts[1].comments = 10  # Was 1, now 10
        qa_posts[2].comments = 2  # Was 2, unchanged

        results2 = classify_discussion_posts(qa_posts, temp_db, first_run_limit=5)

        # Should have 2 updates (posts 0 and 1)
        assert len(results2) == 2
        assert all(not r.is_new for r in results2)

        # Verify comment deltas
        update_by_url = {r.post.url: r for r in results2}
        assert update_by_url["https://community.instructure.com/en/discussion/0/test"].new_comment_count == 5
        assert update_by_url["https://community.instructure.com/en/discussion/1/test"].new_comment_count == 9
```

**Step 2: Run test**

Run: `pytest tests/test_main.py::TestDiscussionTrackingIntegration -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_main.py
git commit -m "test: add integration test for discussion tracking flow"
```

---

## Task 13: Run Full Test Suite

**Step 1: Run all tests**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests pass (270+ tests)

**Step 2: If any failures, debug and fix**

Review any failures, fix issues, run tests again.

**Step 3: Final commit**

```bash
git add -A
git commit -m "chore: complete discussion tracking implementation"
```

---

## Summary

| Task | Description | Files Modified |
|------|-------------|----------------|
| 1 | Add discussion_tracking table | database.py, test_database.py |
| 2 | Add get_discussion_tracking | database.py, test_database.py |
| 3 | Add upsert_discussion_tracking | database.py, test_database.py |
| 4 | Add is_discussion_tracking_empty | database.py, test_database.py |
| 5 | Add extract_source_id | instructure_community.py, test_scrapers.py |
| 6 | Add DiscussionUpdate dataclass | instructure_community.py, test_scrapers.py |
| 7 | Add scrape_latest_comment | instructure_community.py, test_scrapers.py |
| 8 | Add build_discussion_title | rss_builder.py, test_rss_builder.py |
| 9 | Add format_discussion_description | rss_builder.py, test_rss_builder.py |
| 10 | Add classify_discussion_posts | instructure_community.py, test_processor.py |
| 11 | Integrate in main.py | main.py, test_main.py |
| 12 | Integration test | test_main.py |
| 13 | Full test suite | - |

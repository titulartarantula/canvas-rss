# Discussion Feature References Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Link Q&A and blog posts to Canvas features via `content_feature_refs` using hybrid keyword + LLM matching.

**Architecture:** Extract feature references from post title/content by first matching against existing `feature_options`, then `CANVAS_FEATURES`, with LLM fallback. Q&A posts use `'questions'` mention_type, blog posts use `'announces'` on first scrape and `'discusses'` on updates.

**Tech Stack:** Python 3.11, SQLite, Gemini API (LLM fallback), pytest

---

## Task 1: Add 'mentions' to MENTION_TYPES

**Files:**
- Modify: `src/constants.py:100-105`
- Test: Manual verification (constant only)

**Step 1: Add the new mention type**

In `src/constants.py`, update `MENTION_TYPES`:

```python
MENTION_TYPES = {
    'announces',   # Content announces this feature/option
    'discusses',   # Content discusses/explains
    'questions',   # Content asks about
    'feedback',    # Content provides feedback/complaints
    'mentions',    # Weak signal - content-only match or LLM extraction
}
```

**Step 2: Commit**

```bash
git add src/constants.py
git commit -m "feat: add 'mentions' to MENTION_TYPES for weak feature references"
```

---

## Task 2: Add get_all_feature_options() to Database

**Files:**
- Modify: `src/utils/database.py`
- Test: `tests/test_database.py`

**Step 1: Write the failing test**

Add to `tests/test_database.py`:

```python
class TestFeatureOptions:
    """Tests for feature option methods."""

    def test_get_all_feature_options_empty(self, temp_db):
        """Test get_all_feature_options returns empty list when no options exist."""
        options = temp_db.get_all_feature_options()
        assert options == []

    def test_get_all_feature_options_returns_options_with_canonical_name(self, temp_db):
        """Test get_all_feature_options returns options that have canonical_name."""
        # Seed features first
        temp_db.seed_features()

        # Insert option with canonical_name
        temp_db.upsert_feature_option(
            option_id="doc_processor",
            feature_id="assignments",
            name="Document Processor",
            canonical_name="Document Processor",
            status="preview",
        )

        # Insert option without canonical_name (should not be returned)
        temp_db.upsert_feature_option(
            option_id="some_legacy_option",
            feature_id="gradebook",
            name="Legacy Option",
            canonical_name=None,
            status="released",
        )

        options = temp_db.get_all_feature_options()

        assert len(options) == 1
        assert options[0]["option_id"] == "doc_processor"
        assert options[0]["canonical_name"] == "Document Processor"
        assert options[0]["feature_id"] == "assignments"

    def test_get_all_feature_options_includes_name_field(self, temp_db):
        """Test that returned options include name field for fallback matching."""
        temp_db.seed_features()
        temp_db.upsert_feature_option(
            option_id="new_quizzes_logs",
            feature_id="new_quizzes",
            name="New Quizzes Build Logs",
            canonical_name="New Quizzes Build Logs",
            status="optional",
        )

        options = temp_db.get_all_feature_options()

        assert options[0]["name"] == "New Quizzes Build Logs"
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_database.py::TestFeatureOptions -v
```

Expected: FAIL with `AttributeError: 'Database' object has no attribute 'get_all_feature_options'`

**Step 3: Write minimal implementation**

Add to `src/utils/database.py` after `get_active_feature_options()`:

```python
def get_all_feature_options(self) -> List[dict]:
    """Get all feature options that have canonical names for matching.

    Returns:
        List of dicts with option_id, feature_id, canonical_name, name.
    """
    conn = self._get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT option_id, feature_id, canonical_name, name
        FROM feature_options
        WHERE canonical_name IS NOT NULL AND canonical_name != ''
        ORDER BY canonical_name
    """)
    return [dict(row) for row in cursor.fetchall()]
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_database.py::TestFeatureOptions -v
```

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/utils/database.py tests/test_database.py
git commit -m "feat(database): add get_all_feature_options() for content matching"
```

---

## Task 3: Add extract_features_with_llm() to ContentProcessor

**Files:**
- Modify: `src/processor/content_processor.py`
- Test: `tests/test_processor.py`

**Step 1: Write the failing tests**

Add to `tests/test_processor.py`:

```python
class TestExtractFeaturesWithLLM:
    """Tests for LLM-based feature extraction."""

    def test_extract_features_with_llm_no_model_returns_empty(self):
        """Test that extract_features_with_llm returns empty list when no model."""
        from processor.content_processor import ContentProcessor
        processor = ContentProcessor(api_key=None)

        result = processor.extract_features_with_llm(
            title="Help with something",
            content="I need help with my course"
        )

        assert result == []

    def test_extract_features_with_llm_empty_content_returns_empty(self):
        """Test that empty content returns empty list."""
        from processor.content_processor import ContentProcessor
        processor = ContentProcessor(api_key=None)

        result = processor.extract_features_with_llm(title="", content="")
        assert result == []

        result = processor.extract_features_with_llm(title=None, content=None)
        assert result == []

    def test_extract_features_with_llm_parses_response(self, mocker):
        """Test that LLM response is parsed into feature list."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor(api_key="fake-key")

        # Mock the model
        mock_model = mocker.MagicMock()
        mock_response = mocker.MagicMock()
        mock_response.text = "Gradebook\nSpeedGrader\nAssignments"
        mock_model.generate_content.return_value = mock_response
        processor.model = mock_model

        result = processor.extract_features_with_llm(
            title="Grading issues",
            content="I'm having trouble with grades in SpeedGrader"
        )

        assert result == ["Gradebook", "SpeedGrader", "Assignments"]

    def test_extract_features_with_llm_handles_none_response(self, mocker):
        """Test that 'none' response returns empty list."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor(api_key="fake-key")

        mock_model = mocker.MagicMock()
        mock_response = mocker.MagicMock()
        mock_response.text = "none"
        mock_model.generate_content.return_value = mock_response
        processor.model = mock_model

        result = processor.extract_features_with_llm(
            title="General question",
            content="How do I use Canvas?"
        )

        assert result == []

    def test_extract_features_with_llm_handles_api_error(self, mocker):
        """Test that API errors return empty list."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor(api_key="fake-key")

        mock_model = mocker.MagicMock()
        mock_model.generate_content.side_effect = Exception("API error")
        processor.model = mock_model

        result = processor.extract_features_with_llm(
            title="Test",
            content="Test content"
        )

        assert result == []

    def test_extract_features_with_llm_filters_empty_lines(self, mocker):
        """Test that empty lines in response are filtered out."""
        from processor.content_processor import ContentProcessor

        processor = ContentProcessor(api_key="fake-key")

        mock_model = mocker.MagicMock()
        mock_response = mocker.MagicMock()
        mock_response.text = "Gradebook\n\n  \nAssignments\n"
        mock_model.generate_content.return_value = mock_response
        processor.model = mock_model

        result = processor.extract_features_with_llm(
            title="Test",
            content="Test content"
        )

        assert result == ["Gradebook", "Assignments"]
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_processor.py::TestExtractFeaturesWithLLM -v
```

Expected: FAIL with `AttributeError: 'ContentProcessor' object has no attribute 'extract_features_with_llm'`

**Step 3: Write minimal implementation**

Add to `src/processor/content_processor.py`:

```python
def extract_features_with_llm(self, title: str, content: str) -> List[str]:
    """Use LLM to extract Canvas feature names from content.

    Args:
        title: Post title.
        content: Post content.

    Returns:
        List of feature names mentioned (may not be canonical).
    """
    if not title and not content:
        return []

    if not self.model:
        return []

    combined = f"{title or ''}\n{content or ''}"[:1500]

    prompt = """Extract Canvas LMS feature names mentioned in this post.
Return only feature names, one per line. Examples: Gradebook, New Quizzes, SpeedGrader, Assignments, Modules, Pages, Discussions, Rubrics, Calendar, Inbox.
If no Canvas features are mentioned, return "none".

Post:
""" + combined

    try:
        response = self.model.generate_content(prompt)
        text = response.text.strip().lower()

        if text == "none":
            return []

        # Parse lines, filter empty, strip whitespace
        features = [
            line.strip().title()
            for line in response.text.strip().split('\n')
            if line.strip() and line.strip().lower() != "none"
        ]

        return features

    except Exception as e:
        logger.warning(f"LLM feature extraction failed: {e}")
        return []
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_processor.py::TestExtractFeaturesWithLLM -v
```

Expected: PASS (6 tests)

**Step 5: Commit**

```bash
git add src/processor/content_processor.py tests/test_processor.py
git commit -m "feat(processor): add extract_features_with_llm() for fallback matching"
```

---

## Task 4: Add extract_feature_refs() function

**Files:**
- Modify: `src/scrapers/instructure_community.py`
- Test: `tests/test_scrapers.py`

**Step 1: Write the failing tests**

Add to `tests/test_scrapers.py`:

```python
class TestExtractFeatureRefs:
    """Tests for extract_feature_refs function."""

    def test_extract_feature_refs_matches_feature_option_in_title(self, temp_db):
        """Test that canonical option names in title are matched."""
        from scrapers.instructure_community import extract_feature_refs

        # Setup: seed features and add an option
        temp_db.seed_features()
        temp_db.upsert_feature_option(
            option_id="enhanced_gradebook_filters",
            feature_id="gradebook",
            name="Enhanced Gradebook Filters",
            canonical_name="Enhanced Gradebook Filters",
            status="preview",
        )

        refs = extract_feature_refs(
            title="Problems with Enhanced Gradebook Filters",
            content="The filters are not working correctly.",
            db=temp_db,
            post_type="question",
            is_new=True,
        )

        # Should match the option with 'questions' type (Q&A post)
        assert len(refs) >= 1
        option_ref = next((r for r in refs if r[1] == "enhanced_gradebook_filters"), None)
        assert option_ref is not None
        assert option_ref[0] == "gradebook"  # feature_id
        assert option_ref[2] == "questions"  # mention_type

    def test_extract_feature_refs_matches_feature_in_content(self, temp_db):
        """Test that feature names in content get 'mentions' type."""
        from scrapers.instructure_community import extract_feature_refs

        temp_db.seed_features()

        refs = extract_feature_refs(
            title="Help needed",
            content="I'm having trouble with SpeedGrader and the Gradebook.",
            db=temp_db,
            post_type="question",
            is_new=True,
        )

        # Should match features with 'mentions' type (content only)
        feature_ids = [r[0] for r in refs]
        assert "speedgrader" in feature_ids or "gradebook" in feature_ids

    def test_extract_feature_refs_blog_first_scrape_uses_announces(self, temp_db):
        """Test that blog posts on first scrape use 'announces' mention_type."""
        from scrapers.instructure_community import extract_feature_refs

        temp_db.seed_features()

        refs = extract_feature_refs(
            title="New Quizzes Update",
            content="We're excited to announce improvements to New Quizzes.",
            db=temp_db,
            post_type="blog",
            is_new=True,
        )

        # Blog first scrape should use 'announces'
        assert any(r[2] == "announces" for r in refs)

    def test_extract_feature_refs_blog_update_uses_discusses(self, temp_db):
        """Test that blog post updates use 'discusses' mention_type."""
        from scrapers.instructure_community import extract_feature_refs

        temp_db.seed_features()

        refs = extract_feature_refs(
            title="New Quizzes Update",
            content="We're excited to announce improvements to New Quizzes.",
            db=temp_db,
            post_type="blog",
            is_new=False,  # Not first scrape
        )

        # Blog update should use 'discusses' not 'announces'
        assert not any(r[2] == "announces" for r in refs)
        assert any(r[2] in ("discusses", "mentions") for r in refs)

    def test_extract_feature_refs_no_match_returns_general(self, temp_db):
        """Test that no matches returns link to 'general' feature."""
        from scrapers.instructure_community import extract_feature_refs

        temp_db.seed_features()

        refs = extract_feature_refs(
            title="Random question",
            content="Something completely unrelated to Canvas features.",
            db=temp_db,
            post_type="question",
            is_new=True,
            processor=None,  # No LLM fallback
        )

        # Should fall back to 'general'
        assert len(refs) == 1
        assert refs[0][0] == "general"
        assert refs[0][1] is None
        assert refs[0][2] == "mentions"

    def test_extract_feature_refs_deduplicates_keeps_strongest(self, temp_db):
        """Test that duplicate feature refs are deduplicated, keeping strongest mention_type."""
        from scrapers.instructure_community import extract_feature_refs

        temp_db.seed_features()
        temp_db.upsert_feature_option(
            option_id="new_quizzes_logs",
            feature_id="new_quizzes",
            name="New Quizzes Build Logs",
            canonical_name="New Quizzes Build Logs",
            status="optional",
        )

        # Title mentions "New Quizzes" (feature) and content mentions it too
        refs = extract_feature_refs(
            title="New Quizzes problems",
            content="I'm having issues with New Quizzes in my course.",
            db=temp_db,
            post_type="question",
            is_new=True,
        )

        # Should only have one ref to new_quizzes, with strongest type
        new_quizzes_refs = [r for r in refs if r[0] == "new_quizzes"]
        assert len(new_quizzes_refs) == 1

    def test_extract_feature_refs_multiple_features(self, temp_db):
        """Test that multiple different features create multiple refs."""
        from scrapers.instructure_community import extract_feature_refs

        temp_db.seed_features()

        refs = extract_feature_refs(
            title="SpeedGrader and Rubrics question",
            content="How do rubrics work in SpeedGrader?",
            db=temp_db,
            post_type="question",
            is_new=True,
        )

        feature_ids = [r[0] for r in refs]
        # Should have refs to both features
        assert "speedgrader" in feature_ids
        assert "rubrics" in feature_ids
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_scrapers.py::TestExtractFeatureRefs -v
```

Expected: FAIL with `ImportError: cannot import name 'extract_feature_refs'`

**Step 3: Write minimal implementation**

Add to `src/scrapers/instructure_community.py` after the `_slugify()` function:

```python
# Mention type priority (lower index = stronger)
MENTION_TYPE_PRIORITY = ['announces', 'questions', 'discusses', 'feedback', 'mentions']


def extract_feature_refs(
    title: str,
    content: str,
    db: "Database",
    post_type: str,
    is_new: bool,
    processor: Optional["ContentProcessor"] = None,
) -> List[Tuple[str, Optional[str], str]]:
    """Extract feature references from post title and content.

    Args:
        title: Post title.
        content: Post content.
        db: Database instance for querying existing feature_options.
        post_type: 'question' or 'blog'.
        is_new: True if first scrape, False if update (new comments).
        processor: Optional ContentProcessor for LLM fallback.

    Returns:
        List of (feature_id, option_id, mention_type) tuples.
    """
    from src.constants import CANVAS_FEATURES

    refs: List[Tuple[str, Optional[str], str]] = []
    title_lower = (title or "").lower()
    content_lower = (content or "").lower()
    combined_lower = f"{title_lower} {content_lower}"

    # Determine base mention_type based on post_type and is_new
    if post_type == "blog" and is_new:
        title_mention_type = "announces"
        content_mention_type = "announces"
    elif post_type == "question":
        title_mention_type = "questions"
        content_mention_type = "mentions"
    else:
        # Blog update or other
        title_mention_type = "discusses"
        content_mention_type = "mentions"

    # 1. Match against existing feature_options
    existing_options = db.get_all_feature_options()
    for option in existing_options:
        canonical = (option.get("canonical_name") or "").lower()
        name = (option.get("name") or "").lower()

        if not canonical and not name:
            continue

        match_text = canonical or name

        if match_text in title_lower:
            refs.append((option["feature_id"], option["option_id"], title_mention_type))
        elif match_text in content_lower:
            refs.append((option["feature_id"], option["option_id"], content_mention_type))

    # 2. Match against CANVAS_FEATURES
    for feature_id, feature_name in CANVAS_FEATURES.items():
        feature_name_lower = feature_name.lower()

        if feature_name_lower in title_lower or feature_id in title_lower:
            refs.append((feature_id, None, title_mention_type))
        elif feature_name_lower in content_lower or feature_id in content_lower:
            refs.append((feature_id, None, content_mention_type))

    # 3. LLM fallback if no matches and processor available
    if not refs and processor:
        try:
            llm_features = processor.extract_features_with_llm(title, content)
            for feat in llm_features:
                # Try to match LLM output to canonical feature
                matched_id = _match_feature_id(feat, feat, CANVAS_FEATURES)
                refs.append((matched_id, None, "mentions"))
        except Exception as e:
            logger.warning(f"LLM feature extraction failed: {e}")

    # 4. Fall back to 'general' if still no matches
    if not refs:
        refs.append(("general", None, "mentions"))

    # 5. Deduplicate, keeping strongest mention_type per (feature_id, option_id) pair
    return _deduplicate_refs(refs)


def _deduplicate_refs(
    refs: List[Tuple[str, Optional[str], str]]
) -> List[Tuple[str, Optional[str], str]]:
    """Deduplicate refs, keeping strongest mention_type per feature/option pair.

    Args:
        refs: List of (feature_id, option_id, mention_type) tuples.

    Returns:
        Deduplicated list with strongest mention_type per pair.
    """
    # Group by (feature_id, option_id)
    best: Dict[Tuple[str, Optional[str]], str] = {}

    for feature_id, option_id, mention_type in refs:
        key = (feature_id, option_id)

        if key not in best:
            best[key] = mention_type
        else:
            # Keep the stronger mention_type (lower index in priority list)
            current_priority = MENTION_TYPE_PRIORITY.index(best[key]) if best[key] in MENTION_TYPE_PRIORITY else 999
            new_priority = MENTION_TYPE_PRIORITY.index(mention_type) if mention_type in MENTION_TYPE_PRIORITY else 999

            if new_priority < current_priority:
                best[key] = mention_type

    return [(fid, oid, mtype) for (fid, oid), mtype in best.items()]
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_scrapers.py::TestExtractFeatureRefs -v
```

Expected: PASS (7 tests)

**Step 5: Commit**

```bash
git add src/scrapers/instructure_community.py tests/test_scrapers.py
git commit -m "feat(scraper): add extract_feature_refs() for Q&A/blog posts"
```

---

## Task 5: Update classify_discussion_posts() to return feature refs

**Files:**
- Modify: `src/scrapers/instructure_community.py`
- Test: `tests/test_scrapers.py`

**Step 1: Write the failing tests**

Add to `tests/test_scrapers.py`:

```python
class TestClassifyDiscussionPostsWithRefs:
    """Tests for classify_discussion_posts with feature ref extraction."""

    def test_classify_discussion_posts_extracts_refs_for_new_post(self, temp_db):
        """Test that new posts get feature refs extracted."""
        from scrapers.instructure_community import (
            classify_discussion_posts,
            CommunityPost,
        )
        from datetime import datetime, timezone

        temp_db.seed_features()

        post = CommunityPost(
            title="SpeedGrader not loading",
            url="https://community.instructure.com/discussion/12345",
            content="SpeedGrader is giving me an error when I try to grade.",
            published_date=datetime.now(timezone.utc),
            post_type="question",
            comment_count=5,
        )

        updates = classify_discussion_posts([post], temp_db, first_run_limit=10)

        assert len(updates) == 1
        update = updates[0]
        assert update.is_new is True

        # Check that feature_refs were extracted
        assert hasattr(update, 'feature_refs')
        assert len(update.feature_refs) >= 1

        # Should have ref to speedgrader
        feature_ids = [r[0] for r in update.feature_refs]
        assert "speedgrader" in feature_ids
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_scrapers.py::TestClassifyDiscussionPostsWithRefs -v
```

Expected: FAIL with `AttributeError: 'DiscussionUpdate' object has no attribute 'feature_refs'`

**Step 3: Update DiscussionUpdate dataclass**

Modify `DiscussionUpdate` in `src/scrapers/instructure_community.py`:

```python
@dataclass
class DiscussionUpdate:
    """Represents a discussion post that is new or has new comments."""
    post: CommunityPost
    is_new: bool
    previous_comment_count: int
    new_comment_count: int
    latest_comment: Optional[str]
    feature_refs: List[Tuple[str, Optional[str], str]] = None  # (feature_id, option_id, mention_type)

    def __post_init__(self):
        if self.feature_refs is None:
            self.feature_refs = []
```

**Step 4: Update classify_discussion_posts() to extract refs**

Modify `classify_discussion_posts()` to call `extract_feature_refs()`:

```python
def classify_discussion_posts(
    posts: List[CommunityPost],
    db: "Database",
    first_run_limit: int = 5,
    scraper: Optional["InstructureScraper"] = None,
    processor: Optional["ContentProcessor"] = None,
) -> List[DiscussionUpdate]:
    """Classify posts as new or updated based on comment tracking.

    Uses the content_items table to track which posts are new vs updated.
    A post is considered:
    - New: if it doesn't exist in the database
    - Updated: if it exists but comment_count has increased

    Args:
        posts: List of CommunityPost objects to classify.
        db: Database instance for checking existing posts.
        first_run_limit: Max posts to include on first run (when db is empty).
        scraper: Optional scraper to fetch latest comment text.
        processor: Optional ContentProcessor for LLM feature extraction.

    Returns:
        List of DiscussionUpdate objects for new/updated posts.
    """
    if not posts:
        return []

    updates: List[DiscussionUpdate] = []
    new_posts_count = 0

    # Check if this is a first run (no discussion posts exist in db)
    is_first_run = True
    for post in posts:
        if db.item_exists(post.source_id):
            is_first_run = False
            break

    for post in posts:
        source_id = post.source_id
        current_comment_count = post.comment_count or post.comments or 0

        if not db.item_exists(source_id):
            # New post - check first_run_limit
            if is_first_run and new_posts_count >= first_run_limit:
                continue

            # Get latest comment if scraper available
            latest_comment = None
            if scraper and current_comment_count > 0:
                latest_comment = scraper.scrape_latest_comment(post.url)

            # Extract feature refs
            feature_refs = extract_feature_refs(
                title=post.title,
                content=post.content,
                db=db,
                post_type=post.post_type,
                is_new=True,
                processor=processor,
            )

            updates.append(DiscussionUpdate(
                post=post,
                is_new=True,
                previous_comment_count=0,
                new_comment_count=current_comment_count,
                latest_comment=latest_comment,
                feature_refs=feature_refs,
            ))
            new_posts_count += 1
        else:
            # Existing post - check for new comments
            stored_count = db.get_comment_count(source_id) or 0

            if current_comment_count > stored_count:
                # Post has new comments
                latest_comment = None
                if scraper:
                    latest_comment = scraper.scrape_latest_comment(post.url)

                # Extract feature refs (is_new=False for updates)
                feature_refs = extract_feature_refs(
                    title=post.title,
                    content=post.content,
                    db=db,
                    post_type=post.post_type,
                    is_new=False,
                    processor=processor,
                )

                updates.append(DiscussionUpdate(
                    post=post,
                    is_new=False,
                    previous_comment_count=stored_count,
                    new_comment_count=current_comment_count,
                    latest_comment=latest_comment,
                    feature_refs=feature_refs,
                ))

                # Update stored comment count
                db.update_comment_count(source_id, current_comment_count)

    return updates
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_scrapers.py::TestClassifyDiscussionPostsWithRefs -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add src/scrapers/instructure_community.py tests/test_scrapers.py
git commit -m "feat(scraper): extract feature_refs in classify_discussion_posts()"
```

---

## Task 6: Update process_discussions() in main.py to create refs

**Files:**
- Modify: `src/main.py`
- Test: `tests/test_main.py`

**Step 1: Write the failing test**

Add to `tests/test_main.py`:

```python
class TestProcessDiscussionsFeatureRefs:
    """Tests for process_discussions creating feature refs."""

    def test_process_discussions_creates_content_feature_refs(self, temp_db, mocker):
        """Test that process_discussions creates content_feature_refs records."""
        from main import process_discussions
        from scrapers.instructure_community import CommunityPost, DiscussionUpdate
        from processor.content_processor import ContentProcessor
        from datetime import datetime, timezone

        # Seed features
        temp_db.seed_features()

        # Mock the classify_discussion_posts to return a controlled update
        mock_update = DiscussionUpdate(
            post=CommunityPost(
                title="SpeedGrader issue",
                url="https://community.instructure.com/discussion/99999",
                content="SpeedGrader is slow",
                published_date=datetime.now(timezone.utc),
                post_type="question",
                comment_count=3,
            ),
            is_new=True,
            previous_comment_count=0,
            new_comment_count=3,
            latest_comment=None,
            feature_refs=[("speedgrader", None, "questions")],
        )

        mocker.patch(
            "main.classify_discussion_posts",
            return_value=[mock_update]
        )

        # Create a mock processor
        processor = mocker.MagicMock(spec=ContentProcessor)
        processor.sanitize_html.return_value = "SpeedGrader is slow"
        processor.redact_pii.side_effect = lambda x: x
        processor.summarize_with_llm.return_value = "User reports SpeedGrader performance issues."
        processor.classify_topic.return_value = ("Grading", ["SpeedGrader"])

        # Call process_discussions
        items, updates = process_discussions(
            posts=[mock_update.post],
            db=temp_db,
            processor=processor,
            scraper=None,
        )

        # Check that content_feature_refs was created
        refs = temp_db.get_features_for_content("question_99999")
        assert len(refs) >= 1
        assert refs[0]["feature_id"] == "speedgrader"
        assert refs[0]["mention_type"] == "questions"
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_main.py::TestProcessDiscussionsFeatureRefs -v
```

Expected: FAIL (function signature or behavior mismatch)

**Step 3: Update process_discussions() in main.py**

Find the `process_discussions()` function and update it to create `content_feature_refs`:

```python
def process_discussions(
    posts: List[CommunityPost],
    db: Database,
    processor: ContentProcessor,
    scraper: Optional[InstructureScraper] = None,
) -> Tuple[List[ContentItem], List[DiscussionUpdate]]:
    """Process discussion posts (Q&A and blog).

    Args:
        posts: List of CommunityPost objects.
        db: Database instance.
        processor: ContentProcessor for enrichment.
        scraper: Optional scraper for fetching latest comments.

    Returns:
        Tuple of (content_items stored, discussion_updates).
    """
    updates = classify_discussion_posts(
        posts, db, first_run_limit=5, scraper=scraper, processor=processor
    )
    stored_items = []

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
            stored_items.append(item)

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

    return stored_items, updates
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_main.py::TestProcessDiscussionsFeatureRefs -v
```

Expected: PASS

**Step 5: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests pass

**Step 6: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat(main): create content_feature_refs in process_discussions()"
```

---

## Task 7: Integration Testing with Real URLs

**Files:**
- Manual testing

**Step 1: Run the scraper against user-provided URLs**

User will provide specific Q&A and blog URLs to test against.

**Step 2: Verify refs are created**

```python
# In Python REPL or test script
from utils.database import Database
db = Database("data/canvas_digest.db")

# Check refs for a specific content item
refs = db.get_features_for_content("question_12345")
print(refs)

# Check content for a feature
content = db.get_content_for_feature("new_quizzes")
print(content)
```

**Step 3: Commit any fixes**

```bash
git add -A
git commit -m "fix: address issues found in integration testing"
```

---

## Summary

| Task | Description | Tests |
|------|-------------|-------|
| 1 | Add 'mentions' to MENTION_TYPES | N/A |
| 2 | Add get_all_feature_options() | 3 tests |
| 3 | Add extract_features_with_llm() | 6 tests |
| 4 | Add extract_feature_refs() | 7 tests |
| 5 | Update classify_discussion_posts() | 1 test |
| 6 | Update process_discussions() | 1 test |
| 7 | Integration testing | Manual |

**Total new tests:** 18

# Discussion Feature References Design

**Date:** 2026-02-04
**Status:** Approved
**Purpose:** Map Q&A and Blog posts to features/feature_options via `content_feature_refs`

---

## Overview

Q&A and blog posts are scraped and stored in `content_items`, but lack linkage to the feature tracking system. This design adds feature reference extraction so we can answer questions like "What Q&A posts mention New Quizzes?" or "Which blog posts announced Gradebook features?"

## Design Decisions

### 1. Matching Strategy: Hybrid (Keyword + LLM)

- **First:** Match against existing `feature_options.canonical_name` in database
- **Second:** Match against `CANVAS_FEATURES` dictionary (~45 features)
- **Third:** LLM fallback for ambiguous content
- **Fourth:** Link to `'general'` if no match found

### 2. Q&A vs Blog Post Handling

| Aspect | Q&A Posts | Blog Posts (first scrape) | Blog Posts (update) |
|--------|-----------|---------------------------|---------------------|
| Creates `feature_options`? | No | No | No |
| Creates `content_feature_refs`? | Yes | Yes | Yes |
| Default `mention_type` | `'questions'` | `'announces'` | `'discusses'` |

Blog posts can announce features before release notes, but we don't create `feature_options` from them since we lack canonical names. Release notes remain the authoritative source for option creation.

### 3. Mention Types and Confidence

| mention_type | Meaning | When Used |
|--------------|---------|-----------|
| `'announces'` | Authoritative source | Blog post first scrape |
| `'questions'` | Asking about feature | Q&A posts |
| `'discusses'` | Title match / explicit discussion | Title contains feature name |
| `'feedback'` | User feedback | Explicit feedback content |
| `'mentions'` | Weak signal | Content-only match, LLM extraction |

**Priority order** (strongest wins when deduplicating):
1. `'announces'`
2. `'questions'`
3. `'discusses'`
4. `'feedback'`
5. `'mentions'`

### 4. Title vs Content Weighting

- **Title match** → `'discusses'` or `'questions'` (higher confidence)
- **Content-only match** → `'mentions'` (lower confidence)

### 5. Multiple References

A single post can link to multiple features/options. Example: "How do I use SpeedGrader with New Quizzes?" creates refs to both `speedgrader` and `new_quizzes`.

---

## Data Flow

```
Q&A Post scraped
    │
    ├── Extract feature references (keyword → LLM fallback)
    │       │
    │       ├── Match against feature_options.canonical_name (existing)
    │       ├── Match against CANVAS_FEATURES
    │       └── Fall back to 'general'
    │
    └── Create content_feature_refs
            ├── feature_id (always set)
            ├── feature_option_id (if matched existing option)
            └── mention_type = 'questions'

Blog Post scraped (first time)
    │
    ├── Extract feature references (same logic)
    │
    └── Create content_feature_refs
            └── mention_type = 'announces'

Blog Post updated (new comments)
    │
    └── Create/update content_feature_refs
            └── mention_type = 'discusses'
```

---

## Implementation

### Files to Modify

| File | Changes |
|------|---------|
| `src/utils/database.py` | Add `get_all_feature_options()` method |
| `src/scrapers/instructure_community.py` | Add `extract_feature_refs()` function |
| `src/scrapers/instructure_community.py` | Update `classify_discussion_posts()` to return refs |
| `src/processor/content_processor.py` | Add `extract_features_with_llm()` method |
| `src/main.py` | Update `process_discussions()` to create refs |
| `src/constants.py` | Add `'mentions'` to `MENTION_TYPES` |

### New Function: `extract_feature_refs()`

```python
def extract_feature_refs(
    title: str,
    content: str,
    db: "Database",
    post_type: str,  # 'question' or 'blog'
    is_new: bool,    # first scrape or update
    processor: Optional["ContentProcessor"] = None,  # for LLM fallback
) -> List[Tuple[str, Optional[str], str]]:
    """
    Extract feature references from post title and content.

    Returns:
        List of (feature_id, option_id, mention_type) tuples.
    """
```

**Algorithm:**

1. Query existing `feature_options` from database
2. For each option, check if `canonical_name` appears in title or content
3. For each `CANVAS_FEATURES` entry, check if name/id appears in title or content
4. If no matches and processor available, call LLM extraction
5. If still no matches, return `[('general', None, 'mentions')]`
6. Deduplicate, keeping strongest mention_type per feature/option pair

### New Database Method: `get_all_feature_options()`

```python
def get_all_feature_options(self) -> List[dict]:
    """Get all feature options for matching against content."""
    conn = self._get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT option_id, feature_id, canonical_name, name
        FROM feature_options
        WHERE canonical_name IS NOT NULL
    """)
    return [dict(row) for row in cursor.fetchall()]
```

### New ContentProcessor Method: `extract_features_with_llm()`

```python
def extract_features_with_llm(self, title: str, content: str) -> List[str]:
    """
    Use LLM to extract Canvas feature names from content.

    Returns:
        List of feature names mentioned (may not be canonical).
    """
```

Prompt template:
```
Extract Canvas LMS feature names mentioned in this post.
Return only feature names, one per line. Examples: Gradebook, New Quizzes, SpeedGrader, Assignments.
If no features are mentioned, return "none".

Title: {title}
Content: {content[:1000]}
```

---

## Testing Strategy

1. Unit tests for `extract_feature_refs()` with known matches
2. Unit tests for `get_all_feature_options()`
3. Unit tests for `extract_features_with_llm()` (mocked)
4. Integration test with real URLs provided by user
5. Verify `content_feature_refs` records created correctly

---

## Consistency with Release Notes

This design aligns with release note handling:

| Aspect | Release Notes | Q&A/Blog Posts |
|--------|--------------|----------------|
| Creates `feature_options`? | Yes | No |
| Creates `feature_announcements`? | Yes | No |
| Creates `content_feature_refs`? | Yes | Yes |
| Falls back to `'general'`? | Yes | Yes |
| Multiple refs per content? | Yes | Yes |

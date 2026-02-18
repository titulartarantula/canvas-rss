# Canvas-RSS Implementation Plan - Stage 2: Scraping Changes

**Date:** 2026-02-03
**Project:** canvas-rss
**Stage:** 2 of 2 (Scraping Changes)
**Design Doc:** `docs/plans/2026-02-03-database-schema-redesign.md`
**Depends on:** Stage 1 (Database Schema) - COMPLETE

## Overview

Implement scraping changes to populate the new database schema. This stage focuses on extracting source dates, generating proper content IDs, and linking content to features.

## Pre-requisites

- [x] Stage 1 complete: Database schema with features, feature_options, content_feature_refs tables
- [ ] Review and approve this plan

---

## Tasks

### Phase 1: Date Extraction from DOM

#### Task 1.1: Extract dates from Community posts
**File:** `src/scrapers/instructure_community.py`

For Q&A and Blog posts, extract:
| Field | DOM Location | Example |
|-------|--------------|---------|
| `first_posted` | First `<time datetime>` element | `<time datetime="2026-01-15T10:30:00Z">` |
| `last_edited` | "Updated" time element (if exists) | Look for "Edited" or "Updated" label |
| `last_comment_at` | Last comment's `<time>` element | Scan comment section |
| `comment_count` | Pagination text "X of Y" or count element | `"1 of 23 replies"` |

Update `CommunityPost` dataclass to include these fields.

#### Task 1.2: Extract dates from Release/Deploy notes
**File:** `src/scrapers/instructure_community.py`

For release notes pages, extract:
- `first_posted`: Release date from page title/header
- `last_edited`: Page modification date (if available)

Update `ReleaseNotePage` and `DeployNotePage` dataclasses.

#### Task 1.3: Extract dates from Reddit
**File:** `src/scrapers/reddit_scraper.py`

Map Reddit API fields:
| Field | Reddit API | Notes |
|-------|------------|-------|
| `first_posted` | `submission.created_utc` | Convert from Unix timestamp |
| `last_comment_at` | Scan `submission.comments` | Find most recent |
| `comment_count` | `submission.num_comments` | Direct mapping |

#### Task 1.4: Extract dates from Status
**File:** `src/scrapers/status_scraper.py`

Map status API fields:
| Field | Status API | Notes |
|-------|------------|-------|
| `first_posted` | `created_at` | Incident creation |
| `last_edited` | `updated_at` | Last update |

---

### Phase 2: Content ID Generation

#### Task 2.1: Update content_id generation for Community posts
**File:** `src/scrapers/instructure_community.py`

Change from hash-based to actual ID:
```python
# Before (hash-based)
source_id = f"{post_type}_{hashlib.md5(url.encode()).hexdigest()[:8]}"

# After (actual ID from URL)
# URL: https://community.canvaslms.com/t5/Question-Forum/topic/td-p/664616
source_id = f"{post_type}_{numeric_id}"  # e.g., "question_664616"
```

Update `extract_source_id()` function to parse numeric ID from URL.

#### Task 2.2: Update content_id generation for Reddit
**File:** `src/scrapers/reddit_scraper.py`

Use submission ID:
```python
source_id = f"reddit_{submission.id}"  # e.g., "reddit_1i5abc"
```

#### Task 2.3: Update content_id generation for Status
**File:** `src/scrapers/status_scraper.py`

Use incident ID:
```python
source_id = f"status_{incident_id}"  # e.g., "status_xyz789"
```

---

### Phase 3: Feature Classification

#### Task 3.1: Reimplement classify_discussion_posts
**File:** `src/scrapers/instructure_community.py`

Replace stubbed function with new implementation that:
1. Uses `content_items` table for tracking (via `first_posted`, `last_checked_at`)
2. Detects new vs updated posts based on `last_comment_at` changes
3. No longer uses dropped `discussion_tracking` table

#### Task 3.2: Reimplement classify_release_features
**File:** `src/scrapers/instructure_community.py`

Replace stubbed function with new implementation that:
1. Creates `feature_options` records for announced features
2. Links content to features via `content_feature_refs`
3. Uses `mention_type='announces'` for release note announcements

#### Task 3.3: Reimplement classify_deploy_changes
**File:** `src/scrapers/instructure_community.py`

Similar to Task 3.2 but for deploy notes.

#### Task 3.4: Add LLM-based feature matching for community posts
**File:** `src/processor/content_processor.py`

Add method to classify which Canvas feature a community post is about:
```python
def classify_feature(self, content: str, title: str) -> Optional[str]:
    """Use LLM to determine which Canvas feature this content is about.

    Returns:
        feature_id from CANVAS_FEATURES, or None if unclear.
    """
```

---

### Phase 4: Database Integration

#### Task 4.1: Update insert_item to store new date fields
**File:** `src/utils/database.py`

Update `insert_item()` to store:
- `first_posted`
- `last_edited`
- `last_comment_at`
- `last_checked_at`

#### Task 4.2: Update main.py to use new tracking
**File:** `src/main.py`

- Remove remaining v1.3.0 tracking references
- Add calls to `seed_features()` on startup
- Add feature linking after content processing

#### Task 4.3: Add update_item method for tracking changes
**File:** `src/utils/database.py`

Add method to update existing items when re-scraped:
```python
def update_item_tracking(
    self,
    source_id: str,
    last_comment_at: datetime = None,
    comment_count: int = None,
    last_checked_at: datetime = None,
) -> bool:
```

---

### Phase 5: Testing & Cleanup

#### Task 5.1: Update scraper tests
**File:** `tests/test_scrapers.py`

- Update tests for new date extraction
- Update tests for new content_id generation
- Replace v1.3.0 classification tests with v2.0 tests

#### Task 5.2: Update integration tests
**File:** `tests/test_main.py`

- Remove or update `TestV130Integration` and `TestV130FullIntegration`
- Add v2.0 integration tests for feature linking

#### Task 5.3: Fix processor tests (pre-existing)
**File:** `tests/test_processor.py`

Fix outdated mocks that use `genai.configure()` instead of `genai.Client()`.

#### Task 5.4: Remove deprecated code
**Files:** Various

- Remove any remaining references to dropped tables
- Remove unused imports
- Clean up deprecation comments from Stage 1

---

## Verification Checklist

Before marking complete:

- [ ] Source dates extracted from all content types
- [ ] Content IDs use actual IDs (not hashes)
- [ ] Classification functions reimplemented with new schema
- [ ] Features seeded on startup
- [ ] Content linked to features via junction table
- [ ] All tests pass (including fixed processor tests)
- [ ] RSS feed generation still works
- [ ] No references to dropped tables remain

---

## Migration Notes

**Breaking changes in v2.0:**
- `discussion_tracking` table dropped
- `feature_tracking` table dropped
- Old tracking methods removed from Database class
- `source_id` format changed (may affect deduplication for existing data)

**Backwards compatibility:**
- Existing `content_items` data preserved
- RSS feed format unchanged
- API unchanged (internal changes only)

---

## Estimated Scope

| Phase | Tasks | Complexity |
|-------|-------|------------|
| 1. Date Extraction | 4 | Medium - DOM parsing |
| 2. Content ID | 3 | Low - string manipulation |
| 3. Feature Classification | 4 | High - logic reimplementation |
| 4. Database Integration | 3 | Medium - wiring |
| 5. Testing & Cleanup | 4 | Medium - test updates |

**Total:** 18 tasks across 5 phases

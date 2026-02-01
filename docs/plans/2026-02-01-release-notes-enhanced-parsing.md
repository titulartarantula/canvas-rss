# Release Notes Enhanced Parsing Design

**Date:** 2026-02-01
**Version:** v1.3.0
**Status:** Ready for implementation

## Problem Statement

The current RSS aggregator produces a single ~200-word summary for each Release Notes page, which contains multiple features across categories. This loses valuable detail. Educational technologists need quick TLDRs for each individual feature to assess relevance and communicate changes to faculty.

## Design Decisions

### 1. Data Model

Each release note page becomes multiple `content_items` entries using Option A (features as individual content_items with anchor-based source_ids):

**Parent Entry** (`source_id: "release-2026-02-21"`)

- Contains the "Upcoming Canvas Changes" section
- Serves as the main RSS item linking to the full page
- `content_type: "release_note"`

**Feature Entries** (`source_id: "release-2026-02-21#document-processing-app"`)

- One per feature, using the page's anchor IDs
- Contains LLM-generated summary + availability summary
- `content_type: "release_note_feature"`
- Stores `added_date` if "[Added DATE]" annotation exists

### 2. RSS Badges

Simplified badge system - badges apply to **post title only**, not individual features:

- `[NEW] Canvas Release Notes (2026-02-21)` - first time scraped
- `[UPDATE] Canvas Release Notes (2026-02-21)` - new features detected

### 3. RSS Post Structure

```
[Link to full release notes page]

━━━ UPCOMING CANVAS CHANGES ━━━
⚠️ 2026-03-21: User-Agent Header Enforcement
• 2026-03-25: Removal of Unauthenticated File Access
• 2026-04-18: Improving Canvas Infrastructure with a CDN
→ Full list: [link to deprecations page]

━━━ NEW FEATURES ━━━

▸ Assignments - [Document Processing App](anchor-link)
[2-3 sentence LLM-generated summary]
Availability: Admin-enabled at account level; affects instructors and students in Assignments, SpeedGrader

▸ Canvas Apps - [Availability and Exceptions](anchor-link) [Added 2026-01-28]
[2-3 sentence summary]
Availability: Account-level setting; affects admins in App configuration

━━━ OTHER UPDATES ━━━

▸ Canvas Apps - [Updated Apps Page Text](anchor-link)
[2-3 sentence summary]
Availability: Automatic update; affects admins viewing Apps page
```

### 4. Key Formatting Decisions

- Single link to full release notes at top
- Feature names are links to their anchor in the page
- `[Added DATE]` annotations preserved on feature lines
- Urgency flag (⚠️) for upcoming changes within 30 days
- Same treatment for both "New Features" and "Other Updates" sections

### 5. Update Detection

**Daily 6am run logic:**

1. Fetch the release notes page
2. Parse all feature anchor IDs
3. For each anchor, check `item_exists(source_id)` in database
4. New anchors = new features → create `[UPDATE]` RSS entry
5. Store new features with current date as `first_seen_date`

**Update RSS entry:**

- Title: `[UPDATE] Canvas Release Notes (2026-02-21)`
- Contains only the newly added features (not the full page)
- Links to same release notes page

### 6. LLM Summarization

**Feature summaries (2-3 sentences):**

- LLM-generated from full feature content
- Focus on: what it does, who it's for, key benefit

**Prompt template:**

```
You are summarizing a Canvas LMS feature for educational technologists.

Feature: {feature_name}
Category: {category}

Content:
{raw_feature_content}

Write a 2-3 sentence summary that covers:
1. What this feature does
2. Who benefits from it (students, instructors, admins)
3. The key improvement or capability it provides

Keep it concise and jargon-free.
```

**Availability summaries (role-focused, single line):**

- Derived from configuration table (no LLM needed)
- Format: `"{permissions}-enabled at {location}; affects {roles} in {areas}"`
- Example: `"Admin-enabled at account level; affects instructors and students in Assignments, SpeedGrader"`

### 7. Parsing Output Structure

```python
@dataclass
class UpcomingChange:
    date: datetime
    description: str
    days_until: int  # For urgency flag (⚠️ if <= 30)

@dataclass
class FeatureTableData:
    enable_location: str      # "Account Settings"
    default_status: str       # "Off", "On"
    permissions: str          # "Admin only", "Instructor"
    affected_areas: List[str] # ["Assignments", "SpeedGrader"]
    affects_roles: List[str]  # ["instructors", "students"]

@dataclass
class Feature:
    category: str            # "Assignments"
    name: str                # "Document Processing App"
    anchor_id: str           # "document-processing-app"
    added_date: Optional[datetime]  # From "[Added 2026-01-28]" if present
    raw_content: str         # Full HTML for LLM summarization
    table_data: FeatureTableData

@dataclass
class ReleaseNotePage:
    title: str               # "Canvas Release Notes (2026-02-21)"
    url: str
    release_date: datetime
    upcoming_changes: List[UpcomingChange]
    features: List[Feature]
    sections: Dict[str, List[Feature]]  # {"New Features": [...], "Other Updates": [...]}
```

## Implementation Plan

### Step 1: Dataclasses and Parsing (Scraper)

**File:** `src/scrapers/instructure_community.py`

- Add `UpcomingChange`, `FeatureTableData`, `Feature`, `ReleaseNotePage` dataclasses
- Add `parse_release_note_page(url: str) -> ReleaseNotePage` method
- Use Playwright to navigate and extract:
  - Page title and release date
  - Upcoming Canvas Changes section
  - H2 sections ("New Features", "Other Updates")
  - H3 categories and features under each
  - Configuration table per feature
  - `[Added DATE]` annotations

### Step 2: Database Schema Update

**File:** `src/utils/database.py`

- Add `first_seen_date` column to `content_items` table (migration)
- Add `get_features_for_release(release_id: str) -> List[dict]` query
- Add `get_release_note_by_date(date: str) -> Optional[dict]` query

### Step 3: LLM Summarization

**File:** `src/processor/content_processor.py`

- Add `summarize_feature(feature: Feature) -> str` method with feature-specific prompt
- Add `format_availability(table: FeatureTableData) -> str` helper (no LLM)

### Step 4: RSS Builder

**File:** `src/generator/rss_builder.py`

- Add `build_release_note_entry(page: ReleaseNotePage, is_update: bool) -> str` method
- Compose structured body with sections
- Update `CONTENT_TYPE_BADGES` with `release_note_update` type
- Handle urgency flags for upcoming changes

### Step 5: Update Detection

**File:** `src/main.py` (or new orchestration module)

- After parsing release notes page, check each feature's source_id
- If new features found, create `[UPDATE]` entry with only new features
- Store new features in database with `first_seen_date`

## Testing Strategy

- Unit tests for each new dataclass
- Unit tests for `parse_release_note_page()` with mocked HTML
- Unit tests for `format_availability()`
- Unit tests for `build_release_note_entry()`
- Integration test: full parsing of sample release notes page
- Integration test: update detection with mock database

## Follow-up Work

### Deploy Notes (Separate Brainstorm Session)

Deploy Notes should follow a similar structure but may have different:

- Section headings (TBD - needs page analysis)
- Feature table structure (TBD)
- Content focus (fixes vs new features)

Start fresh brainstorm session with this plan as context to design Deploy Notes parsing.

## Reference

- Example Release Notes page: https://community.instructure.com/en/discussion/664643/canvas-release-notes-2026-02-21
- Deprecations page: https://community.instructure.com/en/discussion/254349/instructure-enforcements-deprecations-and-breaking-changes/p1
- Full spec: `specs/canvas-rss.md` (Section: Release Notes Enhanced Parsing v1.3.0)

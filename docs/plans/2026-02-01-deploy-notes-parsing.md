# Deploy Notes Enhanced Parsing Design

**Date:** 2026-02-01
**Version:** v1.3.0
**Status:** Ready for implementation

## Problem Statement

The current RSS aggregator treats Deploy Notes pages as single items with a ~200-word summary. Like Release Notes, Deploy Notes contain multiple individual changes across product areas. Educational technologists need granular TLDRs for each change to assess impact and communicate updates to faculty.

## Design Decisions

### 1. Data Model

Each Deploy Notes page becomes multiple `content_items` entries, mirroring the Release Notes approach.

**Source ID Format:**
```
deploy-{date}#{data-id}
```

Examples:
- Parent: `deploy-2026-02-11`
- Change: `deploy-2026-02-11#small-screen-global-navigation-branding-updated`

**Content Types:**
- `deploy_note` - Parent entry for the page
- `deploy_note_change` - Individual change items

**New Dataclasses:**

```python
@dataclass
class DeployChange:
    category: str              # "Navigation", "Gradebook"
    name: str                  # "Small Screen Branding Updated"
    anchor_id: str             # From data-id attribute
    section: str               # "Updated Features", "Other Updates", "Feature Preview"
    raw_content: str           # Full HTML for LLM summarization
    table_data: Optional[FeatureTableData]  # Reuse from Release Notes
    status: Optional[str]      # "delayed", None
    status_date: Optional[datetime]  # Date from [Delayed as of DATE]

@dataclass
class DeployNotePage:
    title: str                 # "Canvas Deploy Notes (2026-02-11)"
    url: str
    deploy_date: datetime      # Production date
    beta_date: Optional[datetime]
    changes: List[DeployChange]
    sections: Dict[str, List[DeployChange]]
```

**Reused from Release Notes:**
- `FeatureTableData` dataclass (same table structure)
- Table parsing logic

### 2. RSS Badges

Same approach as Release Notes:
- `[NEW] Canvas Deploy Notes (2026-02-11)` - First time scraped
- `[UPDATE] Canvas Deploy Notes (2026-02-11)` - New changes detected

### 3. RSS Post Structure

```
[Canvas Deploy Notes (2026-02-11)](full-page-url)
Beta: 2026-01-29 | Production: 2026-02-11

━━━ UPDATED FEATURES ━━━

▸ Navigation - [Small Screen Branding Updated](anchor-link)
[2-3 sentence LLM summary of what changed and why]
Availability: Automatic update; affects all users in Mobile navigation

⏸️ Canvas Apps - [Sub-Account Monitor Access](anchor-link)
[LLM summary]
Availability: Admin-enabled at account level; affects admins in App settings
Delayed: 2026-01-30

━━━ OTHER UPDATES ━━━

▸ ePortfolios - [Legacy Sunset Banner](anchor-link)
[LLM summary]
Availability: Automatic; affects all users in ePortfolios

━━━ FEATURE PREVIEW CHANGE LOG ━━━

▸ New Quizzes - [IgniteAI Rubric Point Distribution](anchor-link)
[LLM summary]
Availability: Feature preview; requires admin opt-in
```

### 4. Key Formatting Decisions

- Deployment metadata (Beta/Production dates) at top
- Section order: Updated Features → Other Updates → Feature Preview Change Log
- Status flags: `⏸️` for delayed items
- Delay date shown on separate line below Availability
- Change names are links to their anchor in the page
- Same visual structure as Release Notes (━━━ headers, ▸ bullets)

### 5. Update Detection

**Daily run logic:**

1. Fetch the Deploy Notes page
2. Parse all change `data-id` attributes
3. For each change, check `item_exists(source_id)` in database
4. New anchors = new changes → create `[UPDATE]` RSS entry
5. Store new changes with `first_seen_date`

**Update RSS entry:**

- Title: `[UPDATE] Canvas Deploy Notes (2026-02-11)`
- Contains only the newly added changes (not the full page)
- Same section structure, filtered to new items

**Edge cases:**

- Delayed status added to existing change: Not detected as "new" (same anchor)
- Change removed from page: Stays in database, won't appear in future RSS

### 6. LLM Summarization

**Change summary prompt:**

```
You are summarizing a Canvas LMS change for educational technologists.

Change: {change_name}
Category: {category}
Section: {section}

Content:
{raw_content}

Write a 2-3 sentence summary that covers:
1. What behavior changed
2. Why it was changed (bug fix, improvement, accessibility, etc.)
3. Who needs to be aware of this change

Keep it concise and jargon-free.
```

**Availability formatting:**

Reuse `format_availability(table: FeatureTableData) -> str` from Release Notes:
```
"{permissions}-enabled at {location}; affects {roles} in {areas}"
```

For changes without configuration tables (pure bug fixes):
```
"Automatic update; affects {roles} in {areas}"
```

### 7. Anchor Parsing

Both Release Notes and Deploy Notes use `data-id` attributes on heading elements:

- H2: Section headings (`data-id="updated-features"`)
- H3: Category headings (`data-id="navigation"`)
- H4: Individual changes (`data-id="small-screen-global-navigation-branding-updated"`)

Parse `data-id` from H4 elements (deepest level) for individual change source_ids.

## Implementation Plan

### Step 1: Dataclasses and Parsing (Scraper)

**File:** `src/scrapers/instructure_community.py`

- Add `DeployChange`, `DeployNotePage` dataclasses
- Add `parse_deploy_note_page(url: str) -> DeployNotePage` method
- Extract `data-id` attributes from H3/H4 headings
- Parse beta/production dates from page metadata
- Parse `[Delayed as of DATE]` annotations from heading text
- Reuse `FeatureTableData` and table parsing logic from Release Notes

### Step 2: LLM Summarization

**File:** `src/processor/content_processor.py`

- Add `summarize_deploy_change(change: DeployChange) -> str` with adapted prompt
- Reuse `format_availability()` helper

### Step 3: RSS Builder

**File:** `src/generator/rss_builder.py`

- Add `build_deploy_note_entry(page: DeployNotePage, is_update: bool, new_only: List[str]) -> str`
- Add `STATUS_FLAGS = {"delayed": "⏸️"}` constant
- Add `deploy_note` and `deploy_note_update` to `CONTENT_TYPE_BADGES`

### Step 4: Main Orchestration

**File:** `src/main.py`

- Add Deploy Notes scraping to daily run (after Release Notes)
- Add update detection logic for deploy changes
- Convert `DeployChange` → `ContentItem` for storage

## Testing Strategy

### Unit Tests

- `DeployChange` and `DeployNotePage` dataclass creation
- `parse_deploy_note_page()` with mocked HTML
- Status annotation parsing (`[Delayed as of DATE]`)
- Beta/production date extraction
- `summarize_deploy_change()` prompt construction
- `build_deploy_note_entry()` output formatting
- Status flag rendering (⏸️)

### Integration Tests

- Full parsing of sample Deploy Notes page HTML
- Update detection with mock database (new changes found)
- Update detection with no new changes
- Mixed sections (Updated Features + Other Updates + Feature Preview)

### Test Fixtures

Save sanitized HTML snapshots from:
- `canvas-deploy-notes-2026-01-28`
- `canvas-deploy-notes-2026-02-11`

## Summary of Key Decisions

| Decision | Choice |
|----------|--------|
| Granularity | One item per change |
| Source IDs | `deploy-{date}#{data-id}` |
| Badges | `[NEW]` / `[UPDATE]` (same as Release Notes) |
| Sections | Updated Features → Other Updates → Feature Preview |
| Metadata | Beta/Production dates at top |
| Status flags | ⏸️ for delayed |
| LLM prompt | Adapted for "what changed, why, who's affected" |
| Availability | Same table parsing as Release Notes |

## Reference

- Example Deploy Notes pages:
  - https://community.instructure.com/en/discussion/664587/canvas-deploy-notes-2026-01-28
  - https://community.instructure.com/en/discussion/664752/canvas-deploy-notes-2026-02-11
- Related design: `docs/plans/2026-02-01-release-notes-enhanced-parsing.md`
- Full spec: `specs/canvas-rss.md`

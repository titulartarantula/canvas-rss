# LLM Summarization Redesign for Website Display

**Date:** 2026-02-05
**Status:** Approved

## Overview

Redesign the LLM summarization process from RSS feed generation to database-first storage for website display. All LLM processing happens during the daily scrape, never at query time.

## Goals

1. Store structured summaries (`description`, `implications`, `meta_summary`) at appropriate levels
2. Track feature option lifecycle dates (beta, production, deprecation)
3. Unify all content types (release notes, deploy notes, blog, Q&A) into `feature_announcements`
4. Capture comments for blog/Q&A to inform `implications` regeneration
5. Provide CLI for manual regeneration and content triage
6. Maintain anonymity - no author/PII anywhere in database

---

## Schema Changes (v2.0 Clean Rebuild)

### features

Top-level Canvas features (~48 canonical).

```sql
CREATE TABLE features (
    feature_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,                -- LLM: 1-2 sentences, what it is
    status TEXT DEFAULT 'active',    -- 'active', 'deprecated'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    llm_generated_at TIMESTAMP       -- when description was generated
);
```

### feature_options

Sub-features with lifecycle state and meta-summary.

```sql
CREATE TABLE feature_options (
    option_id TEXT PRIMARY KEY,
    feature_id TEXT NOT NULL,
    name TEXT NOT NULL,
    canonical_name TEXT,                  -- exact name from release notes
    description TEXT,                     -- LLM: 1-2 sentences
    meta_summary TEXT,                    -- LLM: 3-4 sentences from latest 5 content
    meta_summary_updated_at TIMESTAMP,
    implementation_status TEXT,           -- template-generated
    status TEXT NOT NULL DEFAULT 'pending',
    config_level TEXT,                    -- 'account', 'course', 'both'
    default_state TEXT,                   -- 'enabled', 'disabled'
    user_group_url TEXT,
    -- Lifecycle dates
    beta_date DATE,                       -- when available in beta
    production_date DATE,                 -- when available in production
    deprecation_date DATE,                -- when deprecated (if applicable)
    first_announced TIMESTAMP,
    last_updated TIMESTAMP,
    llm_generated_at TIMESTAMP,           -- when description was generated
    FOREIGN KEY (feature_id) REFERENCES features(feature_id)
);

CREATE INDEX idx_feature_options_feature ON feature_options(feature_id);
CREATE INDEX idx_feature_options_status ON feature_options(status);
```

### feature_announcements

Individual announcements from all content types.

```sql
CREATE TABLE feature_announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_id TEXT,
    option_id TEXT,
    content_id TEXT NOT NULL,
    h4_title TEXT NOT NULL,
    anchor_id TEXT,
    section TEXT,
    category TEXT,
    description TEXT,                     -- LLM: 1-2 sentences (replaces summary)
    implications TEXT,                    -- LLM: 2-3 sentences
    raw_content TEXT,
    -- Config snapshot fields
    enable_location_account TEXT,
    enable_location_course TEXT,
    subaccount_config BOOLEAN,
    account_course_setting TEXT,
    permissions TEXT,
    affected_areas TEXT,
    affects_ui BOOLEAN,
    added_date DATE,
    announced_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (feature_id) REFERENCES features(feature_id),
    FOREIGN KEY (option_id) REFERENCES feature_options(option_id),
    FOREIGN KEY (content_id) REFERENCES content_items(source_id)
);

CREATE INDEX idx_announcements_feature ON feature_announcements(feature_id);
CREATE INDEX idx_announcements_option ON feature_announcements(option_id);
CREATE INDEX idx_announcements_content ON feature_announcements(content_id);
CREATE INDEX idx_announcements_date ON feature_announcements(announced_at);
```

### content_items

Cleaned up, deprecated columns removed.

```sql
CREATE TABLE content_items (
    id INTEGER PRIMARY KEY,
    source_id TEXT UNIQUE,
    url TEXT,
    title TEXT,
    content_type TEXT,                    -- 'release_note', 'deploy_note', 'blog', 'question', etc.
    content TEXT,                         -- raw content for LLM processing
    engagement_score INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    first_posted TIMESTAMP,
    last_edited TIMESTAMP,
    last_comment_at TIMESTAMP,
    last_checked_at TIMESTAMP,
    scraped_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dropped columns (v1.x cruft):
-- summary, sentiment, primary_topic, topics, source, included_in_feed

CREATE INDEX idx_content_type ON content_items(content_type);
CREATE INDEX idx_first_posted ON content_items(first_posted);
```

### content_comments (New)

Comments for blog/Q&A posts. No author - anonymous by design.

```sql
CREATE TABLE content_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id TEXT NOT NULL,             -- FK to content_items(source_id)
    comment_text TEXT NOT NULL,           -- PII-redacted
    posted_at TIMESTAMP,
    position INTEGER,                     -- order in thread (1, 2, 3...)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (content_id) REFERENCES content_items(source_id)
);

CREATE INDEX idx_comments_content ON content_comments(content_id);
CREATE INDEX idx_comments_posted ON content_comments(posted_at);
```

### Tables to Drop

- `discussion_tracking` (if exists)
- `feature_tracking` (if exists)
- `feed_history` (RSS-only, optional keep for archive)

---

## LLM Generation Triggers

| Table | Field | Trigger | Regeneration |
|-------|-------|---------|--------------|
| `features` | `description` | First content referencing feature | CLI only |
| `feature_options` | `description` | First announcement for option | CLI only |
| `feature_options` | `meta_summary` | New content with mention_type 'announces' or 'feedback' | Automatic |
| `feature_options` | `implementation_status` | Status/config/date change | Automatic (template) |
| `feature_announcements` | `description` | On scrape | Never (immutable) |
| `feature_announcements` | `implications` | On scrape; new comments for blog/Q&A | Auto on new comments |

---

## Content Flow

### All content types create feature_announcements

| Source | content_type | description from | implications from |
|--------|--------------|------------------|-------------------|
| Release note | `release_note` | H4 content | H4 content (who's affected) |
| Deploy note | `deploy_note` | H4 content | H4 content (who's affected) |
| Blog post | `blog` | Initial post | Comments (weighted recent) |
| Q&A post | `question` | Initial question | Answers/comments (weighted recent) |

### Fallback to 'general'

Content that doesn't match any canonical feature/option is assigned to the `general` feature. CLI triage allows manual reassignment.

---

## Lifecycle Date Parsing

### Page-level defaults

Parse from release note intro paragraph:
> "Unless otherwise stated, all features in this release are available in the Beta environment on 2026-01-19 and the Production environment on 2026-02-21."

### Per-feature overrides

Some H4 entries have `[Added DATE]` annotations that override page-level defaults.

### Storage

- `feature_options.beta_date` - when available in beta
- `feature_options.production_date` - when available in production
- `feature_options.deprecation_date` - when deprecated (if applicable)

---

## implementation_status Template

No LLM - generated from structured data:

```python
def generate_implementation_status(option: FeatureOption) -> str:
    status_map = {
        'pending': 'Not yet available',
        'preview': 'In feature preview (beta)',
        'optional': 'Available, disabled by default',
        'default_on': 'Available, enabled by default',
        'released': 'Fully released'
    }

    parts = [status_map.get(option.status, option.status)]

    today = date.today()

    if option.config_level:
        parts.append(f"{option.config_level.title()}-level setting")

    if option.beta_date and option.beta_date > today:
        parts.append(f"Beta: {option.beta_date.strftime('%b %d, %Y')}")

    if option.production_date and option.production_date > today:
        parts.append(f"Production: {option.production_date.strftime('%b %d, %Y')}")
    elif option.production_date:
        parts.append(f"In production since {option.production_date.strftime('%b %Y')}")

    if option.first_announced:
        parts.append(f"First announced {option.first_announced.strftime('%b %Y')}")

    return ". ".join(parts) + "."
```

---

## LLM Prompts

### features.description (1-2 sentences)

```
You are summarizing Canvas LMS features for educational technologists.

Describe what {feature_name} is in 1-2 sentences. Be concise and factual.

Context from recent content:
{content_snippet}
```

### feature_options.description (1-2 sentences)

```
You are summarizing a Canvas LMS feature option for educational technologists.

Feature option: {option_name}
Parent feature: {feature_name}

Describe what this feature option does in 1-2 sentences. Be concise and factual.

Context:
{raw_content}
```

### feature_options.meta_summary (3-4 sentences)

```
You are advising educational technologists about the deployment readiness of a Canvas feature option.

Feature option: {option_name}
Parent feature: {feature_name}
Current status: {implementation_status}

Recent activity (newest first):
{latest_5_content_summaries}

In 3-4 sentences, summarize the current state of this feature option for ed techs considering deployment. Cover: readiness for wide rollout, recent changes (especially status transitions like beta→production), community sentiment, and any concerns. Be direct and actionable.
```

### feature_announcements.description (1-2 sentences)

```
Summarize this Canvas release note entry in 1-2 sentences. What changed or was added?

Title: {h4_title}
Content: {raw_content}
```

### feature_announcements.implications (2-3 sentences)

For release/deploy notes:
```
In 2-3 sentences, explain who is affected by this change and what educational technologists should know. Be actionable.

Title: {h4_title}
Content: {raw_content}
Feature: {feature_name}
```

For blog/Q&A (regenerated on new comments):
```
In 2-3 sentences, summarize the community discussion and what educational technologists should know. Weight recent comments more heavily. Be actionable.

Title: {title}
Initial post: {initial_content}

Comments (newest first):
{comments_list}
```

---

## meta_summary Query

Fetch latest 5 content items for a feature option:

```sql
SELECT ci.title, fa.description, fa.implications, ci.first_posted
FROM content_items ci
JOIN content_feature_refs cfr ON ci.source_id = cfr.content_id
LEFT JOIN feature_announcements fa ON ci.source_id = fa.content_id
WHERE cfr.feature_option_id = ?
ORDER BY ci.first_posted DESC
LIMIT 5;
```

Fed to prompt as:
```
Recent activity (newest first):
1. [2026-02-21] {title} - {description}. {implications}
2. [2026-02-15] {title} - {description}. {implications}
...
```

---

## CLI Commands

### Regeneration

```bash
# Regenerate description for a specific feature
python -m src.cli regenerate feature <feature_id>

# Regenerate description for a specific feature option
python -m src.cli regenerate option <option_id>

# Regenerate meta_summary for a feature option
python -m src.cli regenerate meta-summary <option_id>

# Regenerate all features missing descriptions
python -m src.cli regenerate features --missing

# Regenerate all feature_options missing descriptions
python -m src.cli regenerate options --missing

# Regenerate all meta_summaries
python -m src.cli regenerate meta-summaries --all

# Dry run
python -m src.cli regenerate features --missing --dry-run
```

### General Content Triage

```bash
# List all content tagged as 'general'
python -m src.cli general list

# Show details of a specific item
python -m src.cli general show <content_id>

# Reassign to existing feature
python -m src.cli general assign <content_id> --feature <feature_id>

# Reassign to existing feature option
python -m src.cli general assign <content_id> --option <option_id>

# Create new feature and assign
python -m src.cli general assign <content_id> --new-feature "feature_id" "Feature Name"

# Create new feature option and assign
python -m src.cli general assign <content_id> --new-option "feature_id" "option_id" "Option Name"

# Interactive triage with suggested matches
python -m src.cli general triage

# Auto-assign high-confidence matches (>80%)
python -m src.cli general triage --auto-high

# Only items from last N days
python -m src.cli general triage --days 7

# Export suggestions to CSV
python -m src.cli general triage --export suggestions.csv
```

### Triage Interactive Flow

```
Reviewing 12 items tagged as 'general'...

[1/12] blog_664720 (2026-02-18)
Title: "Tips for using the new grading interface"
Preview: "Many instructors have asked about the recent SpeedGrader updates..."

Suggested matches:
  1. speedgrader (85% confidence) - keyword: "SpeedGrader", "grading"
  2. gradebook (60% confidence) - keyword: "grading"
  3. [skip] - keep as general
  4. [new] - create new feature/option
  5. [quit] - exit triage

Choice [1-5]:
```

Matching logic:
1. Keyword match against `CANVAS_FEATURES` names
2. Match against `feature_options.name` and `canonical_name`
3. Score by keyword hits (title matches weighted higher)
4. Show top 2-3 suggestions with confidence %

---

## Processing Flow

### Daily scrape (release/deploy notes)

```
1. Scrape release/deploy note page
   └── Parse page-level beta_date and production_date from intro paragraph

2. For each H4 entry:
   ├── Extract h4_title, anchor_id, raw_content, config snapshot
   ├── Parse [Added DATE] annotation if present (overrides page-level)
   ├── LLM generate: description, implications
   └── Insert into feature_announcements

3. For each feature_option referenced:
   ├── Upsert with beta_date, production_date
   ├── If status changed → regenerate implementation_status (template)
   ├── If first encounter → LLM generate description
   ├── If mention_type in ('announces', 'feedback'):
   │   └── Regenerate meta_summary from latest 5 content items
   └── Update last_updated timestamp

4. For each feature referenced:
   ├── If first encounter → LLM generate description
   └── Update last_updated timestamp
```

### Daily scrape (blog/Q&A posts)

```
1. Scrape blog/Q&A post
   ├── Insert/update content_items
   └── Scrape comments → insert into content_comments (PII-redacted)

2. If post links to feature/option:
   ├── Create feature_announcement entry
   │   ├── description: from initial post
   │   └── implications: from comments (weighted recent)
   ├── Add content_feature_refs link
   └── If mention_type in ('announces', 'feedback'):
       └── Regenerate meta_summary for linked feature_option

3. If no feature/option match:
   └── Assign to 'general' feature
```

### Comment update detection

```
1. Re-scrape existing blog/Q&A post
2. Compare comment_count with stored value
3. If new comments:
   ├── Insert new comments into content_comments
   ├── Regenerate feature_announcements.implications
   └── If linked to feature_option with 'announces'/'feedback':
       └── Regenerate meta_summary
```

---

## Website Display Structure

```
Feature: SpeedGrader
├── Description: "SpeedGrader is Canvas's inline grading tool..."
├── Related Content:
│   ├── [2026-02-21] [release_note] Performance improvements...
│   └── [2026-02-15] [deploy_note] Fixed submission loading bug...
└── Feature Options:
    └── SpeedGrader Performance Upgrades
        ├── Description: "Enables enhanced performance mode..."
        ├── Implementation Status: "In production since Feb 2026. Account-level setting."
        ├── Meta Summary: "Ready for wide deployment. Community feedback positive..."
        └── Related Content:
            ├── [2026-02-21] [release_note] Now in production...
            ├── [2026-02-15] [deploy_note] Fixed edge case...
            ├── [2026-02-10] [blog] Tips for rolling out...
            └── [2026-02-08] [question] Issues with large courses...
```

---

## Anonymity Principle

**No author/PII anywhere in the database.**

| Table | PII fields | Action |
|-------|------------|--------|
| `content_items` | None | ✓ |
| `feature_announcements` | None | ✓ |
| `feature_options` | None | ✓ |
| `content_comments` | No author field | ✓ |
| All tables | comment_text | Run through `redact_pii()` before storage |

PII redaction patterns:
- Emails: `\S+@\S+\.\S+` → `[email]`
- Reddit usernames: `u/\w+` → `[user]`
- Phone numbers: `\d{3}[-.]?\d{3}[-.]?\d{4}` → `[phone]`

---

## Deliverables

### Code Changes

| File | Changes |
|------|---------|
| `src/utils/database.py` | Clean v2.0 schema, new columns, new tables |
| `src/processor/content_processor.py` | New prompts, `generate_implementation_status()`, meta_summary logic |
| `src/scrapers/instructure_community.py` | Parse page-level beta/production dates, scrape comments |
| `src/cli.py` | **New file** - CLI for regeneration and triage |
| `src/main.py` | Updated flow for LLM generation triggers |
| `src/constants.py` | Any new status values |

### Documentation

| Doc | Content |
|-----|---------|
| `docs/database-schema.md` | Updated ERD and field descriptions |
| `docs/cli.md` | **New file** - CLI usage and examples |
| `README.md` | Add CLI section |

### Tests

| File | Coverage |
|------|----------|
| `tests/test_database.py` | New columns, lifecycle dates, content_comments |
| `tests/test_processor.py` | New prompts, implementation_status template, meta_summary triggers |
| `tests/test_cli.py` | **New file** - CLI commands |

---

## Migration

Fresh v2.0 database - no migration from v1.x. Clean rebuild.

---

## Dependencies

- This design must be implemented before the edtechnews website can consume the data
- Blocks website development

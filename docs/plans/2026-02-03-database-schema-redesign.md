# Database Schema Redesign

**Date:** 2026-02-03
**Status:** Approved

## Overview

Consolidate and restructure the database schema to support the edtechnews website integration. This redesign introduces a feature-centric data model where Canvas features and feature options are first-class entities that content references.

## Goals

1. Track source dates (first_posted, last_edited, last_comment_at) for all content
2. Model Canvas features and feature options as independent entities
3. Link content to features/feature options for cross-referencing
4. Eliminate redundant tracking tables
5. Formalize content types and feature categories as constants

---

## Schema Changes

### Tables to Drop

| Table | Reason |
|-------|--------|
| `discussion_tracking` | Replaced by source dates in content_items |
| `feature_tracking` | Replaced by features + feature_options tables |

### Tables to Modify

#### content_items

```sql
CREATE TABLE content_items (
    -- Identity
    content_id TEXT PRIMARY KEY,      -- Renamed from source_id, uses actual IDs not hashes
    content_type TEXT NOT NULL,       -- Formalized enum (see CONTENT_TYPES)
    url TEXT NOT NULL,
    title TEXT NOT NULL,              -- Clean title, no badges
    summary TEXT,                     -- LLM-generated summary

    -- Source dates (from the content source)
    first_posted TIMESTAMP,           -- When content was created
    last_edited TIMESTAMP,            -- When author last edited (nullable)
    last_comment_at TIMESTAMP,        -- Most recent comment (nullable)
    comment_count INTEGER DEFAULT 0,  -- Total comments

    -- Our tracking dates
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- When we first scraped
    last_checked_at TIMESTAMP,        -- When we last checked for updates

    -- Engagement (kept for sorting/filtering)
    engagement_score INTEGER DEFAULT 0,

    -- Deprecated (keep columns, stop using)
    -- source TEXT,                   -- Redundant with content_type
    -- content TEXT,                  -- Raw content, summary is sufficient
    -- published_date TIMESTAMP,      -- Renamed to first_posted
    -- sentiment TEXT,                -- Not used
    -- primary_topic TEXT,            -- Replaced by feature refs
    -- topics TEXT,                   -- Replaced by feature refs
    -- included_in_feed BOOLEAN       -- RSS-only concern
);

CREATE INDEX idx_content_type ON content_items(content_type);
CREATE INDEX idx_first_posted ON content_items(first_posted);
CREATE INDEX idx_last_comment_at ON content_items(last_comment_at);
```

### New Tables

#### features

Top-level Canvas features (~45 canonical features).

```sql
CREATE TABLE features (
    feature_id TEXT PRIMARY KEY,      -- e.g., 'speedgrader', 'new_quizzes'
    name TEXT NOT NULL,               -- e.g., 'SpeedGrader', 'New Quizzes'
    status TEXT DEFAULT 'active',     -- 'active', 'deprecated'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### feature_options

Sub-features with lifecycle state (announced in release notes).

```sql
CREATE TABLE feature_options (
    option_id TEXT PRIMARY KEY,       -- e.g., 'speedgrader-perf-upgrades'
    feature_id TEXT NOT NULL,         -- FK to features
    name TEXT NOT NULL,               -- e.g., 'Performance and usability upgrades for SpeedGrader'
    summary TEXT,                     -- Description
    status TEXT NOT NULL,             -- 'pending', 'preview', 'optional', 'default_optional', 'released'
    config_level TEXT,                -- 'account', 'course', 'both'
    default_state TEXT,               -- 'enabled', 'disabled'
    first_announced TIMESTAMP,        -- When first mentioned in release notes
    last_updated TIMESTAMP,
    FOREIGN KEY (feature_id) REFERENCES features(feature_id)
);

CREATE INDEX idx_feature_options_feature ON feature_options(feature_id);
CREATE INDEX idx_feature_options_status ON feature_options(status);
```

#### content_feature_refs

Junction table linking content to features and/or feature options.

```sql
CREATE TABLE content_feature_refs (
    content_id TEXT NOT NULL,         -- FK to content_items
    feature_id TEXT,                  -- FK to features (nullable)
    feature_option_id TEXT,           -- FK to feature_options (nullable)
    mention_type TEXT,                -- 'announces', 'discusses', 'questions', 'feedback'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (content_id, COALESCE(feature_id, ''), COALESCE(feature_option_id, '')),
    FOREIGN KEY (content_id) REFERENCES content_items(content_id),
    FOREIGN KEY (feature_id) REFERENCES features(feature_id),
    FOREIGN KEY (feature_option_id) REFERENCES feature_options(option_id),
    CHECK (feature_id IS NOT NULL OR feature_option_id IS NOT NULL)
);

CREATE INDEX idx_content_feature_refs_feature ON content_feature_refs(feature_id);
CREATE INDEX idx_content_feature_refs_option ON content_feature_refs(feature_option_id);
```

---

## Constants

### CONTENT_TYPES

```python
CONTENT_TYPES = {
    'release_note',
    'deploy_note',
    'changelog',
    'blog',
    'question',
    'reddit',
    'status',
}
```

### CANVAS_FEATURES

```python
CANVAS_FEATURES = {
    # Core Course Features
    'announcements': 'Announcements',
    'assignments': 'Assignments',
    'discussions': 'Discussions',
    'files': 'Files',
    'modules': 'Modules',
    'pages': 'Pages',
    'classic_quizzes': 'Quizzes (Classic)',
    'new_quizzes': 'New Quizzes',
    'syllabus': 'Syllabus',

    # Grading & Assessment
    'gradebook': 'Gradebook',
    'speedgrader': 'SpeedGrader',
    'rubrics': 'Rubrics',
    'outcomes': 'Outcomes',
    'mastery_paths': 'Mastery Paths',
    'peer_reviews': 'Peer Reviews',

    # Collaboration
    'collaborations': 'Collaborations',
    'conferences': 'Conferences',
    'groups': 'Groups',
    'chat': 'Chat',

    # Communication
    'inbox': 'Inbox',
    'calendar': 'Calendar',
    'notifications': 'Notifications',

    # User Interface
    'dashboard': 'Dashboard',
    'global_navigation': 'Global Navigation',
    'profile_settings': 'Profile and User Settings',
    'rich_content_editor': 'Rich Content Editor (RCE)',

    # Portfolio & Showcase
    'eportfolios': 'ePortfolios',
    'student_eportfolios': 'Canvas Student ePortfolios',

    # Analytics & Data
    'canvas_analytics': 'Canvas Analytics',
    'canvas_data_services': 'Canvas Data Services',

    # Add-on Products
    'canvas_catalog': 'Canvas Catalog',
    'canvas_studio': 'Canvas Studio',
    'canvas_commons': 'Canvas Commons',
    'student_pathways': 'Canvas Student Pathways',
    'mastery_connect': 'Mastery Connect',
    'parchment_badges': 'Parchment Digital Badges',

    # Mobile
    'canvas_mobile': 'Canvas Mobile',

    # Administration
    'course_import': 'Course Import Tool',
    'blueprint_courses': 'Blueprint Courses',
    'sis_import': 'SIS Import',
    'external_apps_lti': 'External Apps (LTI)',
    'api': 'Web Services / API',
    'account_settings': 'Account Settings',
    'themes_branding': 'Themes/Branding',
    'authentication': 'Authentication',

    # Specialized
    'canvas_elementary': 'Canvas for Elementary',

    # Catch-all
    'general': 'General',
}
```

### FEATURE_OPTION_STATUSES

```python
FEATURE_OPTION_STATUSES = {
    'pending',          # Announced but not yet available
    'preview',          # Feature preview / beta
    'optional',         # Available but disabled by default
    'default_optional', # Enabled by default, can be disabled
    'released',         # Fully released, no longer a feature option
}
```

---

## Scraping Changes

### Date Extraction

For each content type, extract from the DOM:

| Field | Community Posts | Reddit | Status |
|-------|-----------------|--------|--------|
| `first_posted` | First `<time datetime>` | `submission.created_utc` | `created_at` |
| `last_edited` | "Updated" time element | N/A | N/A |
| `last_comment_at` | Last comment time | `submission.comments` scan | `updated_at` |
| `comment_count` | Pagination "X of Y" | `submission.num_comments` | N/A |

### content_id Generation

Use actual IDs from source, not hashes:

| Content Type | Format | Example |
|--------------|--------|---------|
| Community | `{content_type}_{numeric_id}` | `blog_664616` |
| Reddit | `reddit_{submission_id}` | `reddit_1i5abc` |
| Status | `status_{incident_id}` | `status_xyz789` |

---

## Migration Strategy

1. **Add new columns** to content_items (first_posted, last_edited, last_comment_at, last_checked_at)
2. **Create new tables** (features, feature_options, content_feature_refs)
3. **Populate features** with canonical CANVAS_FEATURES
4. **Backfill dates** from existing data where possible
5. **Stop writing** to deprecated columns
6. **Leave deprecated columns** in place (no DROP COLUMN needed)

---

## Query Examples

### All content about a feature (direct + via options)

```sql
SELECT DISTINCT c.*
FROM content_items c
JOIN content_feature_refs r ON c.content_id = r.content_id
LEFT JOIN feature_options fo ON r.feature_option_id = fo.option_id
WHERE r.feature_id = 'new_quizzes'
   OR fo.feature_id = 'new_quizzes'
ORDER BY c.first_posted DESC;
```

### Active feature options for a feature

```sql
SELECT * FROM feature_options
WHERE feature_id = 'speedgrader'
  AND status IN ('preview', 'optional', 'default_optional')
ORDER BY first_announced DESC;
```

### Recent content with activity

```sql
SELECT * FROM content_items
WHERE last_comment_at > datetime('now', '-7 days')
ORDER BY last_comment_at DESC;
```

---

## Decisions

| Question | Decision | Reasoning |
|----------|----------|-----------|
| Track `views` count? | **Skip** | Inconsistent availability across sources. Can add later if needed. |
| `release_note_url` on feature_options? | **Skip** | Derivable from junction table (find content where mention_type='announces') |
| `content_type` on feature_options? | **Skip** | The announcing content already has content_type |

---

## Dependencies

- This design must be implemented in canvas-rss before the edtechnews website can consume the data
- Blocks: `docs/plans/2026-02-03-canvas-rss-implementation-plan.md` (needs revision)

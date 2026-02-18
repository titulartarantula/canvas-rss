# Canonical Feature Options Source of Truth

**Date:** 2026-02-18
**Status:** Approved

## Problem

Feature options and previews are currently parsed from individual release note HTML tables, using heuristics (`is_feature_option` property) and manual overrides (`classification_overrides.yaml`) to classify them. This is fragile and indirect — release notes are announcements, not a definitive registry.

## Solution

Use the [Canvas Feature Option Summary](https://community.instructure.com/en/kb/articles/531316-unknown) as the canonical source of truth for feature options. This single page lists every feature option and preview with its name, description, configuration, and category. Release notes continue to provide announcement timeline entries and lifecycle dates.

## Key Concepts

### Lifecycle Stage vs Availability

These are orthogonal:

- **Lifecycle stage** (from canonical page): what *kind* of feature option is this
  - `preview` — in active development, has user groups for feedback
  - `stable` — released, available for admin configuration (may be permanent)
  - `pending` — will be enforced for all users, last stage before removal

- **Availability** (from release/deploy note dates): *when* can you use it
  - `beta_date` — when available in beta environment
  - `production_date` — when available in production
  - Derived at display time, not stored

### Lifecycle Progression

```
Feature Preview → Stable (Optional / Default Optional) → Pending → Enforced (removed)
```

Not all features follow every stage. Many stay `stable` permanently. `pending` means the feature will be forced on and eventually removed from the options page (e.g., New Quizzes replacing Classic Quizzes).

### Configuration States

The canonical page categories "Optional" and "Default Optional" are not independent categories — they describe the default configuration state. "Optional" = Disabled/Unlocked, "Default Optional" = Enabled/Unlocked. The real data model captures the actual state.

**Account-level states** (two dimensions: enabled/disabled × locked/unlocked):

| Value | Meaning |
|---|---|
| `enabled_unlocked` | On by default, subaccounts/courses can override |
| `enabled_locked` | On, subaccounts/courses cannot override (admin chose to lock) |
| `disabled_unlocked` | Off by default, subaccounts/courses can enable |
| `disabled_locked` | Off, subaccounts/courses cannot override (admin chose to lock) |
| `enabled` | On, account-only — no lock concept, no lower-level override possible |
| `disabled` | Off, account-only — no lock concept, no lower-level override possible |
| `csm_managed` | Must be configured by a Customer Success Manager |
| `lti_required` | Requires LTI configuration, not a standard toggle |
| `user_setting` | User-level setting, not account/course level |
| `N/A` | Feature does not exist at this level |

The distinction between `disabled_locked` and `disabled` (no lock): locked means the lock toggle exists but the admin chose to lock it; bare `disabled` means the feature is account-only and "will not display a locked or unlocked icon" (per Canvas docs). There is no lower level that could override it.

**Course-level states** (no lock concept at course level):

| Value | Meaning |
|---|---|
| `enabled` | On in this course |
| `disabled` | Off in this course |
| `N/A` | Feature does not exist at course level |

### Beta vs Production Configuration

Some features have different configuration in beta vs production environments. Example: Enhanced Rubrics is Enabled/Unlocked in beta but Disabled/Unlocked in production. The schema captures both.

## Schema Changes

### `feature_options` table

**Remove columns:**
- `status` — replaced by `lifecycle_stage` (no longer computed from dates)
- `config_level` — replaced by per-level state columns
- `default_state` — encoded in state values

**Add columns:**
```sql
lifecycle_stage       TEXT    -- 'preview' | 'stable' | 'pending'
prod_account_state    TEXT    -- see account-level states above
prod_course_state     TEXT    -- 'enabled' | 'disabled' | 'N/A'
beta_account_state    TEXT    -- same as prod_account, default 'N/A'
beta_course_state     TEXT    -- same as prod_course, default 'N/A'
source                TEXT    -- 'canonical_page' | 'release_notes'
doc_url               TEXT    -- documentation link from canonical page
```

**Unchanged columns:** `option_id`, `canonical_name`, `name`, `feature_id`, `description`, `meta_summary`, `user_group_url`, `beta_date`, `production_date`, `deprecation_date`, `created_at`, `llm_generated_at`

### Migration

1. Add new columns with defaults
2. Map existing data:
   - `status` → `lifecycle_stage`: preview→preview, optional→stable, default_optional→stable, pending→pending, beta→stable, released→stable
   - `config_level` + `default_state` → state columns (best-effort mapping)
3. Drop old columns (`status`, `config_level`, `default_state`)
4. Delete `OPTION_STATUS_SQL` from `src/api/database.py`
5. Review `classification_overrides.yaml` — some overrides may be unnecessary with canonical source

### `feature_announcements` table

No changes. Keeps its configuration snapshot columns (`enable_location_account`, `enable_location_course`, `subaccount_config`) — these represent config at time of announcement.

## New Scraper

New scraper function for the canonical page, run on the same schedule as release notes.

**Source URL:** `https://community.instructure.com/en/kb/articles/531316-unknown`

**Parsing:**
- 4 HTML sections map to `lifecycle_stage`:
  - "Pending Feature Options" → `pending`
  - "Optional Features" → `stable`
  - "Default Optional Features" → `stable` (with `prod_account_state = enabled_unlocked`)
  - "Feature Previews" → `preview`
- Per entry: name, description, configuration text (parsed into 4 state columns), doc URL, user group URL

**Upsert logic:**
- Match by name to existing `feature_options` records
- If found: update canonical fields (lifecycle_stage, state columns, description, doc_url, user_group_url, source='canonical_page')
- If not found: create new record with `source = 'canonical_page'`

**Release note scraper changes:**
- When classifying features, first match against existing options (seeded from canonical page)
- If matched: only create `feature_announcement` entry and update dates. Do not overwrite canonical fields.
- If no match: create new option with `source = 'release_notes'` (may be picked up by canonical page later)

## API Changes

### `GET /api/options`
- Return `lifecycle_stage` instead of computed `status`
- Return 4 state columns instead of `config_level` and `default_state`
- Add filter: `lifecycle_stage=preview|stable|pending`
- Add derived `availability` field: computed from `beta_date`/`production_date` vs today (`in_beta`, `in_production`, `upcoming_beta`, `upcoming_production`, `no_dates`)

### `GET /api/options/{option_id}`
- Same field changes as list
- Configuration section returns 4 state columns directly
- Announcements and community posts unchanged

### `GET /api/features/{feature_id}`
- Embedded options use `lifecycle_stage` instead of `status`

### `GET /api/dashboard`
- Update any option status references to use `lifecycle_stage`

## Frontend Changes

### Options page (`/options`)
- Replace status filter with lifecycle_stage filter (Preview / Stable / Pending)
- Update pills: preview (blue), stable (green), pending (amber)
- Show config as compact representation: "Prod: Account (Disabled/Unlocked), Course (Disabled)"
- Show beta config only when different from prod
- Add availability indicator from dates: "In production", "Coming to beta Mar 15", etc.

### Option detail page (`/options/{id}`)
- Lifecycle stage shown prominently
- Config section: grid showing all 4 state slots
- Beta vs prod differences highlighted when they differ

### Feature detail page (`/features/{id}`)
- Options list uses lifecycle_stage pills

### New: Glossary page (`/glossary`)
Reference page linked from navigation:
1. **Lifecycle Stages** — preview, stable, pending definitions with progression diagram
2. **Configuration States** — full table of enabled/disabled × locked/unlocked at account and course level, including account-only (no lock) explanation
3. **Special Configurations** — CSM managed, LTI required, user setting
4. **Availability** — beta_date and production_date meaning, upcoming vs released

## Data Flow (After)

```
┌──────────────────────────────────────────────────────────┐
│ CANONICAL PAGE SCRAPER (new)                             │
│ Source: community.instructure.com/en/kb/articles/531316  │
│ Provides: identity, lifecycle_stage, config states,      │
│           description, doc_url, user_group_url           │
│ Cadence: same schedule as release notes                  │
└────────────────────┬─────────────────────────────────────┘
                     │ upsert
                     ▼
┌──────────────────────────────────────────────────────────┐
│ feature_options table                                    │
│ Canonical fields from page, dates from release notes     │
└────────────────────▲─────────────────────────────────────┘
                     │ link announcements + update dates
┌────────────────────┴─────────────────────────────────────┐
│ RELEASE NOTE SCRAPER (modified)                          │
│ Source: release/deploy notes pages                       │
│ Provides: beta_date, production_date,                    │
│           feature_announcements (H4 snapshots)           │
│ No longer creates feature_options from scratch if        │
│ canonical page has already seeded the record             │
└──────────────────────────────────────────────────────────┘
```

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.3] - 2026-02-02

### Changed

- **Skip redundant LLM summarization** for release/deploy notes - they already have per-feature summaries
- **Renamed `has_v130_badge` to `has_tracking_badge`** - version-agnostic naming for tracking system

### Fixed

- Reduced unnecessary Gemini API calls for content types with structured descriptions

## [1.3.0] - 2026-02-01

### Added

- **[NEW]/[UPDATE] badges** for all content types in RSS feed titles
- **Granular feature tracking** for Release Notes - each feature tracked individually
- **Granular change tracking** for Deploy Notes - each change tracked individually
- **Discussion tracking tables** in SQLite database (`discussion_tracking`, `feature_tracking`)
- **First-run flood prevention** - limits new items on first run (5 Q&A, 5 Blog, 3 Release features, 3 Deploy changes)
- **New dataclasses** for structured content:
  - `DiscussionUpdate` - tracks Q&A/Blog post comment changes
  - `Feature`, `FeatureTableData`, `ReleaseNotePage` - parsed release notes
  - `DeployChange`, `DeployNotePage` - parsed deploy notes
  - `UpcomingChange` - upcoming Canvas changes/deprecations
- **Classification functions** for update detection:
  - `classify_discussion_posts()` - detects new posts and posts with new comments
  - `classify_release_features()` - detects new features in release notes
  - `classify_deploy_changes()` - detects new changes in deploy notes
- **LLM summarization methods** for new content types:
  - `summarize_feature()` - summarizes release note features
  - `summarize_deploy_change()` - summarizes deploy note changes
  - `format_availability()` - formats feature availability info
- **RSS formatting functions**:
  - `build_discussion_title()` - formats titles with [NEW]/[UPDATE] badges
  - `format_discussion_description()` - formats descriptions with comment info
  - `build_release_note_entry()` - formats release note RSS entries
  - `build_deploy_note_entry()` - formats deploy note RSS entries
- **Database methods** for tracking:
  - `get_discussion_tracking()`, `upsert_discussion_tracking()`
  - `get_feature_tracking()`, `upsert_feature_tracking()`, `get_features_for_parent()`
  - `is_discussion_tracking_empty()`, `is_feature_tracking_empty()`, `is_first_run_for_type()`
- Comprehensive integration test suite (251 tests for v1.3.0 features)

### Changed

- RSS titles now show `[NEW]` for first-time items and `[UPDATE]` for items with new activity
- Q&A and Blog titles include source label: `[NEW] - Question Forum - Title`
- Release/Deploy notes use simpler format: `[NEW] Canvas Release Notes (2026-02-21)`

## [1.2.0] - 2026-02-01

### Added

- Full discussion tracking for blog and question forum posts (all posts now captured)
- Discussion state summaries for posts with new comment activity
- `[Blog Update]` and `[Q&A Update]` badges for posts with new comments
- Enhanced summarization prompts focused on "where the discussion is at"
- Version number displayed in startup log

### Changed

- Removed engagement threshold filter from question forum scraper (was MIN_QA_ENGAGEMENT=5)
- Removed Product Overview filter from blog scraper (now captures all blog posts)
- Posts with new comments now use `_updated` content type for specialized summarization

## [1.1.2] - 2026-02-01

### Added

- Infinite scroll support for loading all deploy notes from the page
- First-run detection to capture historical posts without date filtering
- INFO-level logging for filtered post counts

### Fixed

- Deploy notes scraping now finds all posts instead of just initially visible ones
- First run now captures all available history instead of just last 24 hours

## [1.1.1] - 2026-01-31

### Fixed

- Fixed Deploys tab click with improved Playwright text selectors
- Scraper now properly switches between Releases and Deploys views
- Deploy notes are now correctly classified with post_type="deploy_note"

## [1.1.0] - 2026-01-31

### Added

- Separate scraping of Releases and Deploys tabs for better content classification
- Discussion tracking for high-engagement Q&A posts
- Source labeling in RSS feed items

### Changed

- Deploy notes now scraped from dedicated Deploys tab instead of title-based classification

## [1.0.0] - 2026-01-31

### Added
- Multi-source RSS aggregation from Instructure Community, Reddit, and Canvas Status page
- Playwright-based web scraping for Instructure Community content
- PRAW integration for Reddit API access
- Google Gemini AI-powered summarization and sentiment analysis
- Topic classification by Canvas feature (Gradebook, Assignments, Quizzes, etc.)
- SQLite-backed deduplication and history tracking
- RSS feed generation with feedgen
- Docker and Docker Compose deployment configuration
- Cron scheduling for daily automated runs
- Privacy-focused content processing with PII redaction
- Comprehensive test suite (270+ tests)
- MS Teams webhook notification support

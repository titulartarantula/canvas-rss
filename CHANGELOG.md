# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

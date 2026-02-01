# Project State

## Current Phase

**Phase 9: v1.3.0 - Unified Tracking** - Complete. [NEW]/[UPDATE] badges with granular tracking.

## Active Tasks

| Task                                | Agent   | Status   | Notes                          |
|-------------------------------------|---------|----------|--------------------------------|
| Docker deployment                   | DevOps  | Complete | All containers working         |
| GitHub README                       | Docs    | Complete | README.md created              |
| Fix Deploys tab click               | Coding  | Complete | Improved selectors, dual-view  |
| Update tests for Deploys tab fix   | Testing | Complete | 47 scraper tests pass          |
| Release v1.1.1 documentation        | Docs    | Complete | VERSION, CHANGELOG updated     |
| Full discussion tracking            | Coding  | Complete | All blog/Q&A posts captured    |
| Release v1.2.0 documentation        | Docs    | Complete | VERSION, CHANGELOG, STATE.md   |
| Security audit                      | Coding  | Complete | Full audit of 4 areas          |
| Security remediation                | Coding  | Complete | All high-severity issues fixed |
| v1.3.0 unified implementation       | Coding  | Complete | 30 tasks, 251 tests pass       |
| Release v1.3.0 documentation        | Docs    | Complete | VERSION, CHANGELOG, README     |

## Completed

### Phase 9: v1.3.0 - Unified Tracking (Complete)

- [x] Database tables for discussion and feature tracking
- [x] Dataclasses for Release Notes, Deploy Notes, Discussion Updates
- [x] Classification functions for [NEW]/[UPDATE] detection
- [x] LLM summarization for features and deploy changes
- [x] RSS formatting with [NEW]/[UPDATE] badges
- [x] First-run flood prevention limits
- [x] Integration tests (251 tests)
- [x] Documentation updates

### Phase 8: Security Hardening (Complete)

- [x] Security audit - input sanitization, credential handling, Docker config, PII data flow
- [x] PII redaction for titles in content_processor.py
- [x] Defensive sanitization in exception handler
- [x] Docker security options (no-new-privileges, cap_drop, resource limits)
- [x] Non-root feed-server with read-only filesystem
- [x] Supercronic replacement for cron (runs as non-root)
- [x] Health checks for both containers

### Phase 4: Content Processing (Complete)

- [x] Implement content_processor.py - ContentProcessor class with Gemini API integration

### Phase 5: RSS Generation (Complete)

- [x] Implement rss_builder.py - RSSBuilder class with feedgen integration
- [x] Write unit tests for rss_builder.py (59 tests, all passing)
- [x] Fix None items bug in create_feed() - filter None before sorting

### Phase 2: Core Infrastructure (Complete)

- [x] Complete database.py - insert_item, get_recent_items, record_feed_generation
- [x] Implement status_page.py - StatusPageMonitor with Instructure API integration
- [x] Implement reddit_client.py - RedditMonitor with PRAW integration
- [x] Write unit tests for database.py (20 tests)
- [x] Write unit tests for status_page.py (20 tests)
- [x] Write unit tests for reddit_client.py (19 tests)

### Phase 1: Project Scaffolding (Complete)

- [x] Create CLAUDE.md - Agent coordination file
- [x] Create STATE.md - Task tracking file
- [x] Create directory structure (src/, tests/, config/, etc.)
- [x] Create requirements.txt
- [x] Create .env.example
- [x] Create .gitignore
- [x] Create config/config.yaml
- [x] Create placeholder modules with stubs:
  - src/main.py
  - src/scrapers/instructure_community.py
  - src/scrapers/reddit_client.py (now implemented)
  - src/scrapers/status_page.py (now implemented)
  - src/processor/content_processor.py
  - src/generator/rss_builder.py
  - src/utils/logger.py (implemented)
  - src/utils/database.py (now complete)
- [x] Create test file placeholders

## Blocked

- None

## Next Up (Phase 3 Tasks)

- [x] Implement instructure_community.py (Playwright web scraping) - COMPLETE
- [x] Implement content_processor.py (Gemini API integration) - COMPLETE
- [x] Implement rss_builder.py (feedgen RSS generation) - COMPLETE

## Known Issues

- None

---

## Phase Progress

| Phase | Status | Description |
|-------|--------|-------------|
| 1. Scaffolding | Complete | Directory structure, configs |
| 2. Infrastructure | Complete | Logger, database, models, tests |
| 3. Scrapers | Complete | Status page (complete), Reddit (complete), Instructure (complete) |
| 4. Processing | Complete | Gemini integration, sanitization |
| 5. RSS Generation | Complete | feedgen RSS builder |
| 6. Main App | Complete | Orchestration |
| 7. Docker | Complete | Container setup, cron scheduling |
| 8. Security | Complete | Audit and hardening |
| 9. v1.3.0 Tracking | Complete | [NEW]/[UPDATE] badges, granular tracking |

---

## Files Created

```
canvas-rss/
├── README.md
├── CLAUDE.md
├── STATE.md
├── Dockerfile
├── docker-compose.yml
├── docker-entrypoint.sh
├── .dockerignore
├── requirements.txt
├── .env.example
├── .gitignore
├── config/
│   └── config.yaml
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── instructure_community.py
│   │   ├── reddit_client.py
│   │   └── status_page.py
│   ├── processor/
│   │   ├── __init__.py
│   │   └── content_processor.py
│   ├── generator/
│   │   ├── __init__.py
│   │   └── rss_builder.py
│   └── utils/
│       ├── __init__.py
│       ├── database.py
│       └── logger.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_database.py
│   ├── test_scrapers.py
│   ├── test_processor.py
│   └── test_rss_builder.py
├── data/         (gitignored)
├── output/       (gitignored)
├── logs/         (gitignored)
└── specs/
    └── canvas-rss.md
```

---

## Recent Changes

- 2026-02-01: v1.3.0 Unified Tracking Implementation - Coding Agent
  - Added [NEW]/[UPDATE] badges to RSS feed titles
  - Implemented granular feature tracking for Release Notes
  - Implemented granular change tracking for Deploy Notes
  - Added discussion tracking for Q&A and Blog posts
  - Added first-run flood prevention (5 Q&A, 5 Blog, 3 features, 3 changes)
  - Created 30 implementation tasks following TDD methodology
  - Added 251 new tests for v1.3.0 features
  - New dataclasses: DiscussionUpdate, Feature, FeatureTableData, ReleaseNotePage, DeployChange, DeployNotePage, UpcomingChange
  - New database tables: discussion_tracking, feature_tracking
  - New classification functions: classify_discussion_posts, classify_release_features, classify_deploy_changes
  - New RSS functions: build_discussion_title, format_discussion_description, build_release_note_entry, build_deploy_note_entry
- 2026-02-01: Security hardening - Coding Agent
  - Full security audit (input sanitization, credentials, Docker, PII handling)
  - Added PII redaction for titles (emails, usernames, phone numbers)
  - Added defensive sanitization in exception handler
  - Docker: Added security_opt (no-new-privileges), cap_drop/cap_add, resource limits
  - Docker: Feed-server now runs as non-root (user 1000:1000) with read_only filesystem
  - Docker: Replaced cron with supercronic (non-root cron alternative)
  - Docker: Added health checks for both containers
  - Docker: Restricted env.sh file permissions (chmod 600)
- 2026-02-01: Release v1.2.0 - Full discussion tracking - Coding/Docs Agent
  - Removed engagement filter from question forum (all posts now captured)
  - Removed Product Overview filter from blog (all blog posts now captured)
  - Added discussion state summaries with `_updated` content types
  - Added `[Blog Update]` and `[Q&A Update]` RSS badges
  - Added version logging at startup
- 2026-01-31: Fixed Deploys tab click with improved Playwright selectors - Coding Agent
  - Added `_click_deploys_tab` method with text-based selectors
  - Updated `scrape_release_notes` to scrape both Releases and Deploys views
  - All 47 Instructure scraper tests pass - Testing Agent
- 2026-01-31: Created README.md for GitHub - Docs Agent
- 2026-01-30: Docker Phase complete - DevOps Agent
  - Created Dockerfile (python:3.11-slim, Playwright, cron)
  - Created docker-compose.yml (aggregator + feed-server services)
  - Created docker-entrypoint.sh (volume permissions, cron setup)
  - Added .dockerignore
  - Migrated from google.generativeai to google.genai SDK
  - Added configurable environment variables (GEMINI_MODEL, CRON_SCHEDULE, TZ, FEED_PORT, FEED_HOST)
  - Added rate limiting with exponential backoff retry for Gemini API
- 2026-01-30: Testing Agent completed main.py integration tests (30 tests, all passing)
- 2026-01-30: Implemented main.py orchestration with conversion functions (Coding Agent)
- 2026-01-30: Testing Agent completed instructure_community.py unit tests (46 tests, all passing)
- 2026-01-30: Implemented instructure_community.py with Playwright sync API (InstructureScraper class) - Coding Agent
- 2026-01-30: Testing Agent completed content_processor.py unit tests (75 tests, all passing)
- 2026-01-30: Implemented content_processor.py with Gemini API integration - Coding Agent
- 2026-01-30: Testing Agent completed rss_builder.py unit tests (59 tests, 58 passed, 1 xfail)
- 2026-01-30: Implemented rss_builder.py with feedgen (RSSBuilder class) - Coding Agent
- 2026-01-30: Testing Agent completed unit tests (63 tests total, all passing)
- 2026-01-30: Implemented reddit_client.py with PRAW integration (RedditMonitor class)
- 2026-01-30: Implemented status_page.py with Instructure status API integration
- 2026-01-30: Completed database.py with insert_item, get_recent_items, record_feed_generation
- 2026-01-29: Phase 1 complete - all scaffolding files created
- 2026-01-29: Project initialized with CLAUDE.md and STATE.md

---

## Test Results (2026-02-01)

320+ tests total (251 for v1.3.0 features alone)

### test_database.py (20 tests)

- Database initialization and schema creation
- `insert_item()` with ContentItem dataclass
- `insert_item()` duplicate handling (returns -1 for existing items)
- `insert_item()` with topics JSON serialization
- `insert_item()` with datetime and string published_date
- `get_recent_items()` returns items within days
- `get_recent_items()` with multiple items
- `get_recent_items()` deserializes topics JSON
- `get_recent_items()` handles invalid JSON gracefully
- `record_feed_generation()` basic functionality
- `record_feed_generation()` INSERT OR REPLACE behavior
- `item_exists()` deduplication checking
- `close()` connection management

### test_scrapers.py - StatusPageMonitor (20 tests)

- StatusPageMonitor initialization
- Custom timeout configuration
- `_parse_datetime()` ISO 8601 parsing (valid, empty, invalid)
- `_extract_incident_content()` from updates
- `_extract_incident_content()` limits to 3 updates
- `get_recent_incidents()` with mocked API
- `get_recent_incidents()` filters old incidents
- `get_recent_incidents()` request/JSON error handling
- `get_current_status()` with mocked API
- `get_current_status()` error handling
- `get_unresolved_incidents()` with mocked API
- Incident dataclass properties

### test_scrapers.py - RedditMonitor (19 tests)

- RedditMonitor initialization with/without credentials
- Default subreddits and keywords configuration
- Graceful handling when PRAW not installed
- RedditPost dataclass properties
- `anonymize()` method on RedditPost
- `_submission_to_post()` for text posts
- `_submission_to_post()` for link posts
- `_submission_to_post()` deleted author handling
- `_submission_to_post()` content truncation (2000 chars)
- `search_canvas_discussions()` without Reddit client
- `search_subreddits()` deduplication
- `get_top_discussions()` limit enforcement
- `get_subreddit_posts()` sort options (new, hot, top, rising)
- `get_subreddit_posts()` error handling

### test_scrapers.py - InstructureScraper (46 tests)

#### Dataclasses (8 tests)

- ReleaseNote creation with all fields
- ReleaseNote default values (likes=0, comments=0)
- ReleaseNote `source` property returns "community"
- ReleaseNote `source_id` property returns unique ID based on URL
- ReleaseNote `source_id` consistent for same URL
- ChangeLogEntry creation with all fields
- ChangeLogEntry `source` property returns "community"
- ChangeLogEntry `source_id` property returns unique ID

#### Initialization (6 tests)

- Default headless=True initialization
- Headless=False initialization
- Custom rate_limit_seconds
- Graceful handling when Playwright not installed
- Graceful handling when browser fails to launch
- Class constants defined correctly

#### Date Parsing (15 tests)

- `_parse_relative_date()` "X minutes ago" format
- `_parse_relative_date()` "X hours ago" format
- `_parse_relative_date()` "X days ago" format
- `_parse_relative_date()` "Yesterday" format
- `_parse_relative_date()` "Today" format
- `_parse_relative_date()` ISO 8601 format
- `_parse_relative_date()` ISO with Z suffix
- `_parse_relative_date()` empty string returns None
- `_parse_relative_date()` None returns None
- `_parse_relative_date()` invalid string returns None
- `_parse_relative_date()` "just now" format
- `_is_within_hours()` returns True for datetime within hours
- `_is_within_hours()` returns False for datetime outside hours
- `_is_within_hours()` returns False for None datetime
- `_is_within_hours()` handles naive datetime

#### Scraping (7 tests)

- `scrape_release_notes()` returns empty when browser is None
- `scrape_release_notes()` successful scrape returns ReleaseNote list
- `scrape_release_notes()` handles navigation errors gracefully
- `scrape_release_notes()` filters posts to last 24 hours
- `scrape_changelog()` returns empty when browser is None
- `scrape_changelog()` successful scrape returns ChangeLogEntry list
- `scrape_changelog()` handles navigation errors gracefully

#### Reactions (4 tests)

- `get_community_reactions()` returns zeros when browser is None
- `get_community_reactions()` returns dict with likes, comments, views
- `get_community_reactions()` handles invalid URL gracefully
- `get_community_reactions()` handles timeout gracefully

#### Cleanup (6 tests)

- `close()` cleans up browser resources
- `close()` safe to call multiple times
- `close()` works with partial initialization
- `__enter__` returns self
- `__exit__` calls close()
- `close()` handles errors during cleanup gracefully

### test_processor.py (75 tests)

#### ContentProcessor Initialization (5 tests)

- Initialization with API key provided directly
- Initialization with API key from environment variable
- Initialization without API key (model is None)
- Graceful handling when google-generativeai not installed
- Handling of model initialization errors

#### deduplicate() (6 tests)

- Empty list returns empty list
- Filters out items that exist in database
- Keeps items that don't exist in database
- Handles None items gracefully
- Mixed existing and new items
- Database error includes item (fail-safe behavior)

#### summarize_with_llm() (7 tests)

- Empty content returns empty string
- None content returns empty string
- Model None returns truncated content (fallback)
- Long content truncated in fallback mode
- Successful API call returns summary
- API error returns empty string
- Long API responses truncated to 300 chars

#### analyze_sentiment() (9 tests)

- Empty/None content returns "neutral"
- Model None returns "neutral"
- Detects positive sentiment
- Detects neutral sentiment
- Detects negative sentiment
- Invalid response defaults to "neutral"
- API error defaults to "neutral"
- Case-insensitive matching

#### classify_topic() (8 tests)

- Empty/None content returns empty list
- Model None returns empty list
- Returns valid topics from TOPIC_CATEGORIES
- Filters out invalid topics
- Case-insensitive matching
- Returns max 3 topics
- API error returns empty list

#### sanitize_html() (11 tests)

- Empty/None content returns empty string
- Allows safe tags (p, br, strong, em, ul, ol, li, a, h3)
- Strips disallowed tags (div, span, h1)
- Strips script tags
- Preserves href attribute on links
- Strips onclick and event attributes
- Strips style attributes

#### redact_pii() (10 tests)

- Empty/None content returns empty string
- Redacts email addresses to "[email]"
- Redacts Reddit usernames (u/username) to "[user]"
- Redacts phone numbers (various formats) to "[phone]"
- Handles multiple occurrences
- Preserves non-PII content

#### enrich_with_llm() (9 tests)

- Empty/None list returns empty list
- Enriches single item without model (fallback behavior)
- Handles None items in list
- Sanitizes HTML content
- Redacts PII
- Full enrichment with model (summary, sentiment, topics)
- Handles item exceptions gracefully
- Processes multiple items

#### Constants and ContentItem (10 tests)

- TOPIC_CATEGORIES defined correctly
- ALLOWED_TAGS defined correctly
- ALLOWED_ATTRIBUTES defined correctly
- PII patterns (email, reddit user, phone) defined and working
- ContentItem creation and default values
- ContentItem with all fields populated
- ContentItem topics=None becomes empty list via __post_init__

### test_rss_builder.py (59 tests)

#### Initialization (7 tests)

- Default values (title, link, description)
- Custom title, link, description
- FeedGenerator properly initialized
- Language set to en-us

#### Emoji Prefix (5 tests)

- `_get_emoji_prefix()` for community, reddit, status sources
- Unknown source returns empty string
- Case-insensitive lookup

#### Category (5 tests)

- `_get_category()` for community (Release Notes), reddit (Community), status (Status)
- Unknown source returns "General"
- Case-insensitive lookup

#### Format Description (7 tests)

- Description with summary, sentiment, topics sections
- Uses content if no summary (truncated to 500 chars)
- Empty fields produce empty description
- All sections combined properly

#### add_item() (16 tests)

- Basic item addition
- Emoji prefix by source (community, reddit, status)
- None item skipped without error
- Missing URL logs warning but continues
- DateTime published_date (timezone-aware and naive)
- ISO string published_date (with Z and +00:00 suffix)
- Invalid date string uses current time
- None published_date uses current time
- Category from source
- Topics as additional categories
- GUID from source_id or URL fallback

#### create_feed() (9 tests)

- Empty list returns valid XML
- None items parameter defaults to empty
- Returns UTF-8 string
- Items sorted by priority (community > status > reddit)
- Skips None items (with workaround - bug documented)
- Handles item exceptions gracefully
- Valid XML structure
- Includes feed metadata
- **XFAIL**: None items in list should be filtered before sorting (bug)

#### save_feed() (5 tests)

- Creates output file
- Creates parent directories if needed
- Writes UTF-8 encoded content
- Overwrites existing file
- Produces valid XML file

#### Source Constants (3 tests)

- SOURCE_EMOJIS defined correctly
- SOURCE_CATEGORIES defined correctly
- SOURCE_PRIORITY defined correctly

#### Integration (2 tests)

- Full workflow with multiple sources
- Empty feed workflow

### test_main.py (30 tests)

#### CommunityPostToContentItem (7 tests)

- Converts CommunityPost basic fields
- Calculates engagement score from likes and comments
- Converts ReleaseNote dataclass
- Converts ChangeLogEntry dataclass
- Preserves source_id
- Handles zero engagement
- Returns ContentItem type

#### RedditPostToContentItem (6 tests)

- Converts RedditPost basic fields
- Calculates engagement score from score and num_comments
- Anonymizes author during conversion
- Preserves source_id
- Handles zero engagement
- Returns ContentItem type

#### IncidentToContentItem (9 tests)

- Converts Incident basic fields
- Prefixes title with impact level (MAJOR)
- Prefixes title with CRITICAL impact
- No prefix for "none" impact
- No prefix for empty impact
- Uses created_at for published_date
- Engagement score is always 0
- Preserves source_id
- Returns ContentItem type

#### MainIntegration (8 tests)

- Main workflow with no items
- Main workflow with items from all sources
- Main creates output directory
- Main writes feed.xml
- Main closes database on success
- Main closes database on error
- Main stores items in database
- Main records feed generation

# Canvas Release Notes RSS Aggregator - Technical Specification

## Project Overview

**Name:** Canvas Release Notes RSS Aggregator  
**Purpose:** Aggregate Canvas LMS release notes, API changes, and user feedback into a single daily RSS feed  
**Audience:** Educational technologists at U of T (CTSI and broader community)  
**Deployment:** Docker container on your Docker VM  
**Distribution:** MS Teams via Power Automate RSS connector  

## Architecture

### High-Level Flow
```
┌─────────────────┐
│  Daily Cron Job │ (6:00 AM EST)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│         Data Collection Layer           │
├─────────────────────────────────────────┤
│ • Instructure Community Scraper         │
│ • Reddit API Client (PRAW)              │
│ • Canvas Status Page Monitor            │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│      Processing & Analysis Layer        │
├─────────────────────────────────────────┤
│ • Content Extraction                    │
│ • Duplicate Detection                   │
│ • LLM Summarization (OpenAI/Anthropic)  │
│ • Sentiment Analysis                    │
│ • Topic Classification                  │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│         Output Generation Layer         │
├─────────────────────────────────────────┤
│ • RSS Feed Generation (XML)             │
│ • Historical Archive (JSON)             │
│ • Change Detection                      │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│          Distribution Layer             │
├─────────────────────────────────────────┤
│ • Static RSS file (example.com/feed.xml)  │
│ • Power Automate webhook (optional)     │
└─────────────────────────────────────────┘
```

## Data Sources

### Primary Sources

1. **Instructure Canvas Community**
   - Release Notes: `https://community.instructure.com/en/categories/canvas-release-notes/`
     - Default view shows Release Notes; click "Deploys" tab to access Deploy Notes
     - Scraper automatically navigates both views
     - Detects "Latest Release" and "Latest Deploy" badges
   - Change Log (API): `https://community.instructure.com/en/categories/canvas-lms-changelog`
   - Q&A Forum: `https://community.instructure.com/en/categories/canvas-lms-question-forum?sort=-dateLastComment`
     - Sorted by most recent comment activity
     - Re-included in feed when new comments are added
   - Blog: `https://community.instructure.com/en/categories/canvas_lms_blog?sort=-dateLastComment`
     - Sorted by most recent comment activity
     - Re-included in feed when new comments are added
   - Method: Headless browser scraping (Playwright)
   - Frequency: Daily
   - Data: Titles, dates, content, engagement metrics, post type, comment count, is_latest flag

2. **Canvas Status Page**
   - URL: `https://status.instructure.com/`
   - Method: API or RSS if available, otherwise scrape
   - Purpose: Incident reports, maintenance windows
   - Frequency: Daily (check for updates in last 24h)

3. **Reddit**
   - Subreddits: r/canvas, r/instructionaldesign, r/highereducation
   - Method: Reddit API (PRAW library)
   - Keywords: "canvas lms", "canvas update", "canvas feature", "canvas release"
   - Time window: Last 24 hours
   - Filter: Posts/comments with >5 upvotes or significant discussion

4. **Canvas GitHub (optional)**
   - Repository: `https://github.com/instructure/canvas-lms`
   - Method: GitHub API
   - Purpose: Recent commits to release branches, new issues
   - Frequency: Daily

## Technical Stack

### Core Technologies
- **Language:** Python 3.11+
- **Web Scraping:** Playwright (headless browser automation)
- **Reddit:** PRAW (Python Reddit API Wrapper)
- **LLM Integration:** OpenAI API or Anthropic Claude API
- **RSS Generation:** feedgen library
- **Data Storage:** SQLite (for deduplication and history)
- **Scheduling:** cron (inside container)
- **Container:** Docker with Alpine Linux base

### Python Dependencies
```
playwright>=1.40.0
praw>=7.7.0
feedgen>=1.0.0
openai>=1.0.0    # or anthropic
beautifulsoup4>=4.12.0
requests>=2.31.0
python-dotenv>=1.0.0
schedule>=1.2.0
sqlite3 (built-in)
```

## Component Design

### 1. Scraper Modules

#### `scrapers/instructure_community.py`
```python
@dataclass
class CommunityPost:
    """A post from the Instructure Canvas Community."""
    title: str
    url: str
    content: str
    published_date: datetime
    likes: int = 0
    comments: int = 0
    post_type: str = "discussion"  # 'release_note', 'deploy_note', 'changelog', 'question', 'blog'
    is_latest: bool = False  # True for "Latest Release" or "Latest Deploy" tagged posts

class InstructureScraper:
    """Scrape Canvas Community release notes, deploy notes, changelog, Q&A, and blog posts"""

    def scrape_release_notes(self, hours: int = 24) -> List[ReleaseNote]:
        """Get posts from last N hours from release notes category.

        Automatically navigates between Release Notes (default view) and
        Deploy Notes (accessible via 'Deploys' tab click). Detects and
        captures 'Latest Release' and 'Latest Deploy' badges.
        """
        pass

    def scrape_changelog(self, hours: int = 24) -> List[ChangeLogEntry]:
        """Get API change log entries"""
        pass

    def scrape_question_forum(self, hours: int = 24) -> List[CommunityPost]:
        """Get Q&A posts from the Canvas LMS question forum"""
        pass

    def scrape_blog(self, hours: int = 24) -> List[CommunityPost]:
        """Get blog posts from the Canvas LMS blog"""
        pass

    def scrape_all(self, hours: int = 24) -> List[CommunityPost]:
        """Scrape all community sources and return unified list"""
        pass

    def get_community_reactions(self, post_url: str) -> dict:
        """Extract likes, comments, engagement from a post"""
        pass
```

#### `scrapers/reddit_client.py`
```python
class RedditMonitor:
    """Monitor Canvas-related Reddit discussions"""
    
    def search_subreddits(self, keywords: List[str], time_window: str = "day") -> List[Post]:
        """Search multiple subreddits for Canvas mentions"""
        pass
    
    def get_top_discussions(self, min_score: int = 5) -> List[Post]:
        """Get highly-engaged posts about Canvas"""
        pass
```

#### `scrapers/status_page.py`
```python
class StatusPageMonitor:
    """Monitor Canvas status page for incidents"""
    
    def get_recent_incidents(self, hours: int = 24) -> List[Incident]:
        """Get incidents from last N hours"""
        pass
```

### 2. Processing Module

#### `processor/content_processor.py`
```python
@dataclass
class ContentItem:
    """A processed content item ready for RSS feed."""
    source: str                     # 'community', 'reddit', 'status'
    source_id: str
    title: str
    url: str
    content: str
    content_type: str = ""          # 'release_note', 'deploy_note', 'changelog', 'blog', 'question', 'reddit', 'status'
    summary: str = ""
    sentiment: str = ""             # positive, neutral, negative (skipped for release_note, deploy_note, changelog, blog, question)
    primary_topic: str = ""         # Single topic for feature-centric grouping
    topics: List[str] = None        # Additional/secondary topics
    published_date: Any = None
    engagement_score: int = 0
    comment_count: int = 0          # For tracking discussion activity (blog, question)
    is_latest: bool = False         # True for "Latest Release" or "Latest Deploy" (release/deploy notes only)

class ContentProcessor:
    """Process and analyze collected content"""

    TOPIC_CATEGORIES = [
        "Gradebook", "Assignments", "SpeedGrader", "Quizzes",
        "Discussions", "Pages", "Files", "People", "Groups",
        "Calendar", "Notifications", "Mobile", "API",
        "Performance", "Accessibility"
    ]
    DEFAULT_TOPIC = "General"

    def deduplicate(self, items: List[ContentItem], db: Database) -> List[ContentItem]:
        """Remove duplicates using SQLite cache"""
        pass

    def summarize_with_llm(self, content: str, content_type: str = "") -> str:
        """Generate concise summary using LLM.

        Uses content-type-specific prompts (v1.1.0):
        - blog/question: Discussion-focused summaries covering community opinions,
          staff responses, and direction of conversation
        - release_note/deploy_note: Feature/fix-focused summaries
        - Other types: Standard content summaries
        """
        pass

    def analyze_sentiment(self, content: str) -> str:
        """Determine sentiment: positive/neutral/negative.

        Note: Sentiment analysis is skipped for release_note, deploy_note,
        changelog, blog, question, and status content types (v1.1.0).
        """
        pass

    def classify_topic(self, content: str) -> Tuple[str, List[str]]:
        """Classify into categories, returning (primary_topic, secondary_topics)"""
        pass

    def enrich_with_llm(self, items: List[ContentItem]) -> List[ContentItem]:
        """Add summaries, sentiment, and topics to items"""
        pass
```

### 3. RSS Generator

#### `generator/rss_builder.py`
```python
class RSSBuilder:
    """Generate RSS feed from processed content (feature-centric organization)"""

    # Source badges for title prefixes (fallback for types without content badges)
    SOURCE_BADGES = {
        "community": "[📢 Community]",
        "reddit": "[💬 Reddit]",
        "status": "[🔧 Status]",
    }

    # Content type badges (preferred over source badges)
    CONTENT_TYPE_BADGES = {
        "release_note": "[New]",
        "deploy_note": "[Fix]",
        "changelog": "[API]",
        "blog": "[Blog]",
        "question": "[Q&A]",
        "reddit": "",      # Uses source badge
        "status": "",      # Uses source badge
    }

    # Human-readable names for content types (used in RSS description)
    CONTENT_TYPE_NAMES = {
        "release_note": "Release Notes",
        "deploy_note": "Deploy Notes",
        "changelog": "API Changelog",
        "blog": "Canvas LMS Blog",
        "question": "Canvas LMS Question Forum",
        "reddit": "Reddit Community",
        "status": "Canvas Status",
    }

    # Priority for sorting by topic (lower = higher priority)
    TOPIC_PRIORITY = {
        "Gradebook": 1, "Assignments": 2, "SpeedGrader": 3, "Quizzes": 4,
        "Discussions": 5, "Pages": 6, "Files": 7, "People": 8, "Groups": 9,
        "Calendar": 10, "Notifications": 11, "Mobile": 12, "API": 13,
        "Performance": 14, "Accessibility": 15, "General": 99,
    }

    def create_feed(self, items: List[ContentItem]) -> str:
        """Generate RSS 2.0 XML feed, sorted by topic priority then content type then date"""
        pass

    def add_item(self, item: ContentItem) -> None:
        """Add individual item to feed with feature-centric title format.

        Title format: "{primary_topic} - [Latest] [{content_badge}] {title}"
        Examples:
        - "Gradebook - [Latest] [New] Canvas Release Notes (2026-01-31)"
        - "SpeedGrader - [Fix] Canvas Deploy Notes (2026-01-30)"
        - "API - [API] New Submissions endpoint"
        - "Assignments - [Blog] Improving workflows"
        - "Quizzes - [💬 Reddit] Timer issues discussion"
        """
        pass

    def save_feed(self, output_path: str) -> None:
        """Write RSS XML to file"""
        pass
```

### 4. Database Schema

#### SQLite Schema
```sql
CREATE TABLE content_items (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,           -- 'community', 'reddit', 'status'
    source_id TEXT UNIQUE,          -- Original post/tweet ID
    url TEXT,
    title TEXT,
    content TEXT,
    summary TEXT,
    published_date TIMESTAMP,
    scraped_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sentiment TEXT,
    primary_topic TEXT,             -- Single topic for feature-centric grouping
    topics TEXT,                    -- JSON array of secondary topics
    engagement_score INTEGER,
    comment_count INTEGER DEFAULT 0, -- For tracking discussion activity (v1.1.0)
    content_type TEXT,              -- 'release_note', 'deploy_note', 'changelog', 'blog', 'question', 'reddit', 'status' (v1.1.0)
    included_in_feed BOOLEAN DEFAULT FALSE
);

CREATE TABLE feed_history (
    id INTEGER PRIMARY KEY,
    feed_date DATE UNIQUE,
    item_count INTEGER,
    feed_xml TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Comment Tracking (v1.1.0):** For discussion-focused content types (`blog`, `question`), the aggregator tracks `comment_count` between runs. If an existing item has new comments, it is re-included in the feed with an updated summary focused on the discussion progress.

## RSS Feed Format

### Feature-Centric Organization

The RSS feed is organized by **Canvas feature/topic** rather than by source. This groups related content together regardless of where it came from (community, Reddit, status page).

**Title Format:** `{PrimaryTopic} - [Latest] [{ContentBadge}] {Title}`

The `[Latest]` badge only appears for Release Notes and Deploy Notes that are tagged as the current release/deploy on the Instructure Community site.

**Content Type Badges:**
- `[New]` - Release Notes (new features)
- `[Fix]` - Deploy Notes (bug fixes, patches)
- `[API]` - API Changelog entries
- `[Blog]` - Canvas LMS Blog posts
- `[Q&A]` - Question Forum discussions
- `[💬 Reddit]` - Reddit discussions (uses source badge)
- `[🔧 Status]` - Status page incidents (uses source badge)

Example titles:
- `Gradebook - [Latest] [New] Canvas Release Notes (2026-01-31)`
- `SpeedGrader - [Fix] Canvas Deploy Notes (2026-01-30)`
- `API - [API] New Submissions API endpoint`
- `Assignments - [Blog] Improving assignment workflows`
- `Calendar - [Q&A] How to sync with external calendars?`
- `Assignments - [💬 Reddit] Discussion about late submissions`
- `Performance - [🔧 Status] Maintenance complete`

### Feed Structure
```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Canvas LMS Daily Digest</title>
    <link>https://example.com/canvas-digest</link>
    <description>Daily digest of Canvas LMS updates, community feedback, and discussions</description>
    <language>en-us</language>
    <lastBuildDate>Wed, 29 Jan 2026 06:00:00 EST</lastBuildDate>

    <!-- Items sorted by topic priority (Gradebook first, then Assignments, etc.) -->
    <!-- Within each topic, items sorted by date (most recent first) -->

    <!-- Gradebook items -->
    <item>
      <title>Gradebook - [📢 Community] New weighted grading option</title>
      <description>
        <![CDATA[
          <h3>Summary</h3>
          <p>[AI-generated 2-3 sentence summary]</p>

          <h3>Sentiment</h3>
          <p>positive</p>

          <h3>Source</h3>
          <p>Release Notes</p>

          <h3>Related Topics</h3>
          <p>Tags: #SpeedGrader #Assignments</p>
        ]]>
      </description>
      <link>[Source URL]</link>
      <pubDate>Wed, 29 Jan 2026 00:00:00 EST</pubDate>
      <category>Gradebook</category>           <!-- Primary: Topic -->
      <category>Release Notes</category>       <!-- Secondary: Source -->
      <category>SpeedGrader</category>         <!-- Secondary: Related topics -->
    </item>

    <item>
      <title>Gradebook - [💬 Reddit] Discussion about grade exports</title>
      <description>[Summary with link]</description>
      <link>[Source URL]</link>
      <pubDate>Wed, 29 Jan 2026 00:00:00 EST</pubDate>
      <category>Gradebook</category>
      <category>Community</category>
    </item>

    <!-- Assignments items -->
    <item>
      <title>Assignments - [📢 Community] Q&A: How to set up peer review?</title>
      <description>[Summary from community Q&A forum]</description>
      <link>[Source URL]</link>
      <pubDate>Wed, 29 Jan 2026 00:00:00 EST</pubDate>
      <category>Assignments</category>
      <category>Release Notes</category>
    </item>

    <!-- General items (uncategorized, shown last) -->
    <item>
      <title>General - [🔧 Status] Scheduled maintenance complete</title>
      <description>[Status update summary]</description>
      <link>[Source URL]</link>
      <pubDate>Wed, 29 Jan 2026 00:00:00 EST</pubDate>
      <category>General</category>
      <category>Status</category>
    </item>

  </channel>
</rss>
```

## Release Notes Enhanced Parsing (v1.3.0)

This section documents the enhanced parsing methodology for Canvas Release Notes and Deploy Notes, providing detailed feature-level summaries instead of a single 200-word summary for the entire page.

### Overview

Release Notes pages contain multiple features across categories (Assignments, Canvas Apps, Quizzes, etc.). The enhanced parser extracts each feature individually, generates targeted summaries, and tracks updates when new features are added post-publication.

### Data Model

Each release note page becomes multiple `content_items` entries:

**Parent Entry** (`source_id: "release-2026-02-21"`)

- Contains the "Upcoming Canvas Changes" section
- Serves as the main RSS item linking to the full page
- `content_type: "release_note"` or `"deploy_note"`

**Feature Entries** (`source_id: "release-2026-02-21#document-processing-app"`)

- One per feature, using the page's anchor IDs
- Contains LLM-generated summary + availability summary
- `content_type: "release_note_feature"` or `"deploy_note_feature"`
- Stores `added_date` if the "[Added DATE]" annotation exists

### RSS Output Structure

**Post Titles (badges apply to title only):**
- `[NEW] Canvas Release Notes (2026-02-21)` - first time scraped
- `[UPDATE] Canvas Release Notes (2026-02-21)` - new features detected after initial scrape

**Post Body Structure:**
```
[Link to full release notes page]

━━━ UPCOMING CANVAS CHANGES ━━━
⚠️ 2026-03-21: User-Agent Header Enforcement
• 2026-03-25: Removal of Unauthenticated File Access
• 2026-04-18: Improving Canvas Infrastructure with a CDN
→ Full list: [link to deprecations page]

━━━ NEW FEATURES ━━━

▸ Assignments - [Document Processing App](anchor-link)
[2-3 sentence LLM-generated summary of what the feature does]
Availability: Admin-enabled at account level; affects instructors and students in Assignments, SpeedGrader

▸ Canvas Apps - [Availability and Exceptions](anchor-link) [Added 2026-01-28]
[2-3 sentence summary]
Availability: Account-level setting; affects admins in App configuration

▸ Course - [Accessibility Checker](anchor-link)
[2-3 sentence summary]
Availability: Enabled by default; affects instructors in Rich Content Editor

━━━ OTHER UPDATES ━━━

▸ Canvas Apps - [Updated Apps Page Text](anchor-link)
[2-3 sentence summary]
Availability: Automatic update; affects admins viewing Apps page
```

**Key formatting decisions:**

- Single link to full release notes at top
- Feature names are links to their anchor in the page
- `[Added DATE]` annotations preserved on feature lines for update posts
- Urgency flag (⚠️) for upcoming changes within 30 days
- Same treatment for both "New Features" and "Other Updates" sections

### Update Detection

**Daily 6am run logic:**

1. Fetch the release notes page
2. Parse all feature anchor IDs
3. For each anchor, check `item_exists(source_id)` in database
4. New anchors = new features → create update RSS entry
5. Store new features with current date as `first_seen_date`

**Update RSS entry:**

- Title: `[UPDATE] Canvas Release Notes (2026-02-21)`
- Contains only the newly added features (not the full page)
- Links to same release notes page

### Parsing Logic

**Extracted from each page:**

1. **Page metadata**
   - Title: "Canvas Release Notes (2026-02-21)"
   - URL: full page URL
   - Release date: parsed from title

2. **Upcoming Canvas Changes section**
   - Each dated item (date + description)
   - Days until each date (for urgency flag calculation)
   - Reference link to deprecations page

3. **Feature sections** (under H2 headings like "New Features", "Other Updates")
   - H3 = Category (e.g., "Assignments", "Canvas Apps")
   - Feature name from heading/link text
   - Anchor ID for `source_id` construction
   - `[Added DATE]` annotation if present
   - Full feature content for LLM summarization
   - Configuration table data for availability summary

**Parsing output structure:**
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

### LLM Summarization

**Feature summaries (2-3 sentences):**

- LLM-generated from full feature content
- Focus on: what it does, who it's for, key benefit
- Prompt tailored for Canvas features

**Availability summaries (role-focused, single line):**

- Emphasize who can use/enable the feature
- Derived from configuration table
- Format: `"{Role}-enabled at {location}; affects {affected_roles} in {affected_areas}"`
- Example: `"Admin-enabled at account level; affects instructors and students in Assignments, SpeedGrader"`

### Content Type Badges

Updated badge system for Release Notes and Deploy Notes:

```python
CONTENT_TYPE_BADGES = {
    # Release/Deploy Notes use [NEW] and [UPDATE] on title only
    "release_note": "[NEW]",
    "release_note_update": "[UPDATE]",
    "deploy_note": "[NEW]",
    "deploy_note_update": "[UPDATE]",
    # Other content types unchanged
    "changelog": "[API]",
    "blog": "[Blog]",
    "blog_updated": "[Blog Update]",
    "question": "[Q&A]",
    "question_updated": "[Q&A Update]",
    "reddit": "",
    "status": "",
}
```

Individual features within the post do not have badges - the category and feature name provide sufficient context.

---

## Docker Configuration

### Directory Structure
```
canvas-rss-aggregator/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── config/
│   └── config.yaml
├── src/
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
├── data/
│   └── canvas_digest.db  (SQLite - mounted volume)
├── output/
│   └── feed.xml  (mounted volume)
└── logs/
    └── aggregator.log  (mounted volume)
```

### Dockerfile
```dockerfile
FROM python:3.11-alpine

# Install system dependencies for Playwright
RUN apk add --no-cache \
    chromium \
    chromium-chromedriver \
    nss \
    freetype \
    harfbuzz \
    ca-certificates \
    ttf-freefont

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/usr/bin/chromium

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright (will use system Chromium)
RUN playwright install-deps

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create directories for data persistence
RUN mkdir -p /app/data /app/output /app/logs

# Set up cron for daily 6 AM EST runs
RUN echo "0 6 * * * cd /app && python src/main.py >> /app/logs/cron.log 2>&1" > /etc/crontabs/root

CMD ["crond", "-f", "-l", "2"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  canvas-rss-aggregator:
    build: .
    container_name: canvas-rss-aggregator
    restart: unless-stopped
    environment:
      - TZ=America/Toronto
      - REDDIT_CLIENT_ID=${REDDIT_CLIENT_ID}
      - REDDIT_CLIENT_SECRET=${REDDIT_CLIENT_SECRET}
      - REDDIT_USER_AGENT=${REDDIT_USER_AGENT}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - LLM_PROVIDER=${LLM_PROVIDER:-openai}  # openai or anthropic
    volumes:
      - ./data:/app/data           # SQLite database
      - ./output:/app/output       # RSS feed output
      - ./logs:/app/logs           # Application logs
      - ./config:/app/config:ro    # Configuration (read-only)
    networks:
      - canvas-rss-net

  # Simple HTTP server to serve the RSS feed
  # Cloudflare handles SSL, rate limiting, DDoS protection
  feed-server:
    image: python:3.11-alpine
    container_name: canvas-rss-server
    restart: unless-stopped
    command: python -m http.server 8080 --directory /app/output
    ports:
      - "127.0.0.1:8080:8080"  # Only bind to localhost
    volumes:
      - ./output:/app/output:ro
    networks:
      - canvas-rss-net
    depends_on:
      - canvas-rss-aggregator

networks:
  canvas-rss-net:
    driver: bridge
```

### .env.example
```bash
# Reddit API Credentials (get from https://www.reddit.com/prefs/apps)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=canvas-rss-aggregator:v1.0 (by /u/yourusername)

# LLM Provider (openai or anthropic)
LLM_PROVIDER=openai

# OpenAI API Key (if using OpenAI)
OPENAI_API_KEY=your_openai_key

# Anthropic API Key (if using Claude)
ANTHROPIC_API_KEY=your_anthropic_key

# Optional: Power Automate Webhook
TEAMS_WEBHOOK_URL=https://your-power-automate-webhook-url
```

### config/config.yaml
```yaml
# Canvas RSS Aggregator Configuration

sources:
  instructure_community:
    enabled: true
    urls:
      release_notes: https://community.instructure.com/en/categories/canvas-release-notes/
      changelog: https://community.instructure.com/en/categories/canvas-lms-changelog
      questions: https://community.instructure.com/en/categories/canvas-lms-question-forum
      blog: https://community.instructure.com/en/categories/canvas_lms_blog
    max_pages: 3
    
  reddit:
    enabled: true
    subreddits:
      - canvas
      - instructionaldesign
      - highereducation
      - professors
    keywords:
      - canvas lms
      - canvas update
      - canvas feature
      - canvas release
      - canvas bug
    min_score: 5
    time_window: day
    
  status_page:
    enabled: true
    url: https://status.instructure.com/
    include_maintenance: false
    
  github:
    enabled: false
    repo: instructure/canvas-lms
    branches:
      - master
      - stable

processing:
  llm:
    provider: openai  # openai or anthropic
    model: gpt-4-turbo  # or claude-3-5-sonnet-20241022
    max_tokens: 500
    temperature: 0.3
    
  summarization:
    max_length: 300  # characters
    style: professional  # professional, casual, technical
    
  sentiment_analysis:
    enabled: true
    
  topic_classification:
    enabled: true
    categories:
      - Gradebook
      - Assignments
      - SpeedGrader
      - Quizzes
      - Discussions
      - Pages
      - Files
      - People
      - Groups
      - Calendar
      - Notifications
      - Mobile
      - API
      - Performance
      - Accessibility

rss:
  title: Canvas LMS Daily Digest
  description: Daily digest of Canvas LMS updates, community feedback, and discussions
  link: https://example.com/canvas-digest
  language: en-us
  max_items: 50
  organization: topic  # 'topic' for feature-centric, 'source' for legacy

  # Source badges for title prefixes (feature-centric view)
  source_badges:
    community: "[📢 Community]"
    reddit: "[💬 Reddit]"
    status: "[🔧 Status]"

  # Topic priority for sorting (lower = higher priority)
  topic_priority:
    - Gradebook
    - Assignments
    - SpeedGrader
    - Quizzes
    - Discussions
    - Pages
    - Files
    - People
    - Groups
    - Calendar
    - Notifications
    - Mobile
    - API
    - Performance
    - Accessibility
    - General  # Fallback for uncategorized items

output:
  feed_path: /app/output/feed.xml
  archive_days: 30  # Keep items from last N days
  
teams:
  enabled: false
  webhook_url: ${TEAMS_WEBHOOK_URL}
  notify_on_important: true  # Send immediate notification for critical updates

logging:
  level: INFO
  file: /app/logs/aggregator.log
  max_size_mb: 10
  backup_count: 5
```

## Main Application

### src/main.py
```python
#!/usr/bin/env python3
"""
Canvas RSS Aggregator - Main Entry Point
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.instructure_community import InstructureScraper
from scrapers.reddit_client import RedditMonitor
from scrapers.status_page import StatusPageMonitor
from processor.content_processor import ContentProcessor
from generator.rss_builder import RSSBuilder
from utils.database import Database
from utils.logger import setup_logger

def main():
    """Main aggregation workflow"""
    
    logger = setup_logger()
    logger.info("=" * 50)
    logger.info(f"Canvas RSS Aggregator started at {datetime.now()}")
    logger.info("=" * 50)
    
    # Initialize components
    db = Database()
    processor = ContentProcessor()
    rss_builder = RSSBuilder()
    
    # Collect content from all sources
    all_items = []
    
    try:
        # 1. Scrape Instructure Community (all sources: release notes, changelog, Q&A, blog)
        logger.info("Scraping Instructure Community...")
        with InstructureScraper() as instructure:
            community_posts = instructure.scrape_all()
            all_items.extend(community_posts)
            logger.info(f"  → Found {len(community_posts)} community posts")
        
        # 2. Monitor Reddit
        logger.info("Monitoring Reddit...")
        reddit = RedditMonitor()
        reddit_posts = reddit.search_canvas_discussions()
        all_items.extend(reddit_posts)
        logger.info(f"  → Found {len(reddit_posts)} relevant Reddit posts")
        
        # 3. Check Status Page
        logger.info("Checking Canvas Status Page...")
        status = StatusPageMonitor()
        incidents = status.get_recent_incidents()
        all_items.extend(incidents)
        logger.info(f"  → Found {len(incidents)} status incidents")
        
        # 5. Process all content
        logger.info("Processing content...")
        new_items = processor.deduplicate(all_items, db)
        logger.info(f"  → {len(new_items)} new items after deduplication")
        
        enriched_items = processor.enrich_with_llm(new_items)
        logger.info(f"  → Enriched {len(enriched_items)} items with summaries and sentiment")
        
        # 6. Generate RSS feed
        logger.info("Generating RSS feed...")
        feed_xml = rss_builder.create_feed(enriched_items)
        output_path = Path("/app/output/feed.xml")
        output_path.write_text(feed_xml)
        logger.info(f"  → RSS feed written to {output_path}")
        
        # 7. Store in database
        for item in enriched_items:
            db.insert_item(item)
        db.record_feed_generation(len(enriched_items), feed_xml)
        
        # 8. Optional: Notify Teams
        if os.getenv("TEAMS_WEBHOOK_URL"):
            logger.info("Notifying MS Teams...")
            # Send webhook to Power Automate
            # (Power Automate will detect RSS update automatically)
        
        logger.info("=" * 50)
        logger.info(f"Aggregation complete! {len(enriched_items)} items in today's feed")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"Error during aggregation: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Container Design Philosophy

**Platform Agnostic:**
- Container runs anywhere (dev laptop, VPS, cloud, on-premises)
- No assumptions about reverse proxy, CDN, or hosting provider
- Simple HTTP server on port 8080 serving static RSS file
- All security/edge protection is external infrastructure (not in container)

**What's in the container:**
- Python scraper scripts
- LLM processing logic
- RSS generation
- SQLite database
- Simple HTTP server (Python built-in)
- Cron scheduler

**What's NOT in the container:**
- SSL/TLS termination (handle externally)
- Rate limiting (handle at proxy/CDN layer)
- DDoS protection (handle at edge)
- Authentication (optional, handle at proxy layer)

**Deployment flexibility:**
```
Container → localhost:8080 → [Your choice of front-end]
                              ├─ Nginx
                              ├─ Apache
                              ├─ Cloudflare Tunnel
                              ├─ Caddy
                              ├─ Traefik
                              └─ Direct (dev/testing)
```

---

## Deployment Steps

### 1. Initial Setup
```bash
# On Docker VM
cd /opt/canvas-rss-aggregator

# Clone or copy project files
git clone <your-repo-url> .

# Create .env file from example
cp .env.example .env
nano .env  # Add your API keys

# Create necessary directories
mkdir -p data output logs

# Set permissions
chmod 755 data output logs
```

### 2. Configure Reddit API
1. Go to https://www.reddit.com/prefs/apps
2. Create a new app (type: script)
3. Copy client ID and secret to `.env`

### 3. Configure LLM Provider
Choose OpenAI or Anthropic:
- OpenAI: Get API key from https://platform.openai.com/
- Anthropic: Get API key from https://console.anthropic.com/

### 4. Build and Run
```bash
# Build the container
docker-compose build

# Start the service
docker-compose up -d

# Check logs
docker-compose logs -f canvas-rss-aggregator

# Test immediate run (don't wait for cron)
docker-compose exec canvas-rss-aggregator python src/main.py
```

### 5. Verify Feed Generation

```bash
# Check if feed was generated
ls -lh output/feed.xml

# View feed content
cat output/feed.xml | head -50

# Access via container's HTTP server
curl http://localhost:8080/feed.xml
```

### 6. Expose to Internet (Choose Your Method)

The container serves the RSS feed on `localhost:8080`. How you expose this to the internet is up to you:

**Option A: Reverse Proxy (Nginx, Apache, Caddy, etc.)**
- Point your proxy to `http://localhost:8080`
- Handle SSL/TLS at proxy level
- Add rate limiting, access control as needed

**Option B: Cloudflare Tunnel**
- Zero port forwarding required
- See **Appendix: Cloudflare Deployment Guide** for setup

**Option C: Direct Exposure (Not Recommended)**
- Only for testing/dev environments
- Change port binding: `0.0.0.0:8080:8080`
- Add firewall rules

**Option D: Cloud Platform**
- Deploy to Docker-compatible host (DigitalOcean, Linode, AWS ECS, etc.)
- Use platform's load balancer for SSL/TLS

The feed will be available wherever you point your chosen method.

### 7. Configure Power Automate (Optional)
1. Create new Flow in Power Automate
2. Trigger: "When a feed item is published" (RSS connector)
3. Feed URL: `https://example.com/canvas-digest/feed.xml`
4. Frequency: Every 1 hour (will check for updates)
5. Action: "Post message in a chat or channel" (Teams connector)
6. Select CTSI Teams channel
7. Format message using feed item fields

## Maintenance & Monitoring

### Logs
```bash
# View real-time logs
docker-compose logs -f

# View specific log file
tail -f logs/aggregator.log

# Check cron execution
docker-compose exec canvas-rss-aggregator cat /app/logs/cron.log
```

### Database Queries
```bash
# Access SQLite database
docker-compose exec canvas-rss-aggregator sqlite3 /app/data/canvas_digest.db

# Check recent items
SELECT source, title, published_date FROM content_items ORDER BY scraped_date DESC LIMIT 10;

# Check feed history
SELECT feed_date, item_count FROM feed_history ORDER BY feed_date DESC LIMIT 7;
```

### Manual Trigger
```bash
# Run aggregation manually (for testing)
docker-compose exec canvas-rss-aggregator python src/main.py
```

### Updates
```bash
# Update code
git pull

# Rebuild container
docker-compose build

# Restart service
docker-compose restart
```

## Future Enhancements

### Phase 2 Features
- [ ] Web dashboard to browse feed items
- [ ] Email digest option (alternative to Teams)
- [ ] User preference system (subscribe to specific topics)
- [ ] Webhooks for immediate critical updates
- [ ] Integration with U of T Canvas instance API (if available)
- [ ] Machine learning for better sentiment analysis
- [ ] Trend detection (emerging topics, recurring issues)

### Phase 3 Features
- [ ] Multi-institution support (aggregate from other LMS communities)
- [ ] User-contributed content (ed techs can submit tips)
- [ ] Analytics dashboard (most discussed features, sentiment trends)
- [ ] Integration with ServiceNow for ticket correlation

## Testing Plan

### Unit Tests
- Test each scraper module independently
- Mock API responses for consistency
- Test RSS generation with sample data

### Integration Tests
- End-to-end test with real scraping (dev environment)
- Verify RSS feed validates against RSS 2.0 spec
- Test Power Automate webhook integration

### Performance Tests
- Measure scraping time for all sources
- Monitor memory usage during LLM processing
- Ensure Docker container restarts cleanly

## Security Considerations

### Overview: Defense-in-Depth Strategy

This project uses a **layered security approach** to protect your server:

```
┌─────────────────────────────────────────┐
│    Edge Protection (CDN/WAF/Proxy)      │ ← Layer 1: DDoS, WAF, Rate Limiting
│    (Cloudflare, Nginx, etc.)            │    See Appendix A-B for options
├─────────────────────────────────────────┤
│         Host Firewall (UFW)             │ ← Layer 2: Block direct access
├─────────────────────────────────────────┤
│   Docker (localhost-only binding)       │ ← Layer 3: Container isolation
├─────────────────────────────────────────┤
│   Application (Content Sanitization)    │ ← Layer 4: Input validation
└─────────────────────────────────────────┘
```

**Key Protection Against Server Threats:**

1. **DDoS Protection** → Edge/CDN absorbs attacks before reaching server
2. **Malicious Traffic** → WAF/reverse proxy blocks exploits
3. **Bad Bots** → Rate limiting and bot detection
4. **Resource Exhaustion** → Rate limits prevent abuse
5. **IP Exposure** → Reverse proxy/CDN hides real server IP
6. **Port Scanning** → Localhost-only binding + firewall
7. **Zero-Day Exploits** → Content sanitization prevents injection

**Edge Protection Options:**
- **Cloudflare** (recommended for this project - see Appendix A)
- **Nginx** with ModSecurity WAF (see Appendix B)
- **Caddy** with rate limiting (see Appendix B)
- **Cloud provider WAF** (AWS WAF, GCP Cloud Armor, etc.)
- **Other CDN** (Fastly, Akamai, etc.)

Choose based on your existing infrastructure and preferences.

### 1. Secrets Management

**API Keys & Credentials**
- ✅ **DO**: Store all secrets in `.env` file (Docker secret or environment variables)
- ✅ **DO**: Add `.env` to `.gitignore` immediately
- ✅ **DO**: Use `.env.example` as template (with dummy values)
- ✅ **DO**: Rotate keys periodically (every 90 days recommended)
- ❌ **DON'T**: Hardcode API keys in source code
- ❌ **DON'T**: Commit `.env` to version control
- ❌ **DON'T**: Log API keys or credentials

**Implementation:**
```python
# Good: Load from environment
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

# Bad: Hardcoded
api_key = "sk-proj-abc123..."  # NEVER DO THIS
```

**Docker Secrets (Optional, More Secure):**
```yaml
# docker-compose.yml
services:
  canvas-rss-aggregator:
    secrets:
      - reddit_client_id
      - openai_api_key
    environment:
      - REDDIT_CLIENT_ID_FILE=/run/secrets/reddit_client_id
      - OPENAI_API_KEY_FILE=/run/secrets/openai_api_key

secrets:
  reddit_client_id:
    file: ./secrets/reddit_client_id.txt
  openai_api_key:
    file: ./secrets/openai_api_key.txt
```

### 2. Web Scraping Ethics & Legal

**Respect Terms of Service**
- ✅ **Check robots.txt** for each site before scraping
- ✅ **Use official APIs** when available (Reddit, GitHub)
- ✅ **Rate limit** your requests (1-2 requests/second max)
- ✅ **Add delays** between requests (2-5 seconds)
- ✅ **Set descriptive User-Agent** header
- ❌ **DON'T**: Hammer servers with rapid requests
- ❌ **DON'T**: Scrape if ToS explicitly prohibits it
- ❌ **DON'T**: Use scraped content commercially without permission

**robots.txt Compliance:**
```python
from urllib.robotparser import RobotFileParser

def check_robots_txt(url: str, user_agent: str) -> bool:
    """Check if URL is allowed by robots.txt"""
    rp = RobotFileParser()
    rp.set_url(f"{url}/robots.txt")
    rp.read()
    return rp.can_fetch(user_agent, url)
```

**Rate Limiting:**
```python
import time
from ratelimit import limits, sleep_and_retry

# Max 30 requests per minute
@sleep_and_retry
@limits(calls=30, period=60)
def scrape_page(url: str):
    time.sleep(2)  # Additional 2-second delay
    response = requests.get(url)
    return response
```

**User-Agent Best Practice:**
```python
headers = {
    'User-Agent': 'Canvas-RSS-Aggregator/1.0 (Your Institution; contact@example.com; Educational Use)'
}
```

### 3. RSS Feed Access Control

**Public vs. Private Feed Decision**

**Option A: Public Feed (Simplest)**
- Feed accessible at `https://example.com/canvas-digest/feed.xml`
- Anyone with URL can access
- **Pros**: Easy to set up, works with standard RSS readers
- **Cons**: Potentially exposes aggregated content publicly
- **Mitigation**: Use "security through obscurity" (long random path)

**Option B: Authenticated Feed (More Secure)**
- Require authentication to access feed
- **Pros**: Control who accesses content
- **Cons**: More complex, may break some RSS readers/Power Automate

**Recommended Approach: Security Through Obscurity + Optional Auth**
```nginx
# Nginx configuration
location /canvas-digest/feed-a7f3d8e9b2c1.xml {
    # Optional: IP whitelist (U of T ranges + your VPN)
    allow 128.100.0.0/16;    # U of T IP range (example)
    allow 142.150.0.0/16;    # U of T IP range (example)
    allow 192.168.1.0/24;    # Your local network
    deny all;
    
    # Optional: Basic auth for extra security
    auth_basic "Canvas Digest";
    auth_basic_user_file /etc/nginx/.htpasswd;
    
    alias /opt/canvas-rss-aggregator/output/feed.xml;
    
    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Content-Security-Policy "default-src 'none'" always;
}

# Rate limiting to prevent abuse
limit_req_zone $binary_remote_addr zone=rss_limit:10m rate=10r/m;

location /canvas-digest/ {
    limit_req zone=rss_limit burst=5 nodelay;
    # ... rest of config
}
```

**Generate secure random feed path:**
```bash
# Generate unique feed URL component
openssl rand -hex 16
# Output: a7f3d8e9b2c14f6a8d5e7f0a1b2c3d4e

# Feed URL becomes:
# https://example.com/canvas-digest/feed-a7f3d8e9b2c14f6a.xml
```

### 4. Data Privacy & Content Sanitization

**Personal Information Protection**
- ❌ **DON'T**: Include Reddit usernames in RSS feed (use "A Reddit user" instead)
- ❌ **DON'T**: Include email addresses from community posts
- ❌ **DON'T**: Include personal/sensitive details from discussions
- ✅ **DO**: Anonymize or redact personal info before publishing
- ✅ **DO**: Link to original source instead of copying full content

**Content Sanitization (Prevent XSS):**
```python
import bleach
from html import escape

ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'a', 'h3']
ALLOWED_ATTRIBUTES = {'a': ['href', 'title']}

def sanitize_html(content: str) -> str:
    """Remove potentially malicious HTML/scripts"""
    # First pass: bleach for HTML sanitization
    clean = bleach.clean(
        content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )
    return clean

def sanitize_for_rss(content: str) -> str:
    """Prepare content for RSS CDATA section"""
    # Escape any potential XML special chars
    return escape(content, quote=False)
```

**Privacy in Database:**
```sql
-- Don't store sensitive data
CREATE TABLE content_items (
    -- Good: Store hashed source ID for deduplication
    source_id_hash TEXT UNIQUE,  
    
    -- Bad: Don't store author names/emails
    -- author_name TEXT,  ❌
    -- author_email TEXT,  ❌
    
    -- Good: Store anonymized reference
    source_type TEXT,  -- 'reddit_user', 'community_user', etc.
    
    -- Bad: Don't store full scraped HTML
    -- raw_html TEXT,  ❌
);
```

### 5. Docker Container Security

**Run as Non-Root User**
```dockerfile
# Dockerfile - Add non-root user
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

# Change ownership of app directories
RUN chown -R appuser:appuser /app /app/data /app/output /app/logs

# Switch to non-root user
USER appuser

# Cron needs to run as appuser too
CMD ["crond", "-f", "-l", "2"]
```

**Minimal Base Image**
- Use `python:3.11-alpine` (smaller attack surface)
- Only install necessary system packages
- Multi-stage build to exclude build dependencies from final image

**Container Isolation**
```yaml
# docker-compose.yml
services:
  canvas-rss-aggregator:
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE  # Only if needed
    read_only: true
    tmpfs:
      - /tmp
    volumes:
      - ./data:/app/data
      - ./output:/app/output:ro  # Read-only where possible
```

**Network Isolation**
```yaml
networks:
  canvas-rss-net:
    driver: bridge
    internal: false  # Needs external access for scraping
    ipam:
      config:
        - subnet: 172.28.0.0/16
```

### 6. Dependency Management

**Keep Dependencies Updated**
```bash
# Check for vulnerable packages
pip install safety
safety check

# Update requirements.txt regularly
pip list --outdated
```

**Pin Versions (Reproducible Builds)**
```
# requirements.txt - Pin to specific versions
playwright==1.40.0
praw==7.7.1
feedgen==1.0.0
openai==1.6.1
beautifulsoup4==4.12.2
requests==2.31.0

# Use pip-tools for dependency management
pip-compile requirements.in --output-file requirements.txt
```

**Automated Security Scanning**
```yaml
# .github/workflows/security.yml (if using GitHub)
name: Security Scan
on: [push, pull_request]
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'
```

### 7. Logging & Monitoring Security

**What NOT to Log**
```python
import logging

# Bad: Logging sensitive data
logger.info(f"Using API key: {api_key}")  # ❌ NEVER
logger.debug(f"Reddit credentials: {username}:{password}")  # ❌ NEVER

# Good: Log without sensitive data
logger.info("OpenAI API initialized successfully")  # ✅
logger.debug(f"Scraping URL: {url}")  # ✅
logger.warning(f"Rate limit hit for source: {source_name}")  # ✅
```

**Sanitize Logs**
```python
import re

def sanitize_log_message(message: str) -> str:
    """Remove potential secrets from log messages"""
    # Redact API keys
    message = re.sub(r'(api[_-]?key["\s:=]+)([^\s"]+)', r'\1***REDACTED***', message, flags=re.IGNORECASE)
    # Redact tokens
    message = re.sub(r'(token["\s:=]+)([^\s"]+)', r'\1***REDACTED***', message, flags=re.IGNORECASE)
    # Redact passwords
    message = re.sub(r'(password["\s:=]+)([^\s"]+)', r'\1***REDACTED***', message, flags=re.IGNORECASE)
    return message
```

**Log Rotation & Access Control**
```yaml
# docker-compose.yml
services:
  canvas-rss-aggregator:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

```bash
# Set restrictive permissions on log files
chmod 600 /opt/canvas-rss-aggregator/logs/*.log
chown $USER:$USER /opt/canvas-rss-aggregator/logs/*.log
```

### 8. Firewall & Network Security

**Host-Level Firewall (Example using UFW)**
```bash
# Deny all incoming by default
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (if needed for remote access)
sudo ufw allow 22/tcp

# IMPORTANT: Docker container binds to localhost only
# Port 8080 should NOT be accessible from internet

# If using reverse proxy on same host: no additional rules needed
# If using tunnel (Cloudflare, ngrok, etc.): no inbound rules needed

# Enable firewall
sudo ufw enable
```

**Critical: Localhost-Only Binding**
```yaml
# docker-compose.yml
services:
  feed-server:
    ports:
      - "127.0.0.1:8080:8080"  # ← ONLY localhost, never 0.0.0.0
```

This ensures:
- Container port is only accessible from localhost
- Reverse proxy/tunnel accesses via localhost
- Direct internet access is impossible (even if firewall misconfigured)

**Edge Protection (Choose One)**

The container serves HTTP only. You need edge protection for production:

1. **CDN with WAF** (Cloudflare, Fastly, Akamai)
   - DDoS protection
   - Bot filtering
   - Rate limiting
   - Automatic SSL
   - See **Appendix A** for Cloudflare setup guide

2. **Reverse Proxy** (Nginx, Caddy, Apache)
   - SSL/TLS termination
   - Rate limiting
   - Access control
   - See **Appendix B** for configuration examples

3. **Cloud Load Balancer** (AWS ALB, GCP Load Balancer)
   - Managed SSL
   - Built-in DDoS protection
   - Health checks
   - See **Appendix C** for cloud deployments

**Security Checklist:**
- [ ] Container binds to `127.0.0.1` only
- [ ] Firewall denies inbound to port 8080
- [ ] Edge protection configured (CDN/proxy/load balancer)
- [ ] HTTPS enabled (Let's Encrypt, Cloudflare, or cloud-managed)
- [ ] Rate limiting configured (10-50 requests/minute recommended)
- [ ] Monitoring/alerting set up

### 9. Monitoring & Alerting

**Detect Anomalies**
```python
# Monitor scraping for unusual patterns
def check_anomalies(items: List[ContentItem]):
    """Alert if scraping returns unusual results"""
    
    # Too many items (possible scraper malfunction)
    if len(items) > 100:
        logger.warning(f"Unusually high item count: {len(items)}")
        send_alert("High item count detected")
    
    # No items (possible scraper breakage)
    if len(items) == 0:
        logger.error("No items scraped - scraper may be broken")
        send_alert("Zero items scraped")
    
    # Detect potential PII in content
    if contains_email(items) or contains_phone(items):
        logger.warning("Potential PII detected in scraped content")
        # Redact before publishing
```

**Health Check Endpoint**
```python
# Optional: Add a health check HTTP endpoint
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/health')
def health_check():
    """Health check for monitoring"""
    status = {
        'status': 'healthy',
        'last_run': get_last_successful_run(),
        'feed_items': count_feed_items(),
        'database': check_database_connection()
    }
    return jsonify(status), 200
```

### 10. Incident Response Plan

**If API Keys Are Compromised:**
1. **Immediately rotate** all affected API keys
2. **Update `.env`** with new keys
3. **Restart container**: `docker-compose restart`
4. **Review logs** for unauthorized access
5. **Check bills** for unusual API usage
6. **Consider IP whitelisting** for API access (if provider supports)

**If Scraper Is Blocked:**
1. **Stop scraping immediately** (respect the block)
2. **Review robots.txt** and ToS
3. **Contact site admin** if block is unintentional
4. **Implement longer delays** between requests
5. **Consider using official API** if available

**If Feed Is Abused:**
1. **Monitor access logs** for suspicious patterns
2. **Implement rate limiting** (if not already)
3. **Change feed URL** (regenerate random path)
4. **Add IP whitelist** or authentication
5. **Review who has access** to feed URL

---

## Success Metrics

### Key Performance Indicators
- Daily feed generation success rate (target: 99%+)
- Number of unique items per day (target: 5-15)
- Processing time (target: <5 minutes)
- RSS feed load time (target: <1 second)
- Teams integration reliability (target: 100%)

### User Engagement (via Teams)
- Number of link clicks from Teams
- Feedback from CTSI ed techs
- Reduction in time spent manually checking sources

## Support & Troubleshooting

### Common Issues

**Issue: Playwright fails to launch browser**
- Solution: Ensure chromium is installed in Docker image
- Check: `docker-compose exec canvas-rss-aggregator chromium-browser --version`

**Issue: Reddit API rate limits**
- Solution: Reduce frequency or number of subreddits
- Check: Review Reddit API usage limits

**Issue: LLM API timeouts**
- Solution: Increase timeout, reduce batch size, or add retry logic
- Check: API provider status page

**Issue: Empty RSS feed**
- Solution: Check logs for scraping errors
- Check: Verify database has items: `SELECT COUNT(*) FROM content_items;`

**Issue: Teams not receiving updates**
- Solution: Check Power Automate flow status
- Verify: RSS feed URL is accessible from Teams/Power Automate

---

## Next Steps

1. **Review this spec** - Confirm it matches your vision
2. **Set up API credentials** - Reddit, OpenAI/Anthropic
3. **Create Docker VM directory structure**
4. **Develop scrapers** (start with Instructure Community)
5. **Test RSS generation** with sample data
6. **Deploy to Docker VM**
7. **Configure Power Automate flow**
8. **Monitor first week** of daily runs

---

*This specification is ready to hand off to Claude Code or any developer for implementation.*

---

# APPENDICES

## Appendix A: Cloudflare Deployment Guide

**Note:** This is ONE option for production deployment. The container works with any reverse proxy or CDN.

### Why Cloudflare for This Project?

**Advantages:**
- ✅ DDoS protection at the edge (unlimited, automatic)
- ✅ Bot filtering (reduces load on your server)
- ✅ Rate limiting (prevents abuse before hitting your server)
- ✅ Free SSL/TLS (automatic certificates)
- ✅ IP masking (hides your server's real IP)
- ✅ Zero maintenance (no cert renewal, updates handled automatically)
- ✅ Tunnel option (no port forwarding needed)

**When to use Cloudflare:**
- You want comprehensive DDoS protection
- You're worried about bad bots/scrapers
- You want minimal security management overhead
- You already use Cloudflare for other services

**When NOT to use Cloudflare:**
- You prefer self-hosted solutions
- You already have a robust reverse proxy setup
- You're deploying on a platform with built-in edge protection
- Privacy concerns about routing traffic through third party

### Cloudflare Setup (Step-by-Step)

**Prerequisites:**
- Cloudflare account (free tier is sufficient)
- Domain added to Cloudflare
- Container running and accessible on localhost:8080

#### Option 1: Cloudflare Tunnel (Recommended)

**Benefits:**
- No inbound firewall ports needed (outbound connection only)
- Your server IP never exposed
- Works behind NAT/firewall without port forwarding
- Encrypted tunnel to Cloudflare edge
- Automatic reconnection

**Setup:**
```bash
# 1. Install cloudflared
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# 2. Authenticate
cloudflared tunnel login
# Opens browser to authenticate with Cloudflare account

# 3. Create tunnel
cloudflared tunnel create canvas-rss
# Outputs: Tunnel credentials written to ~/.cloudflared/<ID>.json

# 4. Configure tunnel
nano ~/.cloudflared/config.yml
```

**Tunnel Configuration:**
```yaml
tunnel: <YOUR-TUNNEL-ID>
credentials-file: /home/user/.cloudflared/<YOUR-TUNNEL-ID>.json

ingress:
  # Canvas RSS Feed
  - hostname: example.com
    path: /canvas-digest/*
    service: http://localhost:8080
  
  # Or use subdomain
  - hostname: canvas-digest.example.com
    service: http://localhost:8080
  
  # Catch-all (must be last)
  - service: http_status:404
```

```bash
# 5. Route DNS through tunnel
cloudflared tunnel route dns canvas-rss example.com

# 6. Test tunnel
cloudflared tunnel run canvas-rss

# 7. Install as system service
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared

# 8. Verify
systemctl status cloudflared
curl https://example.com/canvas-digest/feed.xml
```

#### Option 2: Cloudflare Proxy (Traditional)

If you have port forwarding or VPS with public IP:

**DNS Configuration:**
```
Cloudflare Dashboard → DNS → Add Record

Type: A
Name: example.com (or canvas-digest.example.com)
Content: Your server's public IP
Proxy status: Proxied (🟠 orange cloud)  ← Enable this!
TTL: Auto
```

**This enables:**
- DDoS protection
- WAF (Web Application Firewall)
- Bot protection
- Rate limiting
- SSL/TLS

**Your server needs:**
- Port 80/443 accessible
- Reverse proxy (Nginx, Caddy, etc.) handling localhost:8080

### Cloudflare Security Configuration

Once Cloudflare proxy is enabled, configure security features:

#### 1. SSL/TLS Settings
```
SSL/TLS → Overview
Encryption mode: Full (strict)

SSL/TLS → Edge Certificates
Always Use HTTPS: ON
Minimum TLS Version: TLS 1.2
Automatic HTTPS Rewrites: ON
```

#### 2. Bot Protection
```
Security → Settings
Security Level: Medium (or High for stricter)
Challenge Passage: 30 minutes
Browser Integrity Check: ON

Security → Bots
Bot Fight Mode: ON
```

#### 3. Rate Limiting
```
Security → Rate Limiting Rules → Create

Rule Name: RSS Feed Protection
If incoming requests match:
  URI Path equals "/canvas-digest/feed.xml"
With the same value of:
  IP Address
When rate exceeds:
  10 requests per 1 minute
Then:
  Block for 1 hour
  HTTP 429 response
```

#### 4. WAF Rules (Firewall)
```
Security → WAF → Create firewall rule

Rule 1: Block High Threat Score
  Expression: (cf.threat_score gt 50)
  Action: Block

Rule 2: Challenge Medium Threats
  Expression: (cf.threat_score gt 30 and cf.threat_score le 50)
  Action: Managed Challenge

Rule 3: Known Bots (Optional)
  Expression: (cf.client.bot)
  Action: JS Challenge
```

#### 5. Security Headers
```
Rules → Transform Rules → Modify Response Header

Add these headers:
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: no-referrer
  Permissions-Policy: geolocation=(), microphone=(), camera=()
```

#### 6. Page Rules (Caching - Optional)
```
Rules → Page Rules → Create

URL: example.com/canvas-digest/feed.xml
Settings:
  Cache Level: Standard
  Edge Cache TTL: 1 hour
  Browser Cache TTL: 30 minutes
```

This caches the feed at Cloudflare edge, reducing load on your server.

### Cloudflare Monitoring

**Analytics Dashboard:**
```
Analytics → Traffic
  - Monitor request volume
  - Check for spikes (potential attacks)
  
Analytics → Security
  - View blocked requests
  - Monitor threat score distribution
  - Check bot detection stats
```

**Set Up Alerts:**
```
Notifications → Add

Alert Type: Rate Limiting Threshold
Threshold: 100+ requests/min from single IP
Action: Send email

Alert Type: Security Event Spike
Threshold: 50+ high-threat requests/hour
Action: Send email
```

### Firewall Configuration (Host-Level)

When using Cloudflare Tunnel:
```bash
# No inbound ports needed!
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp  # SSH only
sudo ufw enable
```

When using Cloudflare Proxy (traditional):
```bash
# Only allow Cloudflare IP ranges (optional extra security)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp

# Allow Cloudflare IPs only (get from https://www.cloudflare.com/ips/)
for ip in $(curl -s https://www.cloudflare.com/ips-v4); do
  sudo ufw allow from $ip to any port 80,443 proto tcp
done

sudo ufw enable
```

### Cost: Free Tier Sufficient

**Free plan includes:**
- Unlimited DDoS protection
- Universal SSL/TLS
- Bot Fight Mode
- 5 WAF rules
- Rate limiting (10,000 requests/month)
- Basic analytics

**For this project:** Free tier is more than adequate.

---

## Appendix B: Alternative Reverse Proxy Examples

### Option 1: Nginx

**Install:**
```bash
sudo apt install nginx
```

**Configuration:** `/etc/nginx/sites-available/canvas-rss`
```nginx
server {
    listen 80;
    server_name example.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com;

    # SSL Configuration (use certbot)
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Strict-Transport-Security "max-age=31536000" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=rss_limit:10m rate=10r/m;

    location /canvas-digest/ {
        limit_req zone=rss_limit burst=5 nodelay;
        
        proxy_pass http://localhost:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Cache control
        add_header Cache-Control "public, max-age=1800";
    }
}
```

**Enable:**
```bash
sudo ln -s /etc/nginx/sites-available/canvas-rss /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d example.com
```

---

### Option 2: Caddy (Easiest)

**Install:**
```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

**Configuration:** `/etc/caddy/Caddyfile`
```caddy
example.com {
    # Automatic HTTPS with Let's Encrypt
    
    # Rate limiting (requires plugin)
    rate_limit {
        zone canvas_rss {
            key {remote_host}
            events 10
            window 1m
        }
    }
    
    # Security headers
    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "no-referrer"
        -Server
    }
    
    # Reverse proxy to container
    handle /canvas-digest/* {
        reverse_proxy localhost:8080
    }
}
```

**Reload:**
```bash
sudo systemctl reload caddy
```

**Why Caddy:**
- Automatic HTTPS (zero config)
- Simpler syntax than Nginx
- Built-in security best practices

---

### Option 3: Apache

**Install:**
```bash
sudo apt install apache2
sudo a2enmod proxy proxy_http ssl headers rewrite
```

**Configuration:** `/etc/apache2/sites-available/canvas-rss.conf`
```apache
<VirtualHost *:80>
    ServerName example.com
    Redirect permanent / https://example.com/
</VirtualHost>

<VirtualHost *:443>
    ServerName example.com

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/example.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/example.com/privkey.pem

    # Security headers
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-Frame-Options "DENY"
    Header always set Strict-Transport-Security "max-age=31536000"

    # Rate limiting (requires mod_ratelimit)
    <Location /canvas-digest/>
        SetOutputFilter RATE_LIMIT
        SetEnv rate-limit 1024
    </Location>

    # Reverse proxy
    ProxyPreserveHost On
    ProxyPass /canvas-digest/ http://localhost:8080/
    ProxyPassReverse /canvas-digest/ http://localhost:8080/
</VirtualHost>
```

**Enable:**
```bash
sudo a2ensite canvas-rss
sudo apache2ctl configtest
sudo systemctl reload apache2
```

---

## Appendix C: Platform-Specific Deployments

### Deploy to DigitalOcean

**1. Create Droplet**
- Choose Ubuntu 22.04
- Docker pre-installed (from Marketplace)
- $6/month droplet is sufficient

**2. Deploy Container**
```bash
# Clone project
git clone <your-repo> /opt/canvas-rss
cd /opt/canvas-rss

# Configure environment
cp .env.example .env
nano .env  # Add API keys

# Run
docker-compose up -d

# Set up Caddy or Nginx (see Appendix B)
```

---

### Deploy to AWS ECS (Fargate)

**1. Create ECR Repository**
```bash
aws ecr create-repository --repository-name canvas-rss-aggregator
```

**2. Build & Push**
```bash
# Build for AMD64 (ECS default)
docker buildx build --platform linux/amd64 -t canvas-rss .

# Tag and push
docker tag canvas-rss:latest <account>.dkr.ecr.us-east-1.amazonaws.com/canvas-rss-aggregator:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/canvas-rss-aggregator:latest
```

**3. Create ECS Task**
- Use Fargate launch type
- Mount EFS for persistent storage (database, RSS file)
- Use Application Load Balancer for HTTPS

---

### Deploy to Google Cloud Run

**Dockerfile adjustment needed** (Cloud Run uses PORT env var):
```dockerfile
# Add to Dockerfile
ENV PORT=8080
CMD python -m http.server $PORT --directory /app/output
```

**Deploy:**
```bash
gcloud run deploy canvas-rss-aggregator \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi
```

Cloud Run handles HTTPS automatically.

---

## Appendix D: Security Best Practices Summary

Regardless of deployment platform, follow these principles:

### 1. Container Isolation
- ✅ Run as non-root user
- ✅ Bind to localhost only (`127.0.0.1:8080`)
- ✅ Drop unnecessary Linux capabilities
- ✅ Use read-only volumes where possible

### 2. Network Security
- ✅ Firewall: deny all inbound except necessary ports
- ✅ Use reverse proxy (don't expose container directly)
- ✅ Enable HTTPS/TLS (Let's Encrypt is free)

### 3. Application Security
- ✅ Sanitize scraped content (prevent XSS)
- ✅ Redact personal information (privacy)
- ✅ Rate limit scrapers (be a good web citizen)
- ✅ Validate all inputs

### 4. Secrets Management
- ✅ Never commit `.env` to version control
- ✅ Use environment variables or Docker secrets
- ✅ Rotate API keys periodically (90 days)
- ✅ Use minimal permissions for API keys

### 5. Monitoring
- ✅ Log scraping errors
- ✅ Monitor API usage/costs
- ✅ Alert on feed generation failures
- ✅ Track access patterns (detect abuse)

### 6. Maintenance
- ✅ Update dependencies monthly
- ✅ Scan for vulnerabilities (`pip safety check`)
- ✅ Review logs weekly
- ✅ Test scraper against target sites

---

*End of appendices. Main spec is platform-agnostic; use these guides as needed for your environment.*
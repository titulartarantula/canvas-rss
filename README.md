# Canvas LMS Daily Digest

**Version 1.1.0** | [Changelog](CHANGELOG.md)

A daily RSS feed aggregator for Canvas LMS release notes, community discussions, and status updates. Designed for educational technologists who want to stay informed about Canvas updates without manually checking multiple sources.

## Features

- **Multi-source aggregation** - Collects updates from Instructure Community (release notes, deploy notes, changelog, Q&A, blog), Reddit discussions, and Canvas status page
- **Release & Deploy Notes separation** - Automatically navigates between Release Notes and Deploy Notes tabs to capture both types of updates
- **"Latest" badges** - Identifies and tags the current "Latest Release" and "Latest Deploy" notes for quick reference
- **Discussion-focused updates** - Blog and Q&A posts are sorted by recent comment activity, with summaries focused on discussion progress rather than just the original content
- **Comment tracking** - Re-includes previously seen posts when new comments are added to ongoing discussions
- **AI-powered summaries** - Uses Google Gemini to generate concise summaries, sentiment analysis (where appropriate), and topic classification
- **Feature-centric organization** - RSS items grouped by Canvas feature (Gradebook, Assignments, Quizzes, etc.) rather than by source
- **Accurate source labeling** - Each item shows its true content type (Release Notes, Deploy Notes, API Changelog, Canvas LMS Blog, Question Forum, etc.)
- **Privacy-focused** - Automatically redacts personal information and anonymizes Reddit usernames
- **Docker deployment** - Ready-to-deploy containerized setup with cron scheduling
- **Deduplication** - SQLite-backed history prevents duplicate items across runs

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (for containerized deployment)
- API credentials:
  - [Google Gemini API key](https://ai.google.dev/)
  - [Reddit API credentials](https://www.reddit.com/prefs/apps) (optional)

### Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/canvas-rss.git
cd canvas-rss

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run the aggregator
python src/main.py
```

### Docker Deployment

```bash
# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Build and start containers
docker-compose up -d

# View logs
docker-compose logs -f

# Run manually (don't wait for cron)
docker-compose exec canvas-rss-aggregator python src/main.py
```

The RSS feed will be available at `http://localhost:8080/feed.xml`.

## Configuration

### Environment Variables

Create a `.env` file with the following:

```bash
# Required: Google Gemini API
GEMINI_API_KEY=your_gemini_api_key

# Optional: Reddit API (enables Reddit monitoring)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=canvas-rss-aggregator:v1.1.0

# Optional: Customization
GEMINI_MODEL=gemini-2.0-flash       # AI model to use
CRON_SCHEDULE=0 6 * * *              # Daily at 6 AM (default)
TZ=America/Toronto                   # Timezone
FEED_PORT=8080                       # Feed server port
FEED_HOST=0.0.0.0                    # Feed server host
```

### config.yaml

The `config/config.yaml` file controls data sources and processing options:

```yaml
sources:
  instructure_community:
    enabled: true
    max_pages: 3
  reddit:
    enabled: true
    min_score: 5
  status_page:
    enabled: true

processing:
  summarization:
    max_length: 300
  sentiment_analysis:
    enabled: true
  topic_classification:
    enabled: true

rss:
  title: Canvas LMS Daily Digest
  max_items: 50
```

## RSS Feed Format

Items are organized by Canvas feature with content type badges:

```
Gradebook - [Latest] [New] Canvas Release Notes (2026-01-31)
SpeedGrader - [Fix] Canvas Deploy Notes (2026-01-30)
API - [API] New Submissions API endpoint
Assignments - [Blog] Improving assignment workflows
Calendar - [Q&A] How to sync with external calendars?
Performance - [🔧 Status] Maintenance complete
Quizzes - [💬 Reddit] Discussion about quiz timer issues
```

Badge meanings:

- **[Latest]** - Current release or deploy (Release/Deploy Notes only)
- **[New]** - Release Notes (new features)
- **[Fix]** - Deploy Notes (bug fixes, patches)
- **[API]** - API Changelog entries
- **[Blog]** - Canvas LMS Blog posts
- **[Q&A]** - Question Forum discussions

Each item includes:

- AI-generated summary (discussion-focused for blog/Q&A posts)
- Sentiment analysis (for Reddit and status updates)
- Accurate source label (Release Notes, Deploy Notes, Canvas LMS Blog, etc.)
- Related topics
- Link to original source

## Architecture

```
┌─────────────────┐
│  Daily Cron Job │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│         Data Collection Layer           │
│ • Instructure Community (Playwright)    │
│ • Reddit API (PRAW)                     │
│ • Canvas Status Page                    │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│      Processing & Analysis Layer        │
│ • Content Extraction                    │
│ • Duplicate Detection (SQLite)          │
│ • LLM Summarization (Gemini)            │
│ • Sentiment Analysis                    │
│ • Topic Classification                  │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│         Output Generation Layer         │
│ • RSS Feed Generation (feedgen)         │
│ • Historical Archive                    │
└─────────────────────────────────────────┘
```

## Project Structure

```
canvas-rss/
├── src/
│   ├── main.py                    # Application entry point
│   ├── scrapers/
│   │   ├── instructure_community.py  # Playwright web scraper
│   │   ├── reddit_client.py          # PRAW Reddit client
│   │   └── status_page.py            # Status page monitor
│   ├── processor/
│   │   └── content_processor.py      # Gemini AI processing
│   ├── generator/
│   │   └── rss_builder.py            # RSS feed generation
│   └── utils/
│       ├── database.py               # SQLite operations
│       └── logger.py                 # Logging configuration
├── tests/                         # Test suite (270 tests)
├── config/
│   └── config.yaml                # Configuration file
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_rss_builder.py -v
```

## Data Sources

| Source | Method | Content |
|--------|--------|---------|
| [Instructure Community](https://community.instructure.com/) | Playwright | Release notes, changelog, Q&A, blog |
| [Reddit](https://reddit.com/r/canvas) | PRAW API | r/canvas, r/instructionaldesign discussions |
| [Canvas Status](https://status.instructure.com/) | API | Incidents, maintenance updates |

## Deployment Options

The Docker container serves the RSS feed on `localhost:8080`. For production, use a reverse proxy:

- **Cloudflare Tunnel** - Zero port forwarding, automatic SSL
- **Nginx/Caddy** - Traditional reverse proxy with Let's Encrypt
- **Cloud platforms** - AWS ECS, Google Cloud Run, DigitalOcean

See [specs/canvas-rss.md](specs/canvas-rss.md) for detailed deployment guides.

## Troubleshooting

**Empty RSS feed**
- Check logs: `docker-compose logs canvas-rss-aggregator`
- Verify API keys in `.env`
- Run manually: `docker-compose exec canvas-rss-aggregator python src/main.py`

**Playwright fails**
- Ensure Chromium is installed: `playwright install chromium`
- In Docker, the image includes Chromium automatically

**Reddit API errors**
- Verify credentials at https://www.reddit.com/prefs/apps
- Check rate limits in logs

**Gemini API timeouts**
- The aggregator includes exponential backoff retry logic
- Check your API quota at https://ai.google.dev/

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `pytest tests/ -v`
5. Commit: `git commit -m "Add my feature"`
6. Push: `git push origin feature/my-feature`
7. Open a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Built for educational technologists at the University of Toronto
- Uses [Playwright](https://playwright.dev/) for web scraping
- Uses [PRAW](https://praw.readthedocs.io/) for Reddit API
- Uses [feedgen](https://feedgen.kiesow.be/) for RSS generation
- AI summaries powered by [Google Gemini](https://ai.google.dev/)

"""Scraper for Instructure Canvas Community release notes and changelog."""

import logging
import time
import re
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None
    PlaywrightTimeout = Exception

logger = logging.getLogger("canvas_rss")


@dataclass
class CommunityPost:
    """A post from the Instructure Canvas Community."""

    title: str
    url: str
    content: str
    published_date: datetime
    likes: int = 0
    comments: int = 0
    post_type: str = "discussion"  # 'release_note', 'changelog', 'question', 'blog'

    @property
    def source(self) -> str:
        """Return the source type for this post."""
        return "community"

    @property
    def source_id(self) -> str:
        """Generate unique ID from URL and post type."""
        return f"{self.post_type}_{hash(self.url)}"


# Keep legacy classes for backwards compatibility
@dataclass
class ReleaseNote:
    """A release note from the Canvas Community."""

    title: str
    url: str
    content: str
    published_date: datetime
    likes: int = 0
    comments: int = 0

    @property
    def source(self) -> str:
        """Return the source type for this release note."""
        return "community"

    @property
    def source_id(self) -> str:
        """Generate unique ID from URL."""
        return f"community_{hash(self.url)}"


@dataclass
class ChangeLogEntry:
    """A changelog entry from the Canvas API changelog."""

    title: str
    url: str
    content: str
    published_date: datetime

    @property
    def source(self) -> str:
        """Return the source type for this changelog entry."""
        return "community"

    @property
    def source_id(self) -> str:
        """Generate unique ID from URL."""
        return f"changelog_{hash(self.url)}"


class InstructureScraper:
    """Scrape Canvas Community release notes and change logs.

    Uses Playwright sync API for JavaScript-rendered page scraping.
    """

    RELEASE_NOTES_URL = "https://community.instructure.com/en/categories/canvas-release-notes/"
    CHANGELOG_URL = "https://community.instructure.com/en/categories/canvas-lms-changelog"
    QUESTION_FORUM_URL = "https://community.instructure.com/en/categories/canvas-lms-question-forum"
    BLOG_URL = "https://community.instructure.com/en/categories/canvas_lms_blog"
    USER_AGENT = "Canvas-RSS-Aggregator/1.0 (Educational Use)"

    def __init__(self, headless: bool = True, rate_limit_seconds: float = 3.0):
        """Initialize the scraper with Playwright browser.

        Args:
            headless: Run browser in headless mode (default: True).
            rate_limit_seconds: Delay between page navigations (default: 3.0).
        """
        self.headless = headless
        self.rate_limit_seconds = rate_limit_seconds
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        if not PLAYWRIGHT_AVAILABLE:
            logger.warning(
                "Playwright is not installed. Instructure Community scraping will be disabled. "
                "Install with: pip install playwright && playwright install chromium"
            )
            return

        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=headless)
            self.context = self.browser.new_context(
                user_agent=self.USER_AGENT
            )
            self.page = self.context.new_page()
            logger.info("Playwright browser initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Playwright browser: {e}")
            self._cleanup_partial()

    def _cleanup_partial(self):
        """Clean up partially initialized resources."""
        if self.page:
            try:
                self.page.close()
            except Exception:
                pass
            self.page = None
        if self.context:
            try:
                self.context.close()
            except Exception:
                pass
            self.context = None
        if self.browser:
            try:
                self.browser.close()
            except Exception:
                pass
            self.browser = None
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception:
                pass
            self.playwright = None

    def _rate_limit(self):
        """Apply rate limiting between requests."""
        if self.rate_limit_seconds > 0:
            time.sleep(self.rate_limit_seconds)

    def _parse_relative_date(self, date_text: str) -> Optional[datetime]:
        """Parse relative date strings like '2 hours ago', 'Yesterday', etc.

        Args:
            date_text: String containing relative or absolute date.

        Returns:
            datetime object or None if parsing fails.
        """
        if not date_text:
            return None

        date_text = date_text.strip().lower()
        now = datetime.now(timezone.utc)

        try:
            # Handle "X minutes/hours/days ago" patterns
            if "ago" in date_text:
                # Extract number and unit
                match = re.search(r'(\d+)\s*(second|minute|hour|day|week|month)s?\s*ago', date_text)
                if match:
                    value = int(match.group(1))
                    unit = match.group(2)

                    if unit == "second":
                        return now - timedelta(seconds=value)
                    elif unit == "minute":
                        return now - timedelta(minutes=value)
                    elif unit == "hour":
                        return now - timedelta(hours=value)
                    elif unit == "day":
                        return now - timedelta(days=value)
                    elif unit == "week":
                        return now - timedelta(weeks=value)
                    elif unit == "month":
                        return now - timedelta(days=value * 30)

            # Handle "yesterday"
            if "yesterday" in date_text:
                return now - timedelta(days=1)

            # Handle "today"
            if "today" in date_text:
                return now

            # Handle "just now" or "moments ago"
            if "just now" in date_text or "moments ago" in date_text:
                return now

            # Try ISO format
            if "t" in date_text or "-" in date_text:
                # Clean up common variations
                clean_date = date_text.replace("z", "+00:00")
                if clean_date.endswith("+00:00+00:00"):
                    clean_date = clean_date[:-6]
                return datetime.fromisoformat(clean_date)

            # Try common date formats
            for fmt in ["%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d"]:
                try:
                    parsed = datetime.strptime(date_text, fmt)
                    return parsed.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue

        except Exception as e:
            logger.debug(f"Could not parse date '{date_text}': {e}")

        return None

    def _is_within_hours(self, dt: Optional[datetime], hours: int = 24) -> bool:
        """Check if datetime is within the last N hours.

        Args:
            dt: datetime to check.
            hours: Number of hours to look back (default: 24).

        Returns:
            True if datetime is within the time window.
        """
        if not dt:
            return False

        now = datetime.now(timezone.utc)

        # Ensure datetime is timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        cutoff = now - timedelta(hours=hours)
        return dt >= cutoff

    def _dismiss_cookie_consent(self) -> None:
        """Dismiss cookie consent banner if present."""
        if not self.page:
            return

        try:
            # Look for common cookie consent buttons
            accept_selectors = [
                'button:has-text("Accept")',
                'button:has-text("Accept All")',
                'button:has-text("I Accept")',
                '[id*="accept"]',
                '[class*="accept"]',
            ]

            for selector in accept_selectors:
                try:
                    btn = self.page.locator(selector).first
                    if btn.is_visible(timeout=2000):
                        btn.click()
                        self.page.wait_for_timeout(1000)
                        logger.debug("Dismissed cookie consent banner")
                        return
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"No cookie consent to dismiss: {e}")

    def _extract_post_cards(self) -> List[dict]:
        """Extract post card information from the current page.

        Returns:
            List of dicts with title, url, date_text for each post.
        """
        posts = []

        if not self.page:
            return posts

        try:
            # Wait for content to load
            self.page.wait_for_load_state("networkidle", timeout=15000)

            # Dismiss cookie consent if present
            self._dismiss_cookie_consent()

            # Wait a bit more for content to render after dismissing cookie banner
            self.page.wait_for_timeout(2000)

            # Try multiple selector strategies for community posts
            # Instructure Community uses various card/list layouts
            selectors = [
                # H3 links (common in Instructure Community)
                "h3 a[href*='/discussion/']",
                "h3 a[href*='/blog/']",
                "h3 a",
                # Card-based layouts
                "article",
                "[class*='topic-list'] [class*='item']",
                "[class*='post-list'] [class*='item']",
                "[class*='topic'] a[href*='/discussion/']",
                "[class*='card'] a[href*='/discussion/']",
                # List-based layouts
                "li[class*='topic']",
                "tr[class*='topic']",
                # Generic content containers
                ".content-list-item",
                "[data-testid*='topic']",
                "[data-testid*='post']",
                # Link-based extraction as fallback
                "a[href*='/discussion/']",
                "a[href*='/t/']",
            ]

            for selector in selectors:
                try:
                    elements = self.page.query_selector_all(selector)
                    if elements:
                        logger.debug(f"Found {len(elements)} elements with selector: {selector}")
                        break
                except Exception:
                    continue
            else:
                # No elements found with any selector
                logger.warning("Could not find post elements on page")
                return posts

            # Extract data from found elements
            for element in elements[:50]:  # Limit to 50 posts
                try:
                    # Try to find title and URL
                    title = ""
                    url = ""
                    date_text = ""

                    # Check if element is a link
                    tag_name = element.evaluate("el => el.tagName.toLowerCase()")
                    if tag_name == "a":
                        title = element.inner_text().strip()
                        url = element.get_attribute("href") or ""
                    else:
                        # Find link within element - check for /discussion/ first, then /t/
                        link = (
                            element.query_selector("a[href*='/discussion/']") or
                            element.query_selector("a[href*='/t/']") or
                            element.query_selector("a")
                        )
                        if link:
                            title = link.inner_text().strip()
                            url = link.get_attribute("href") or ""

                    # Look for date information
                    date_element = (
                        element.query_selector("time") or
                        element.query_selector("[class*='date']") or
                        element.query_selector("[class*='time']") or
                        element.query_selector("[datetime]")
                    )
                    if date_element:
                        date_text = (
                            date_element.get_attribute("datetime") or
                            date_element.get_attribute("title") or
                            date_element.inner_text()
                        )

                    # Skip if we don't have minimum required data
                    if not title or not url:
                        continue

                    # Make URL absolute
                    if url.startswith("/"):
                        url = f"https://community.instructure.com{url}"

                    # Skip if URL doesn't look like a post
                    if "/t/" not in url and "/topic" not in url.lower() and "/discussion/" not in url and "/blog/" not in url:
                        continue

                    posts.append({
                        "title": title[:500],  # Limit title length
                        "url": url,
                        "date_text": date_text
                    })

                except Exception as e:
                    logger.debug(f"Error extracting post card: {e}")
                    continue

            # Deduplicate by URL
            seen_urls = set()
            unique_posts = []
            for post in posts:
                if post["url"] not in seen_urls:
                    seen_urls.add(post["url"])
                    unique_posts.append(post)

            return unique_posts

        except PlaywrightTimeout:
            logger.warning("Timeout waiting for post cards to load")
            return []
        except Exception as e:
            logger.error(f"Error extracting post cards: {e}")
            return []

    def _get_post_content(self, url: str) -> tuple:
        """Navigate to a post and extract its content.

        Args:
            url: URL of the post to scrape.

        Returns:
            Tuple of (content, likes, comments).
        """
        if not self.page:
            return ("", 0, 0)

        try:
            self._rate_limit()
            self.page.goto(url, timeout=30000)
            self.page.wait_for_load_state("networkidle", timeout=15000)

            content = ""
            likes = 0
            comments = 0

            # Extract main content
            content_selectors = [
                "[class*='post-content']",
                "[class*='topic-content']",
                "[class*='message-body']",
                "article [class*='content']",
                ".post-body",
                ".topic-body",
                "article",
                "main [class*='content']",
            ]

            for selector in content_selectors:
                try:
                    content_el = self.page.query_selector(selector)
                    if content_el:
                        content = content_el.inner_text().strip()
                        if len(content) > 50:  # Found substantial content
                            break
                except Exception:
                    continue

            # Limit content length
            content = content[:5000] if content else ""

            # Extract likes/reactions
            likes_selectors = [
                "[class*='like-count']",
                "[class*='kudos']",
                "[class*='reaction-count']",
                "[aria-label*='like']",
                "[title*='like']",
            ]

            for selector in likes_selectors:
                try:
                    likes_el = self.page.query_selector(selector)
                    if likes_el:
                        likes_text = likes_el.inner_text().strip()
                        likes_match = re.search(r'(\d+)', likes_text)
                        if likes_match:
                            likes = int(likes_match.group(1))
                            break
                except Exception:
                    continue

            # Extract comment count
            comments_selectors = [
                "[class*='comment-count']",
                "[class*='reply-count']",
                "[class*='replies']",
                "[aria-label*='comment']",
                "[aria-label*='repl']",
            ]

            for selector in comments_selectors:
                try:
                    comments_el = self.page.query_selector(selector)
                    if comments_el:
                        comments_text = comments_el.inner_text().strip()
                        comments_match = re.search(r'(\d+)', comments_text)
                        if comments_match:
                            comments = int(comments_match.group(1))
                            break
                except Exception:
                    continue

            return (content, likes, comments)

        except PlaywrightTimeout:
            logger.warning(f"Timeout loading post: {url}")
            return ("", 0, 0)
        except Exception as e:
            logger.error(f"Error getting post content from {url}: {e}")
            return ("", 0, 0)

    def scrape_release_notes(self, hours: int = 24) -> List[ReleaseNote]:
        """Get posts from last N hours from release notes category.

        Args:
            hours: Number of hours to look back (default: 24).

        Returns:
            List of ReleaseNote objects for recent posts.
        """
        if not self.page:
            logger.warning("Browser not available, returning empty release notes list")
            return []

        release_notes = []

        try:
            logger.info(f"Scraping release notes from {self.RELEASE_NOTES_URL}")
            self.page.goto(self.RELEASE_NOTES_URL, timeout=30000)

            # Extract post cards
            posts = self._extract_post_cards()
            logger.info(f"Found {len(posts)} total posts on release notes page")

            # Filter to recent posts and get full content
            for post in posts:
                published_date = self._parse_relative_date(post.get("date_text", ""))

                # If we couldn't parse the date, we'll check it during content fetch
                # For now, include posts with unparseable dates
                if published_date and not self._is_within_hours(published_date, hours):
                    logger.debug(f"Skipping old post: {post['title']}")
                    continue

                # Get full content
                content, likes, comments = self._get_post_content(post["url"])

                # Use current time if we couldn't parse the date
                if not published_date:
                    published_date = datetime.now(timezone.utc)

                release_note = ReleaseNote(
                    title=post["title"],
                    url=post["url"],
                    content=content,
                    published_date=published_date,
                    likes=likes,
                    comments=comments
                )
                release_notes.append(release_note)

            logger.info(f"Scraped {len(release_notes)} release notes from last {hours} hours")
            return release_notes

        except PlaywrightTimeout:
            logger.error(f"Timeout loading release notes page: {self.RELEASE_NOTES_URL}")
            return []
        except Exception as e:
            logger.error(f"Error scraping release notes: {e}")
            return []

    def scrape_changelog(self, hours: int = 24) -> List[ChangeLogEntry]:
        """Get API change log entries from last N hours.

        Args:
            hours: Number of hours to look back (default: 24).

        Returns:
            List of ChangeLogEntry objects for recent entries.
        """
        if not self.page:
            logger.warning("Browser not available, returning empty changelog list")
            return []

        changelog_entries = []

        try:
            logger.info(f"Scraping changelog from {self.CHANGELOG_URL}")
            self.page.goto(self.CHANGELOG_URL, timeout=30000)

            # Extract post cards
            posts = self._extract_post_cards()
            logger.info(f"Found {len(posts)} total posts on changelog page")

            # Filter to recent posts and get full content
            for post in posts:
                published_date = self._parse_relative_date(post.get("date_text", ""))

                # Filter by date if we have one
                if published_date and not self._is_within_hours(published_date, hours):
                    logger.debug(f"Skipping old changelog entry: {post['title']}")
                    continue

                # Get full content
                content, _, _ = self._get_post_content(post["url"])

                # Use current time if we couldn't parse the date
                if not published_date:
                    published_date = datetime.now(timezone.utc)

                entry = ChangeLogEntry(
                    title=post["title"],
                    url=post["url"],
                    content=content,
                    published_date=published_date
                )
                changelog_entries.append(entry)

            logger.info(f"Scraped {len(changelog_entries)} changelog entries from last {hours} hours")
            return changelog_entries

        except PlaywrightTimeout:
            logger.error(f"Timeout loading changelog page: {self.CHANGELOG_URL}")
            return []
        except Exception as e:
            logger.error(f"Error scraping changelog: {e}")
            return []

    def scrape_question_forum(self, hours: int = 24) -> List[CommunityPost]:
        """Get Q&A posts from the Canvas LMS question forum.

        Args:
            hours: Number of hours to look back (default: 24).

        Returns:
            List of CommunityPost objects for recent questions.
        """
        if not self.page:
            logger.warning("Browser not available, returning empty question forum list")
            return []

        posts = []

        try:
            logger.info(f"Scraping question forum from {self.QUESTION_FORUM_URL}")
            self.page.goto(self.QUESTION_FORUM_URL, timeout=30000)

            # Extract post cards
            post_cards = self._extract_post_cards()
            logger.info(f"Found {len(post_cards)} total posts on question forum page")

            # Filter to recent posts and get full content
            for post in post_cards:
                published_date = self._parse_relative_date(post.get("date_text", ""))

                if published_date and not self._is_within_hours(published_date, hours):
                    logger.debug(f"Skipping old question: {post['title']}")
                    continue

                # Get full content
                content, likes, comments = self._get_post_content(post["url"])

                if not published_date:
                    published_date = datetime.now(timezone.utc)

                community_post = CommunityPost(
                    title=post["title"],
                    url=post["url"],
                    content=content,
                    published_date=published_date,
                    likes=likes,
                    comments=comments,
                    post_type="question"
                )
                posts.append(community_post)

            logger.info(f"Scraped {len(posts)} questions from last {hours} hours")
            return posts

        except PlaywrightTimeout:
            logger.error(f"Timeout loading question forum: {self.QUESTION_FORUM_URL}")
            return []
        except Exception as e:
            logger.error(f"Error scraping question forum: {e}")
            return []

    def scrape_blog(self, hours: int = 24) -> List[CommunityPost]:
        """Get blog posts from the Canvas LMS blog.

        Args:
            hours: Number of hours to look back (default: 24).

        Returns:
            List of CommunityPost objects for recent blog posts.
        """
        if not self.page:
            logger.warning("Browser not available, returning empty blog list")
            return []

        posts = []

        try:
            logger.info(f"Scraping blog from {self.BLOG_URL}")
            self.page.goto(self.BLOG_URL, timeout=30000)

            # Extract post cards
            post_cards = self._extract_post_cards()
            logger.info(f"Found {len(post_cards)} total posts on blog page")

            # Filter to recent posts and get full content
            for post in post_cards:
                published_date = self._parse_relative_date(post.get("date_text", ""))

                if published_date and not self._is_within_hours(published_date, hours):
                    logger.debug(f"Skipping old blog post: {post['title']}")
                    continue

                # Get full content
                content, likes, comments = self._get_post_content(post["url"])

                if not published_date:
                    published_date = datetime.now(timezone.utc)

                community_post = CommunityPost(
                    title=post["title"],
                    url=post["url"],
                    content=content,
                    published_date=published_date,
                    likes=likes,
                    comments=comments,
                    post_type="blog"
                )
                posts.append(community_post)

            logger.info(f"Scraped {len(posts)} blog posts from last {hours} hours")
            return posts

        except PlaywrightTimeout:
            logger.error(f"Timeout loading blog: {self.BLOG_URL}")
            return []
        except Exception as e:
            logger.error(f"Error scraping blog: {e}")
            return []

    def scrape_all(self, hours: int = 24) -> List[CommunityPost]:
        """Scrape all community sources and return unified list.

        Scrapes release notes, changelog, Q&A forum, and blog posts.

        Args:
            hours: Number of hours to look back (default: 24).

        Returns:
            List of CommunityPost objects from all sources.
        """
        all_posts = []

        # Scrape release notes and convert to CommunityPost
        release_notes = self.scrape_release_notes(hours)
        for note in release_notes:
            post = CommunityPost(
                title=note.title,
                url=note.url,
                content=note.content,
                published_date=note.published_date,
                likes=note.likes,
                comments=note.comments,
                post_type="release_note"
            )
            all_posts.append(post)

        # Scrape changelog and convert to CommunityPost
        changelog = self.scrape_changelog(hours)
        for entry in changelog:
            post = CommunityPost(
                title=entry.title,
                url=entry.url,
                content=entry.content,
                published_date=entry.published_date,
                post_type="changelog"
            )
            all_posts.append(post)

        # Scrape Q&A forum
        questions = self.scrape_question_forum(hours)
        all_posts.extend(questions)

        # Scrape blog
        blog_posts = self.scrape_blog(hours)
        all_posts.extend(blog_posts)

        logger.info(
            f"Scraped {len(all_posts)} total community posts: "
            f"{len(release_notes)} release notes, {len(changelog)} changelog, "
            f"{len(questions)} questions, {len(blog_posts)} blog posts"
        )
        return all_posts

    def get_community_reactions(self, post_url: str) -> dict:
        """Extract likes, comments, views from a specific post.

        Args:
            post_url: URL of the community post.

        Returns:
            Dictionary with 'likes', 'comments', 'views' counts.
        """
        result = {"likes": 0, "comments": 0, "views": 0}

        if not self.page:
            logger.warning("Browser not available, returning zero reactions")
            return result

        try:
            self._rate_limit()
            self.page.goto(post_url, timeout=30000)
            self.page.wait_for_load_state("networkidle", timeout=15000)

            # Extract likes
            likes_selectors = [
                "[class*='like-count']",
                "[class*='kudos']",
                "[class*='reaction-count']",
                "[aria-label*='like']",
            ]
            for selector in likes_selectors:
                try:
                    el = self.page.query_selector(selector)
                    if el:
                        text = el.inner_text().strip()
                        match = re.search(r'(\d+)', text)
                        if match:
                            result["likes"] = int(match.group(1))
                            break
                except Exception:
                    continue

            # Extract comments
            comments_selectors = [
                "[class*='comment-count']",
                "[class*='reply-count']",
                "[class*='replies']",
            ]
            for selector in comments_selectors:
                try:
                    el = self.page.query_selector(selector)
                    if el:
                        text = el.inner_text().strip()
                        match = re.search(r'(\d+)', text)
                        if match:
                            result["comments"] = int(match.group(1))
                            break
                except Exception:
                    continue

            # Extract views
            views_selectors = [
                "[class*='view-count']",
                "[class*='views']",
                "[aria-label*='view']",
            ]
            for selector in views_selectors:
                try:
                    el = self.page.query_selector(selector)
                    if el:
                        text = el.inner_text().strip()
                        match = re.search(r'(\d+)', text)
                        if match:
                            result["views"] = int(match.group(1))
                            break
                except Exception:
                    continue

            logger.debug(f"Reactions for {post_url}: {result}")
            return result

        except PlaywrightTimeout:
            logger.warning(f"Timeout getting reactions for: {post_url}")
            return result
        except Exception as e:
            logger.error(f"Error getting community reactions from {post_url}: {e}")
            return result

    def close(self):
        """Clean up browser and Playwright resources.

        Safe to call multiple times.
        """
        if self.page:
            try:
                self.page.close()
                logger.debug("Page closed")
            except Exception as e:
                logger.debug(f"Error closing page: {e}")
            self.page = None

        if self.context:
            try:
                self.context.close()
                logger.debug("Context closed")
            except Exception as e:
                logger.debug(f"Error closing context: {e}")
            self.context = None

        if self.browser:
            try:
                self.browser.close()
                logger.debug("Browser closed")
            except Exception as e:
                logger.debug(f"Error closing browser: {e}")
            self.browser = None

        if self.playwright:
            try:
                self.playwright.stop()
                logger.debug("Playwright stopped")
            except Exception as e:
                logger.debug(f"Error stopping Playwright: {e}")
            self.playwright = None

        logger.info("Instructure scraper resources cleaned up")

    def __enter__(self):
        """Support context manager protocol."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up on context manager exit."""
        self.close()
        return False

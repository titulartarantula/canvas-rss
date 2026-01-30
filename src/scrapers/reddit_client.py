"""Reddit client for monitoring Canvas-related discussions."""

import logging
import os
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

try:
    import praw
    from praw.models import Submission
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False
    praw = None
    Submission = None

logger = logging.getLogger("canvas_rss")


@dataclass
class RedditPost:
    """A Reddit post about Canvas."""

    title: str
    url: str
    content: str
    subreddit: str
    author: str  # Will be anonymized before publishing
    score: int
    num_comments: int
    published_date: datetime
    source_id: str = ""  # Unique identifier for deduplication
    permalink: str = ""  # Reddit permalink

    @property
    def source(self) -> str:
        """Return the source type for this post."""
        return "reddit"

    def anonymize(self) -> "RedditPost":
        """Return a copy with anonymized author."""
        return RedditPost(
            title=self.title,
            url=self.url,
            content=self.content,
            subreddit=self.subreddit,
            author="A Reddit user",  # Anonymized
            score=self.score,
            num_comments=self.num_comments,
            published_date=self.published_date,
            source_id=self.source_id,
            permalink=self.permalink
        )


class RedditMonitor:
    """Monitor Canvas-related Reddit discussions.

    Uses PRAW (Python Reddit API Wrapper) to search for Canvas-related
    discussions across multiple subreddits.
    """

    DEFAULT_SUBREDDITS = ["canvas", "instructionaldesign", "highereducation", "professors"]
    DEFAULT_KEYWORDS = ["canvas lms", "canvas update", "canvas feature", "canvas release", "canvas bug"]

    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        user_agent: str = None
    ):
        """Initialize the Reddit client with PRAW.

        Args:
            client_id: Reddit API client ID (or set REDDIT_CLIENT_ID env var).
            client_secret: Reddit API client secret (or set REDDIT_CLIENT_SECRET env var).
            user_agent: User agent string (or set REDDIT_USER_AGENT env var).
        """
        if not PRAW_AVAILABLE:
            logger.warning("PRAW is not installed. Reddit monitoring will be disabled.")
            self.reddit = None
            return

        self.client_id = client_id or os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("REDDIT_CLIENT_SECRET")
        self.user_agent = user_agent or os.getenv(
            "REDDIT_USER_AGENT",
            "canvas-rss-aggregator:v1.0 (Educational Use)"
        )

        if not self.client_id or not self.client_secret:
            logger.warning(
                "Reddit API credentials not provided. "
                "Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET environment variables."
            )
            self.reddit = None
            return

        try:
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent
            )
            # Test connection with read-only mode
            self.reddit.read_only = True
            logger.info("Reddit client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Reddit client: {e}")
            self.reddit = None

    def _submission_to_post(self, submission: "Submission") -> RedditPost:
        """Convert a PRAW Submission object to RedditPost.

        Args:
            submission: PRAW Submission object.

        Returns:
            RedditPost dataclass instance.
        """
        # Get post content (selftext for text posts, URL for link posts)
        if submission.is_self:
            content = submission.selftext or ""
        else:
            content = f"Link: {submission.url}"

        # Convert Unix timestamp to datetime
        published = datetime.fromtimestamp(
            submission.created_utc,
            tz=timezone.utc
        )

        return RedditPost(
            title=submission.title,
            url=f"https://reddit.com{submission.permalink}",
            content=content[:2000],  # Limit content length
            subreddit=submission.subreddit.display_name,
            author=str(submission.author) if submission.author else "[deleted]",
            score=submission.score,
            num_comments=submission.num_comments,
            published_date=published,
            source_id=f"reddit_{submission.id}",
            permalink=submission.permalink
        )

    def search_subreddits(
        self,
        keywords: List[str] = None,
        time_window: str = "day",
        limit: int = 25
    ) -> List[RedditPost]:
        """Search multiple subreddits for Canvas mentions.

        Args:
            keywords: List of keywords to search for (default: DEFAULT_KEYWORDS).
            time_window: Time filter - 'hour', 'day', 'week', 'month', 'year', 'all'.
            limit: Maximum posts per keyword search (default: 25).

        Returns:
            List of RedditPost objects matching the search criteria.
        """
        if not self.reddit:
            logger.warning("Reddit client not initialized, skipping search")
            return []

        keywords = keywords or self.DEFAULT_KEYWORDS
        posts = []
        seen_ids = set()

        for keyword in keywords:
            try:
                # Search all subreddits for the keyword
                search_results = self.reddit.subreddit("all").search(
                    keyword,
                    time_filter=time_window,
                    limit=limit,
                    sort="relevance"
                )

                for submission in search_results:
                    # Skip duplicates
                    if submission.id in seen_ids:
                        continue
                    seen_ids.add(submission.id)

                    # Only include posts from relevant subreddits
                    sub_name = submission.subreddit.display_name.lower()
                    if sub_name in [s.lower() for s in self.DEFAULT_SUBREDDITS]:
                        posts.append(self._submission_to_post(submission))

            except Exception as e:
                logger.error(f"Error searching for keyword '{keyword}': {e}")
                continue

        logger.info(f"Found {len(posts)} posts matching Canvas keywords")
        return posts

    def search_canvas_discussions(self, min_score: int = 5) -> List[RedditPost]:
        """Get highly-engaged posts about Canvas from the last 24 hours.

        This is the main method used by the aggregator. It searches for
        Canvas-related discussions and filters by engagement (score).

        Args:
            min_score: Minimum post score to include (default: 5).

        Returns:
            List of RedditPost objects sorted by score descending.
        """
        if not self.reddit:
            logger.warning("Reddit client not initialized, skipping search")
            return []

        all_posts = []
        seen_ids = set()

        # Method 1: Search in target subreddits
        for subreddit_name in self.DEFAULT_SUBREDDITS:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)

                # Get new posts from the last day
                for submission in subreddit.new(limit=50):
                    if submission.id in seen_ids:
                        continue
                    seen_ids.add(submission.id)

                    # Check if post mentions Canvas
                    title_lower = submission.title.lower()
                    content_lower = (submission.selftext or "").lower()
                    combined = f"{title_lower} {content_lower}"

                    # Must mention Canvas
                    if "canvas" not in combined:
                        continue

                    post = self._submission_to_post(submission)
                    all_posts.append(post)

            except Exception as e:
                logger.error(f"Error fetching from r/{subreddit_name}: {e}")
                continue

        # Method 2: Keyword search across subreddits
        keyword_posts = self.search_subreddits(
            keywords=self.DEFAULT_KEYWORDS,
            time_window="day",
            limit=25
        )

        for post in keyword_posts:
            if post.source_id not in seen_ids:
                seen_ids.add(post.source_id)
                all_posts.append(post)

        # Filter by minimum score
        filtered_posts = [p for p in all_posts if p.score >= min_score]

        # Sort by score (highest first)
        filtered_posts.sort(key=lambda p: p.score, reverse=True)

        logger.info(
            f"Found {len(filtered_posts)} Canvas discussions "
            f"with score >= {min_score} (from {len(all_posts)} total)"
        )

        return filtered_posts

    def get_top_discussions(
        self,
        min_score: int = 5,
        limit: int = 20
    ) -> List[RedditPost]:
        """Get highly-engaged posts about Canvas.

        Args:
            min_score: Minimum post score to include (default: 5).
            limit: Maximum number of posts to return (default: 20).

        Returns:
            List of top RedditPost objects by score.
        """
        posts = self.search_canvas_discussions(min_score=min_score)
        return posts[:limit]

    def get_subreddit_posts(
        self,
        subreddit_name: str,
        sort: str = "new",
        limit: int = 25
    ) -> List[RedditPost]:
        """Get posts from a specific subreddit.

        Args:
            subreddit_name: Name of the subreddit (without r/).
            sort: Sort method - 'new', 'hot', 'top', 'rising'.
            limit: Maximum posts to fetch.

        Returns:
            List of RedditPost objects.
        """
        if not self.reddit:
            logger.warning("Reddit client not initialized")
            return []

        try:
            subreddit = self.reddit.subreddit(subreddit_name)

            if sort == "new":
                submissions = subreddit.new(limit=limit)
            elif sort == "hot":
                submissions = subreddit.hot(limit=limit)
            elif sort == "top":
                submissions = subreddit.top(time_filter="day", limit=limit)
            elif sort == "rising":
                submissions = subreddit.rising(limit=limit)
            else:
                submissions = subreddit.new(limit=limit)

            posts = [self._submission_to_post(s) for s in submissions]
            logger.info(f"Fetched {len(posts)} posts from r/{subreddit_name}")
            return posts

        except Exception as e:
            logger.error(f"Error fetching from r/{subreddit_name}: {e}")
            return []

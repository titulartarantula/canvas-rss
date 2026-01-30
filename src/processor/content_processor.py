"""Content processing, LLM summarization, and sanitization."""

import logging
import os
import re
import time
from typing import List, Any, Tuple, TYPE_CHECKING

import bleach

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None

if TYPE_CHECKING:
    from src.utils.database import Database

from dataclasses import dataclass

logger = logging.getLogger("canvas_rss")


@dataclass
class ContentItem:
    """A processed content item ready for RSS feed."""

    source: str  # 'community', 'reddit', 'status'
    source_id: str
    title: str
    url: str
    content: str
    summary: str = ""
    sentiment: str = ""  # positive, neutral, negative
    primary_topic: str = ""  # Single topic for feature-centric grouping
    topics: List[str] = None  # Additional/secondary topics
    published_date: Any = None
    engagement_score: int = 0

    def __post_init__(self):
        if self.topics is None:
            self.topics = []


class ContentProcessor:
    """Process and analyze collected content."""

    TOPIC_CATEGORIES = [
        "Gradebook", "Assignments", "SpeedGrader", "Quizzes",
        "Discussions", "Pages", "Files", "People", "Groups",
        "Calendar", "Notifications", "Mobile", "API",
        "Performance", "Accessibility"
    ]

    DEFAULT_TOPIC = "General"  # Fallback for unclassified items

    # HTML sanitization settings
    ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'a', 'h3']
    ALLOWED_ATTRIBUTES = {'a': ['href', 'title']}

    # PII redaction patterns
    EMAIL_PATTERN = re.compile(r'\S+@\S+\.\S+')
    REDDIT_USER_PATTERN = re.compile(r'u/\w+')
    PHONE_PATTERN = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')

    def __init__(self, gemini_api_key: str = None):
        """Initialize the content processor.

        Args:
            gemini_api_key: Google Gemini API key (or set GEMINI_API_KEY env var).
        """
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.model = None

        if not GENAI_AVAILABLE:
            logger.warning(
                "google-generativeai is not installed. "
                "LLM features will be disabled."
            )
            return

        if not self.gemini_api_key:
            logger.warning(
                "Gemini API key not provided. "
                "Set GEMINI_API_KEY environment variable or pass gemini_api_key parameter. "
                "LLM features will be disabled."
            )
            return

        try:
            genai.configure(api_key=self.gemini_api_key)
            self.model = genai.GenerativeModel(
                "gemini-2.0-flash-lite",
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=500
                )
            )
            logger.info("Gemini model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            self.model = None

    def deduplicate(self, items: List[ContentItem], db: "Database") -> List[ContentItem]:
        """Remove duplicates using SQLite cache.

        Args:
            items: List of ContentItem objects to filter.
            db: Database instance for checking existing items.

        Returns:
            List of new (non-duplicate) ContentItem objects.
        """
        if not items:
            return []

        new_items = []
        for item in items:
            if item is None:
                continue
            try:
                if not db.item_exists(item.source_id):
                    new_items.append(item)
                else:
                    logger.debug(f"Skipping duplicate item: {item.source_id}")
            except Exception as e:
                logger.error(f"Error checking duplicate for {item.source_id}: {e}")
                # Include item if we can't determine duplicate status
                new_items.append(item)

        logger.info(f"Deduplicated {len(items)} items to {len(new_items)} new items")
        return new_items

    def summarize_with_llm(self, content: str) -> str:
        """Generate concise summary using Gemini.

        Args:
            content: The content to summarize.

        Returns:
            Summary string (max 300 chars), or truncated content if LLM unavailable.
        """
        if not content:
            return ""

        # Fallback if model not available
        if self.model is None:
            truncated = content[:300]
            if len(content) > 300:
                truncated = truncated.rsplit(' ', 1)[0] + "..."
            return truncated

        try:
            prompt = f"Summarize this Canvas LMS update in 2-3 sentences for educational technologists: {content}"
            response = self.model.generate_content(prompt)
            summary = response.text.strip()

            # Limit to 300 characters
            if len(summary) > 300:
                summary = summary[:300].rsplit(' ', 1)[0] + "..."

            return summary

        except Exception as e:
            logger.error(f"LLM summarization failed: {e}")
            return ""

    def analyze_sentiment(self, content: str) -> str:
        """Determine sentiment: positive/neutral/negative.

        Args:
            content: The content to analyze.

        Returns:
            Sentiment string: 'positive', 'neutral', or 'negative'.
        """
        if not content:
            return "neutral"

        # Fallback if model not available
        if self.model is None:
            return "neutral"

        try:
            prompt = (
                "Analyze sentiment of this Canvas LMS content. "
                "Reply with exactly one word: positive, neutral, or negative.\n\n"
                f"Content: {content}"
            )
            response = self.model.generate_content(prompt)
            sentiment = response.text.strip().lower()

            # Validate response
            valid_sentiments = ["positive", "neutral", "negative"]
            if sentiment in valid_sentiments:
                return sentiment
            else:
                logger.warning(f"Invalid sentiment response: {sentiment}, defaulting to neutral")
                return "neutral"

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return "neutral"

    def classify_topic(self, content: str) -> Tuple[str, List[str]]:
        """Classify into categories: Gradebook, Assignments, etc.

        Args:
            content: The content to classify.

        Returns:
            Tuple of (primary_topic, secondary_topics).
            Primary topic is the most relevant, secondary are additional matches.
        """
        if not content:
            return (self.DEFAULT_TOPIC, [])

        # Fallback if model not available
        if self.model is None:
            return (self.DEFAULT_TOPIC, [])

        try:
            categories_str = ", ".join(self.TOPIC_CATEGORIES)
            prompt = (
                f"From this list of Canvas LMS topics: {categories_str}\n\n"
                "Identify the PRIMARY topic (the single most relevant topic) this content is about, "
                "then list any SECONDARY topics (0-2 additional relevant topics).\n"
                "Format your response exactly as: PRIMARY: [topic] | SECONDARY: [topic1, topic2]\n"
                "If no secondary topics apply, use: PRIMARY: [topic] | SECONDARY: none\n\n"
                f"Content: {content}"
            )
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            # Parse the response
            categories_lower = {c.lower(): c for c in self.TOPIC_CATEGORIES}
            primary_topic = self.DEFAULT_TOPIC
            secondary_topics = []

            # Try to parse PRIMARY: ... | SECONDARY: ... format
            if "|" in response_text:
                parts = response_text.split("|")
                if len(parts) >= 2:
                    # Parse primary
                    primary_part = parts[0].replace("PRIMARY:", "").strip()
                    primary_lower = primary_part.lower()
                    if primary_lower in categories_lower:
                        primary_topic = categories_lower[primary_lower]

                    # Parse secondary
                    secondary_part = parts[1].replace("SECONDARY:", "").strip()
                    if secondary_part.lower() != "none":
                        for topic in secondary_part.split(","):
                            topic_clean = topic.strip().lower()
                            if topic_clean in categories_lower:
                                secondary_topics.append(categories_lower[topic_clean])
            else:
                # Fallback: parse as comma-separated list, first is primary
                parsed_topics = [t.strip() for t in response_text.split(",")]
                for i, topic in enumerate(parsed_topics):
                    topic_lower = topic.lower()
                    if topic_lower in categories_lower:
                        if i == 0:
                            primary_topic = categories_lower[topic_lower]
                        else:
                            secondary_topics.append(categories_lower[topic_lower])

            # Limit secondary topics to 2
            return (primary_topic, secondary_topics[:2])

        except Exception as e:
            logger.error(f"Topic classification failed: {e}")
            return (self.DEFAULT_TOPIC, [])

    def sanitize_html(self, content: str) -> str:
        """Remove potentially malicious HTML/scripts.

        Args:
            content: HTML content to sanitize.

        Returns:
            Sanitized HTML with only allowed tags and attributes.
        """
        if not content:
            return ""

        try:
            sanitized = bleach.clean(
                content,
                tags=self.ALLOWED_TAGS,
                attributes=self.ALLOWED_ATTRIBUTES,
                strip=True
            )
            return sanitized
        except Exception as e:
            logger.error(f"HTML sanitization failed: {e}")
            # Return plain text as fallback
            return bleach.clean(content, tags=[], strip=True)

    def redact_pii(self, content: str) -> str:
        """Redact personal information (usernames, emails, phones).

        Args:
            content: Content potentially containing PII.

        Returns:
            Content with PII replaced by placeholders.
        """
        if not content:
            return ""

        try:
            # Replace emails
            redacted = self.EMAIL_PATTERN.sub("[email]", content)

            # Replace Reddit usernames
            redacted = self.REDDIT_USER_PATTERN.sub("[user]", redacted)

            # Replace phone numbers
            redacted = self.PHONE_PATTERN.sub("[phone]", redacted)

            return redacted

        except Exception as e:
            logger.error(f"PII redaction failed: {e}")
            return content

    def enrich_with_llm(self, items: List[ContentItem]) -> List[ContentItem]:
        """Add summaries, sentiment, and topics to items.

        Args:
            items: List of ContentItem objects to enrich.

        Returns:
            List of enriched ContentItem objects.
        """
        if not items:
            return []

        enriched_items = []
        total = len(items)

        for i, item in enumerate(items, 1):
            if item is None:
                continue

            try:
                logger.info(f"Enriching item {i}/{total}: {item.source_id}")

                # Step 1: Sanitize HTML content
                sanitized_content = self.sanitize_html(item.content)

                # Step 2: Redact PII
                redacted_content = self.redact_pii(sanitized_content)

                # Update item content with sanitized/redacted version
                item.content = redacted_content

                # Step 3: Generate summary
                item.summary = self.summarize_with_llm(redacted_content)

                # Rate limiting between API calls
                if self.model is not None:
                    time.sleep(0.5)

                # Step 4: Analyze sentiment
                item.sentiment = self.analyze_sentiment(redacted_content)

                # Rate limiting between API calls
                if self.model is not None:
                    time.sleep(0.5)

                # Step 5: Classify topics (primary and secondary)
                primary, secondary = self.classify_topic(redacted_content)
                item.primary_topic = primary
                item.topics = secondary

                # Rate limiting between API calls (except for last item)
                if self.model is not None and i < total:
                    time.sleep(0.5)

                enriched_items.append(item)
                logger.debug(
                    f"Enriched {item.source_id}: "
                    f"sentiment={item.sentiment}, primary_topic={item.primary_topic}, "
                    f"secondary_topics={item.topics}"
                )

            except Exception as e:
                logger.error(f"Failed to enrich item {item.source_id}: {e}")
                # Include item even if enrichment fails
                enriched_items.append(item)

        logger.info(f"Enriched {len(enriched_items)} items")
        return enriched_items

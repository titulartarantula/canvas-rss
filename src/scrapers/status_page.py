"""Monitor Canvas status page for incidents."""

import logging
import requests
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("canvas_rss")


@dataclass
class Incident:
    """A status page incident."""

    title: str
    url: str
    status: str  # investigating, identified, monitoring, resolved
    impact: str  # none, minor, major, critical
    content: str
    created_at: datetime
    updated_at: datetime
    source_id: str = ""  # Unique identifier for deduplication

    @property
    def source(self) -> str:
        """Return the source type for this incident."""
        return "status"

    # v2.0 source date field aliases for consistency with other scrapers
    @property
    def first_posted(self) -> datetime:
        """Return when the incident was first created."""
        return self.created_at

    @property
    def last_edited(self) -> Optional[datetime]:
        """Return when the incident was last updated."""
        return self.updated_at


class StatusPageMonitor:
    """Monitor Canvas status page for incidents.

    Uses the Statuspage.io API (hosted at status.instructure.com) to fetch
    recent incidents and current system status.
    """

    STATUS_URL = "https://status.instructure.com/"
    API_BASE = "https://status.instructure.com/api/v2"
    INCIDENTS_API = f"{API_BASE}/incidents.json"
    STATUS_API = f"{API_BASE}/status.json"

    def __init__(self, timeout: int = 30):
        """Initialize the status page monitor.

        Args:
            timeout: Request timeout in seconds.
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Canvas-RSS-Aggregator/1.0 (Educational Use)",
            "Accept": "application/json"
        })

    def _parse_datetime(self, dt_string: Optional[str]) -> Optional[datetime]:
        """Parse ISO 8601 datetime string to datetime object.

        Args:
            dt_string: ISO 8601 formatted datetime string.

        Returns:
            datetime object or None if parsing fails.
        """
        if not dt_string:
            return None
        try:
            # Handle ISO 8601 format with timezone
            # Example: "2024-01-15T10:30:00.000Z"
            if dt_string.endswith("Z"):
                dt_string = dt_string[:-1] + "+00:00"
            return datetime.fromisoformat(dt_string)
        except ValueError as e:
            logger.warning(f"Failed to parse datetime '{dt_string}': {e}")
            return None

    def _extract_incident_content(self, incident_data: dict) -> str:
        """Extract human-readable content from incident updates.

        Args:
            incident_data: Raw incident data from API.

        Returns:
            Formatted string with incident updates.
        """
        updates = incident_data.get("incident_updates", [])
        if not updates:
            return incident_data.get("name", "No details available.")

        # Get the most recent update(s)
        content_parts = []
        for update in updates[:3]:  # Limit to 3 most recent updates
            status = update.get("status", "").capitalize()
            body = update.get("body", "")
            if body:
                content_parts.append(f"[{status}] {body}")

        return "\n\n".join(content_parts) if content_parts else incident_data.get("name", "")

    def get_recent_incidents(self, hours: int = 24) -> List[Incident]:
        """Get incidents from last N hours.

        Args:
            hours: Number of hours to look back (default: 24).

        Returns:
            List of Incident objects for incidents updated in the time window.
        """
        try:
            response = self.session.get(self.INCIDENTS_API, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch incidents from status page: {e}")
            return []
        except ValueError as e:
            logger.error(f"Failed to parse incidents JSON response: {e}")
            return []

        incidents = []
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        for incident_data in data.get("incidents", []):
            # Parse timestamps
            updated_at = self._parse_datetime(incident_data.get("updated_at"))
            created_at = self._parse_datetime(incident_data.get("created_at"))

            # Skip if no valid timestamps
            if not updated_at:
                continue

            # Skip incidents not updated within the time window
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            if updated_at < cutoff_time:
                continue

            # Build incident URL
            incident_id = incident_data.get("id", "")
            shortlink = incident_data.get("shortlink", "")
            url = shortlink if shortlink else f"{self.STATUS_URL}incidents/{incident_id}"

            # Create Incident object
            incident = Incident(
                title=incident_data.get("name", "Unknown Incident"),
                url=url,
                status=incident_data.get("status", "unknown"),
                impact=incident_data.get("impact", "none"),
                content=self._extract_incident_content(incident_data),
                created_at=created_at or datetime.now(timezone.utc),
                updated_at=updated_at,
                source_id=f"status_{incident_id}"
            )
            incidents.append(incident)

        logger.info(f"Found {len(incidents)} incidents updated in the last {hours} hours")
        return incidents

    def get_current_status(self) -> dict:
        """Get current overall system status.

        Returns:
            Dictionary with status information including:
            - indicator: 'none', 'minor', 'major', 'critical'
            - description: Human-readable status description
            - components: List of component statuses
        """
        try:
            response = self.session.get(self.STATUS_API, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch current status: {e}")
            return {
                "indicator": "unknown",
                "description": f"Unable to fetch status: {e}",
                "components": []
            }
        except ValueError as e:
            logger.error(f"Failed to parse status JSON response: {e}")
            return {
                "indicator": "unknown",
                "description": f"Invalid response: {e}",
                "components": []
            }

        status_info = data.get("status", {})
        return {
            "indicator": status_info.get("indicator", "unknown"),
            "description": status_info.get("description", "Unknown status"),
            "page_url": data.get("page", {}).get("url", self.STATUS_URL)
        }

    def get_unresolved_incidents(self) -> List[Incident]:
        """Get all currently unresolved incidents.

        Returns:
            List of Incident objects for unresolved incidents.
        """
        try:
            url = f"{self.API_BASE}/incidents/unresolved.json"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch unresolved incidents: {e}")
            return []
        except ValueError as e:
            logger.error(f"Failed to parse unresolved incidents JSON: {e}")
            return []

        incidents = []
        for incident_data in data.get("incidents", []):
            updated_at = self._parse_datetime(incident_data.get("updated_at"))
            created_at = self._parse_datetime(incident_data.get("created_at"))

            incident_id = incident_data.get("id", "")
            shortlink = incident_data.get("shortlink", "")
            url = shortlink if shortlink else f"{self.STATUS_URL}incidents/{incident_id}"

            incident = Incident(
                title=incident_data.get("name", "Unknown Incident"),
                url=url,
                status=incident_data.get("status", "unknown"),
                impact=incident_data.get("impact", "none"),
                content=self._extract_incident_content(incident_data),
                created_at=created_at or datetime.now(timezone.utc),
                updated_at=updated_at or datetime.now(timezone.utc),
                source_id=f"status_{incident_id}"
            )
            incidents.append(incident)

        logger.info(f"Found {len(incidents)} unresolved incidents")
        return incidents

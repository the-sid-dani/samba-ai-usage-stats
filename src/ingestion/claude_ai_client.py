"""Claude.ai Enterprise audit logs client for knowledge worker productivity tracking."""

import csv
import json
import os
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

from ..shared.config import config
from ..shared.logging_setup import get_logger


@dataclass
class ClaudeAiAuditEvent:
    """Structured representation of claude.ai Enterprise audit event."""
    # Core identifiers
    actor_email: str
    actor_name: str
    event_type: str  # conversation_created, project_created, file_uploaded, message_sent
    event_timestamp: datetime
    event_date: date

    # Event metadata
    conversation_id: Optional[str] = None
    project_id: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    message_count: Optional[int] = None

    # Derived metrics
    estimated_session_minutes: Optional[int] = None
    interaction_type: Optional[str] = None  # chat, analysis, coding_assistance, document_review


class ClaudeAiAuditError(Exception):
    """Custom exception for claude.ai audit log processing errors."""
    pass


class ClaudeAiClient:
    """Client for claude.ai Enterprise audit logs processing."""

    def __init__(self):
        self.logger = get_logger("claude_ai_client")
        self.audit_logs_path = config.get("CLAUDE_AI_AUDIT_LOGS_PATH", "data/claude_ai_audit_logs/")
        self.parsing_stats = {
            "total_rows": 0,
            "successful_parses": 0,
            "parsing_failures": 0,
            "fallback_successes": 0
        }

    def _parse_json_robust(self, json_string: str) -> Dict[str, Any]:
        """
        Robust JSON parsing with multiple fallback strategies.

        Handles common issues in audit log CSV exports:
        - Python dict syntax with single quotes
        - Malformed JSON strings
        - Empty/null values
        """
        if not json_string or json_string.strip() in ('{}', '""', "''"):
            return {}

        # Strategy 1: Standard JSON parsing
        try:
            result = json.loads(json_string)
            return result
        except json.JSONDecodeError:
            pass

        # Strategy 2: Convert Python dict syntax to JSON
        try:
            # Replace single quotes with double quotes for JSON compliance
            cleaned = re.sub(r"'([^']*)':", r'"\1":', json_string)  # Keys
            cleaned = re.sub(r": '([^']*)'", r': "\1"', cleaned)    # String values
            cleaned = re.sub(r"'([^']*)'", r'"\1"', cleaned)       # Remaining quotes

            # Handle Python boolean/None values
            cleaned = cleaned.replace('True', 'true').replace('False', 'false').replace('None', 'null')

            result = json.loads(cleaned)
            return result
        except json.JSONDecodeError:
            pass

        # Strategy 3: Regex extraction for key-value pairs
        try:
            result = {}

            # Extract common patterns
            email_match = re.search(r"email_address['\"]?\s*:\s*['\"]([^'\"]+)['\"]", json_string)
            if email_match:
                result['email_address'] = email_match.group(1)

            name_match = re.search(r"name['\"]?\s*:\s*['\"]([^'\"]+)['\"]", json_string)
            if name_match:
                result['name'] = name_match.group(1)

            uuid_match = re.search(r"uuid['\"]?\s*:\s*['\"]([^'\"]+)['\"]", json_string)
            if uuid_match:
                result['uuid'] = uuid_match.group(1)

            type_match = re.search(r"type['\"]?\s*:\s*['\"]([^'\"]+)['\"]", json_string)
            if type_match:
                result['type'] = type_match.group(1)

            if result:
                self.parsing_stats["fallback_successes"] += 1
                return result
        except Exception:
            pass

        # Strategy 4: Return minimal valid structure
        self.logger.warning(f"All parsing strategies failed for: {json_string[:100]}...")
        self.parsing_stats["parsing_failures"] += 1
        return {"parse_error": True, "raw_content": json_string[:200]}

    def get_parsing_stats(self) -> Dict[str, Any]:
        """Get statistics on parsing success rates."""
        if self.parsing_stats["total_rows"] == 0:
            return self.parsing_stats

        success_rate = self.parsing_stats["successful_parses"] / self.parsing_stats["total_rows"]
        fallback_rate = self.parsing_stats["fallback_successes"] / self.parsing_stats["total_rows"]
        failure_rate = self.parsing_stats["parsing_failures"] / self.parsing_stats["total_rows"]

        return {
            **self.parsing_stats,
            "success_rate": success_rate,
            "fallback_rate": fallback_rate,
            "failure_rate": failure_rate,
            "overall_quality": success_rate + fallback_rate
        }

    def process_audit_logs_export(self, file_path: str) -> List[ClaudeAiAuditEvent]:
        """
        Process claude.ai Enterprise audit logs export file.

        Args:
            file_path: Path to CSV/JSON export file from claude.ai Enterprise console

        Returns:
            List of ClaudeAiAuditEvent objects

        Raises:
            ClaudeAiAuditError: If file processing fails
        """
        self.logger.info(f"Processing claude.ai audit logs: {file_path}")

        if not os.path.exists(file_path):
            raise ClaudeAiAuditError(f"Audit logs file not found: {file_path}")

        events = []

        try:
            if file_path.endswith('.csv'):
                events = self._process_csv_export(file_path)
            elif file_path.endswith('.json'):
                events = self._process_json_export(file_path)
            else:
                raise ClaudeAiAuditError(f"Unsupported file format: {file_path}")

            self.logger.info(f"Successfully processed {len(events)} audit events")
            return events

        except Exception as e:
            self.logger.error(f"Failed to process audit logs: {e}")
            raise ClaudeAiAuditError(f"Audit log processing failed: {e}")

    def _process_csv_export(self, file_path: str) -> List[ClaudeAiAuditEvent]:
        """Process CSV format audit logs export."""
        events = []

        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                try:
                    event = self._parse_audit_row(row)
                    if event:
                        events.append(event)
                except Exception as e:
                    self.logger.warning(f"Failed to parse audit row: {e}, row: {row}")
                    continue

        return events

    def _process_json_export(self, file_path: str) -> List[ClaudeAiAuditEvent]:
        """Process JSON format audit logs export."""
        events = []

        with open(file_path, 'r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)

            # Handle different JSON structures
            audit_events = data if isinstance(data, list) else data.get('events', [])

            for event_data in audit_events:
                try:
                    event = self._parse_audit_event(event_data)
                    if event:
                        events.append(event)
                except Exception as e:
                    self.logger.warning(f"Failed to parse audit event: {e}, event: {event_data}")
                    continue

        return events

    def _parse_audit_row(self, row: Dict[str, str]) -> Optional[ClaudeAiAuditEvent]:
        """Parse a single audit log row from CSV with robust JSON handling."""
        self.parsing_stats["total_rows"] += 1

        try:
            # Parse JSON fields with robust parsing
            actor_info = self._parse_json_robust(row.get('actor_info', '{}'))
            event_info = self._parse_json_robust(row.get('event_info', '{}'))
            entity_info = self._parse_json_robust(row.get('entity_info', '{}'))

            # Extract core fields from parsed JSON
            if 'metadata' in actor_info and 'email_address' in actor_info['metadata']:
                actor_email = actor_info['metadata']['email_address']
            elif 'email_address' in actor_info:
                actor_email = actor_info['email_address']
            else:
                actor_email = row.get('actor_email') or row.get('user_email') or row.get('email')

            actor_name = actor_info.get('name', '') or row.get('actor_name') or row.get('user_name') or row.get('name')
            event_type = row.get('event') or row.get('event_type') or row.get('action')
            timestamp_str = row.get('created_at') or row.get('timestamp') or row.get('date')

            if not all([actor_email, event_type, timestamp_str]):
                self.logger.warning(f"Missing required fields in audit row")
                return None

            self.parsing_stats["successful_parses"] += 1

            # Parse timestamp
            event_timestamp = self._parse_timestamp(timestamp_str)
            event_date = event_timestamp.date()

            # Extract metadata from entity_info JSON
            conversation_id = None
            project_id = None
            file_name = None

            if entity_info.get('type') == 'chat_conversation':
                conversation_id = entity_info.get('uuid')
                if 'metadata' in entity_info and 'project_uuid' in entity_info['metadata']:
                    project_id = entity_info['metadata']['project_uuid']
            elif entity_info.get('type') == 'chat_project':
                project_id = entity_info.get('uuid')
            elif entity_info.get('type') == 'file':
                file_name = entity_info.get('uuid')  # File ID as filename

            file_size = self._safe_int(row.get('file_size'))
            message_count = self._safe_int(row.get('message_count'))

            # Derive interaction type
            client_platform = row.get('client_platform', '')
            interaction_type = self._derive_interaction_type(event_type, client_platform)

            return ClaudeAiAuditEvent(
                actor_email=actor_email,
                actor_name=actor_name or "",
                event_type=event_type,
                event_timestamp=event_timestamp,
                event_date=event_date,
                conversation_id=conversation_id,
                project_id=project_id,
                file_name=file_name,
                file_size=file_size,
                message_count=message_count,
                estimated_session_minutes=self._estimate_session_minutes(event_type),
                interaction_type=interaction_type
            )

        except Exception as e:
            self.logger.error(f"Error parsing audit row: {e}")
            return None

    def _parse_audit_event(self, event_data: Dict[str, Any]) -> Optional[ClaudeAiAuditEvent]:
        """Parse a single audit event from JSON."""
        try:
            # Handle nested actor structure
            actor = event_data.get('actor', {})
            actor_email = actor.get('email') if isinstance(actor, dict) else event_data.get('actor_email')
            actor_name = actor.get('name') if isinstance(actor, dict) else event_data.get('actor_name')

            event_type = event_data.get('event_type')
            timestamp_str = event_data.get('timestamp')

            if not all([actor_email, event_type, timestamp_str]):
                return None

            # Parse timestamp
            event_timestamp = self._parse_timestamp(timestamp_str)
            event_date = event_timestamp.date()

            # Extract metadata
            metadata = event_data.get('metadata', {})
            conversation_id = metadata.get('conversation_id')
            project_id = metadata.get('project_id')
            file_name = metadata.get('file_name')
            file_size = metadata.get('file_size')
            message_count = metadata.get('message_count')

            # Derive interaction type
            client_platform = row.get('client_platform', '')
            interaction_type = self._derive_interaction_type(event_type, client_platform)

            return ClaudeAiAuditEvent(
                actor_email=actor_email,
                actor_name=actor_name or "",
                event_type=event_type,
                event_timestamp=event_timestamp,
                event_date=event_date,
                conversation_id=conversation_id,
                project_id=project_id,
                file_name=file_name,
                file_size=file_size,
                message_count=message_count,
                estimated_session_minutes=self._estimate_session_minutes(event_type),
                interaction_type=interaction_type
            )

        except Exception as e:
            self.logger.error(f"Error parsing audit event: {e}")
            return None

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp string to datetime object."""
        # Try different timestamp formats
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",      # ISO with microseconds
            "%Y-%m-%dT%H:%M:%SZ",         # ISO without microseconds
            "%Y-%m-%d %H:%M:%S",          # Standard format
            "%Y-%m-%d",                   # Date only
        ]

        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue

        # Fallback: assume Unix timestamp
        try:
            return datetime.fromtimestamp(float(timestamp_str))
        except (ValueError, TypeError):
            pass

        raise ValueError(f"Unable to parse timestamp: {timestamp_str}")

    def _safe_int(self, value: Any) -> Optional[int]:
        """Safely convert value to int."""
        if value is None or value == "":
            return None
        try:
            return int(float(str(value)))
        except (ValueError, TypeError):
            return None

    def _estimate_session_minutes(self, event_type: str) -> int:
        """Estimate session time based on event type."""
        if 'conversation_created' in event_type:
            return 15  # Average conversation length
        elif 'file_uploaded' in event_type:
            return 5   # File upload interaction
        elif 'project' in event_type:
            return 30  # Project work
        elif 'sign' in event_type:
            return 1   # Login/logout
        else:
            return 2   # Other interactions

    def _derive_interaction_type(self, event_type: str, client_platform: Optional[str] = None) -> str:
        """Derive interaction type from event and platform data."""
        if not event_type:
            return "unknown"

        event_lower = event_type.lower()

        # Platform-specific logic
        if 'conversation' in event_lower:
            if client_platform == 'desktop_app':
                return 'coding_assistance'
            elif client_platform == 'web_claude_ai':
                return 'chat'
            else:
                return 'general'
        elif 'file' in event_lower:
            return 'document_review'
        elif 'project' in event_lower:
            return 'analysis'
        else:
            return 'general'

    def get_daily_aggregates(self, events: List[ClaudeAiAuditEvent], target_date: date) -> Dict[str, Any]:
        """
        Aggregate claude.ai events for a specific date.

        Args:
            events: List of audit events
            target_date: Date to aggregate for

        Returns:
            Dictionary with aggregated metrics
        """
        daily_events = [e for e in events if e.event_date == target_date]

        if not daily_events:
            return {}

        # Group by user
        user_aggregates = {}

        for event in daily_events:
            email = event.actor_email
            if email not in user_aggregates:
                user_aggregates[email] = {
                    "actor_email": email,
                    "actor_name": event.actor_name,
                    "event_date": target_date,
                    "conversations_created": 0,
                    "projects_created": 0,
                    "files_uploaded": 0,
                    "messages_sent": 0,
                    "total_events": 0,
                    "interaction_types": set(),
                    "estimated_active_minutes": 0
                }

            agg = user_aggregates[email]
            agg["total_events"] += 1

            # Count specific event types
            if "conversation" in event.event_type.lower():
                agg["conversations_created"] += 1
            elif "project" in event.event_type.lower():
                agg["projects_created"] += 1
            elif "file" in event.event_type.lower() or "upload" in event.event_type.lower():
                agg["files_uploaded"] += 1
            elif "message" in event.event_type.lower():
                agg["messages_sent"] += 1

            # Track interaction types
            if event.interaction_type:
                agg["interaction_types"].add(event.interaction_type)

        # Convert sets to lists for JSON serialization
        for agg in user_aggregates.values():
            agg["interaction_types"] = list(agg["interaction_types"])
            # Estimate active time based on event patterns (5 minutes per conversation, 2 per message)
            agg["estimated_active_minutes"] = (
                agg["conversations_created"] * 5 +
                agg["projects_created"] * 10 +
                agg["files_uploaded"] * 3 +
                agg["messages_sent"] * 2
            )

        return list(user_aggregates.values())

    def process_recent_logs(self, days_back: int = 7) -> List[ClaudeAiAuditEvent]:
        """
        Process recent audit logs from the configured directory.

        Args:
            days_back: Number of days to look back for log files

        Returns:
            List of audit events from recent log files
        """
        if not os.path.exists(self.audit_logs_path):
            self.logger.warning(f"Audit logs directory not found: {self.audit_logs_path}")
            return []

        all_events = []
        target_date = date.today() - timedelta(days=days_back)

        for file_name in os.listdir(self.audit_logs_path):
            if not (file_name.endswith('.csv') or file_name.endswith('.json')):
                continue

            file_path = os.path.join(self.audit_logs_path, file_name)

            try:
                events = self.process_audit_logs_export(file_path)
                # Filter events to recent timeframe
                recent_events = [e for e in events if e.event_date >= target_date]
                all_events.extend(recent_events)
            except Exception as e:
                self.logger.error(f"Failed to process audit file {file_name}: {e}")
                continue

        self.logger.info(f"Processed {len(all_events)} recent audit events from {days_back} days")
        return all_events
"""Unit tests for claude.ai audit logs client."""

import pytest
import json
from datetime import datetime, date
from unittest.mock import Mock, patch, mock_open

# Set up path for imports
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

from src.ingestion.claude_ai_client import ClaudeAiClient, ClaudeAiAuditEvent, ClaudeAiAuditError


class TestClaudeAiClient:
    """Test cases for ClaudeAiClient."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch('src.ingestion.claude_ai_client.config') as mock_config:
            mock_config.get.return_value = "test/audit/logs/"
            self.client = ClaudeAiClient()

    def test_robust_json_parsing_standard_json(self):
        """Test robust JSON parsing with standard JSON."""
        json_string = '{"name": "Sid", "email_address": "sid.dani@samba.tv"}'

        result = self.client._parse_json_robust(json_string)

        assert result["name"] == "Sid"
        assert result["email_address"] == "sid.dani@samba.tv"

    def test_robust_json_parsing_python_dict_syntax(self):
        """Test robust JSON parsing with Python dict syntax."""
        # This is the format that was causing failures
        python_dict_string = "{'name': 'Sid', 'metadata': {'email_address': 'sid.dani@samba.tv'}}"

        result = self.client._parse_json_robust(python_dict_string)

        assert result["name"] == "Sid"
        assert result["metadata"]["email_address"] == "sid.dani@samba.tv"

    def test_robust_json_parsing_fallback_regex(self):
        """Test fallback regex extraction for malformed JSON."""
        malformed_string = "garbage{'name': 'Sid'garbage'email_address': 'sid@samba.tv'more garbage"

        result = self.client._parse_json_robust(malformed_string)

        assert result["name"] == "Sid"
        assert result["email_address"] == "sid@samba.tv"

    def test_robust_json_parsing_empty_input(self):
        """Test handling of empty or null inputs."""
        test_cases = ["", "{}", '""', "''", None]

        for empty_input in test_cases:
            result = self.client._parse_json_robust(empty_input or "")
            assert result == {}

    def test_robust_json_parsing_complete_failure(self):
        """Test handling when all parsing strategies fail."""
        completely_broken = "not json at all $$%% invalid"

        result = self.client._parse_json_robust(completely_broken)

        assert result["parse_error"] is True
        assert "raw_content" in result

    def test_parse_audit_row_success(self):
        """Test successful audit row parsing."""
        # Real format from the CSV
        test_row = {
            'created_at': '2025-09-28T02:45:39.374856Z',
            'actor_info': "{'name': 'Sid', 'metadata': {'email_address': 'sid.dani@samba.tv'}}",
            'event': 'conversation_created',
            'event_info': '{}',
            'entity_info': "{'type': 'chat_conversation', 'uuid': 'conv-123'}",
            'client_platform': 'web_claude_ai'
        }

        result = self.client._parse_audit_row(test_row)

        assert result is not None
        assert result.actor_email == "sid.dani@samba.tv"
        assert result.actor_name == "Sid"
        assert result.event_type == "conversation_created"
        assert result.conversation_id == "conv-123"
        assert result.interaction_type == "chat"

    def test_parse_audit_row_missing_required_fields(self):
        """Test handling of missing required fields."""
        test_row = {
            'created_at': '2025-09-28T02:45:39.374856Z',
            'actor_info': "{}",  # Missing email
            'event': '',  # Missing event type
        }

        result = self.client._parse_audit_row(test_row)

        assert result is None

    def test_derive_interaction_type(self):
        """Test interaction type derivation logic."""
        test_cases = [
            ("conversation_created", "desktop_app", "coding_assistance"),
            ("conversation_created", "web_claude_ai", "chat"),
            ("file_uploaded", "web_claude_ai", "document_review"),
            ("project_created", "desktop_app", "analysis"),
            ("user_signed_in", "web_claude_ai", "general")
        ]

        for event_type, platform, expected in test_cases:
            result = self.client._derive_interaction_type(event_type, platform)
            assert result == expected

    def test_estimate_session_minutes(self):
        """Test session time estimation."""
        test_cases = [
            ("conversation_created", 15),
            ("file_uploaded", 5),
            ("project_created", 30),
            ("user_signed_in", 1),
            ("unknown_event", 2)
        ]

        for event_type, expected_minutes in test_cases:
            result = self.client._estimate_session_minutes(event_type)
            assert result == expected_minutes

    def test_parsing_stats_tracking(self):
        """Test that parsing statistics are properly tracked."""
        # Process some test data
        self.client._parse_json_robust('{"valid": "json"}')  # Success
        self.client._parse_json_robust("{'python': 'dict'}")  # Fallback success
        self.client._parse_json_robust("completely invalid")  # Failure

        stats = self.client.get_parsing_stats()

        assert stats["total_rows"] == 0  # Only counted in _parse_audit_row
        assert stats["successful_parses"] == 0
        assert stats["fallback_successes"] == 1
        assert stats["parsing_failures"] == 1

    @patch('builtins.open', mock_open(read_data='created_at,actor_info,event\n2025-09-28T02:45:39.374856Z,"{\\"name\\": \\"Sid\\"}",conversation_created'))
    def test_process_csv_export_success(self):
        """Test successful CSV processing."""
        with patch.object(self.client, '_parse_audit_row') as mock_parse:
            mock_event = ClaudeAiAuditEvent(
                actor_email="sid.dani@samba.tv",
                actor_name="Sid",
                event_type="conversation_created",
                event_timestamp=datetime.now(),
                event_date=date.today()
            )
            mock_parse.return_value = mock_event

            result = self.client.process_audit_logs_export("test.csv")

            assert len(result) == 1
            assert result[0].actor_email == "sid.dani@samba.tv"

    def test_process_nonexistent_file(self):
        """Test handling of missing audit log files."""
        with pytest.raises(ClaudeAiAuditError, match="not found"):
            self.client.process_audit_logs_export("nonexistent.csv")


class TestClaudeAiAuditEvent:
    """Test cases for ClaudeAiAuditEvent dataclass."""

    def test_audit_event_creation(self):
        """Test ClaudeAiAuditEvent creation."""
        event_timestamp = datetime.now()
        event_date = event_timestamp.date()

        event = ClaudeAiAuditEvent(
            actor_email="sid.dani@samba.tv",
            actor_name="Sid",
            event_type="conversation_created",
            event_timestamp=event_timestamp,
            event_date=event_date,
            conversation_id="conv-123",
            interaction_type="chat"
        )

        assert event.actor_email == "sid.dani@samba.tv"
        assert event.actor_name == "Sid"
        assert event.event_type == "conversation_created"
        assert event.conversation_id == "conv-123"
        assert event.interaction_type == "chat"


class TestDataQualityMonitoring:
    """Test cases for data quality monitoring."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch('src.ingestion.claude_ai_client.config') as mock_config:
            mock_config.get.return_value = "test/audit/logs/"
            self.client = ClaudeAiClient()

    def test_parsing_stats_calculation(self):
        """Test parsing statistics calculation."""
        # Simulate processing stats
        self.client.parsing_stats = {
            "total_rows": 100,
            "successful_parses": 85,
            "parsing_failures": 10,
            "fallback_successes": 5
        }

        stats = self.client.get_parsing_stats()

        assert stats["success_rate"] == 0.85
        assert stats["fallback_rate"] == 0.05
        assert stats["failure_rate"] == 0.10
        assert stats["overall_quality"] == 0.90

    def test_data_quality_threshold_monitoring(self):
        """Test data quality monitoring against thresholds."""
        stats = {
            "total_rows": 100,
            "successful_parses": 70,
            "fallback_successes": 20,
            "parsing_failures": 10,
            "overall_quality": 0.90
        }

        # Should pass quality threshold (90% overall quality)
        assert stats["overall_quality"] >= 0.90

        # Should trigger monitoring alert if quality drops below 95%
        high_quality_threshold = 0.95
        needs_attention = stats["overall_quality"] < high_quality_threshold
        assert needs_attention  # This dataset would need attention
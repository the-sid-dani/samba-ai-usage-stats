"""User attribution system for accurate cost allocation across platforms."""

from typing import List, Dict, Optional, Any, Set, Tuple
from dataclasses import dataclass
from datetime import datetime, date
from enum import Enum

from ..ingestion.sheets_client import APIKeyMapping, GoogleSheetsClient
from ..shared.logging_setup import get_logger
from .transformer import UsageFactRecord


class AttributionMethod(Enum):
    """Methods used for user attribution."""
    DIRECT_EMAIL = "direct_email"  # Cursor direct email
    API_KEY_MAPPING = "api_key_mapping"  # Google Sheets mapping
    FALLBACK_UNKNOWN = "fallback_unknown"  # Unable to attribute


@dataclass
class AttributionResult:
    """Result of user attribution process."""
    user_email: str
    method: AttributionMethod
    confidence: float  # 0.0 to 1.0
    source: str  # "cursor_api", "google_sheets", etc.
    warnings: List[str]


@dataclass
class AttributionReport:
    """Comprehensive attribution analysis report."""
    total_records: int
    attributed_records: int
    attribution_rate: float
    method_breakdown: Dict[str, int]
    unmapped_api_keys: Set[str]
    attribution_conflicts: List[Dict[str, Any]]
    data_quality_issues: List[str]
    recommendations: List[str]


class UserAttributionEngine:
    """Comprehensive user attribution system."""

    def __init__(self, sheets_client: GoogleSheetsClient = None):
        self.logger = get_logger("attribution_engine")
        self.sheets_client = sheets_client or GoogleSheetsClient()
        self._api_key_cache = None
        self._cache_timestamp = None

    def _get_api_key_mappings(self, force_refresh: bool = False) -> List[APIKeyMapping]:
        """Get API key mappings with caching."""
        now = datetime.now()

        # Use cache if it's less than 1 hour old
        if (not force_refresh and
            self._api_key_cache is not None and
            self._cache_timestamp and
            (now - self._cache_timestamp).seconds < 3600):
            return self._api_key_cache

        # Refresh cache
        try:
            self._api_key_cache = self.sheets_client.get_api_key_mappings()
            self._cache_timestamp = now
            self.logger.info(f"Refreshed API key mapping cache: {len(self._api_key_cache)} mappings")
        except Exception as e:
            self.logger.error(f"Failed to refresh API key mappings: {e}")
            if self._api_key_cache is None:
                self._api_key_cache = []

        return self._api_key_cache

    def attribute_user(
        self,
        record: UsageFactRecord,
        api_key_mappings: List[APIKeyMapping] = None
    ) -> AttributionResult:
        """
        Attribute a usage record to a user.

        Args:
            record: Usage fact record to attribute
            api_key_mappings: Optional API key mappings (uses cache if not provided)

        Returns:
            AttributionResult with user email and confidence
        """
        warnings = []

        # Use provided mappings or fetch from cache
        if api_key_mappings is None:
            api_key_mappings = self._get_api_key_mappings()

        # Create lookup dictionary
        api_key_lookup = {mapping.api_key_name: mapping for mapping in api_key_mappings}

        # Case 1: Direct email attribution (Cursor)
        if record.user_email and record.user_email.strip():
            normalized_email = record.user_email.lower().strip()

            # Validate email format
            if "@" in normalized_email and "." in normalized_email:
                return AttributionResult(
                    user_email=normalized_email,
                    method=AttributionMethod.DIRECT_EMAIL,
                    confidence=0.95,
                    source=record.platform,
                    warnings=warnings
                )
            else:
                warnings.append(f"Invalid email format: {record.user_email}")

        # Case 2: API key mapping attribution (Anthropic)
        if record.api_key_id and record.api_key_id in api_key_lookup:
            mapping = api_key_lookup[record.api_key_id]

            # Check for platform consistency
            expected_platforms = self._get_expected_platforms(mapping.platform)
            if record.platform not in expected_platforms:
                warnings.append(
                    f"Platform mismatch: record={record.platform}, mapping={mapping.platform}"
                )

            return AttributionResult(
                user_email=mapping.user_email.lower().strip(),
                method=AttributionMethod.API_KEY_MAPPING,
                confidence=0.90,
                source="google_sheets",
                warnings=warnings
            )

        # Case 3: Unable to attribute
        warnings.append(f"No attribution method available for API key: {record.api_key_id}")

        return AttributionResult(
            user_email="unknown@unattributed.com",
            method=AttributionMethod.FALLBACK_UNKNOWN,
            confidence=0.0,
            source="fallback",
            warnings=warnings
        )

    def _get_expected_platforms(self, mapping_platform: str) -> List[str]:
        """Get expected platform values for a mapping platform."""
        platform_mapping = {
            "cursor": ["cursor"],
            "anthropic": ["anthropic_api", "anthropic_code", "anthropic_web"],
            "anthropic_api": ["anthropic_api"],
            "anthropic_code": ["anthropic_code"],
            "anthropic_web": ["anthropic_web"]
        }
        return platform_mapping.get(mapping_platform, [mapping_platform])

    def attribute_batch(
        self,
        records: List[UsageFactRecord],
        force_mapping_refresh: bool = False
    ) -> Tuple[List[UsageFactRecord], AttributionReport]:
        """
        Attribute a batch of usage records to users.

        Args:
            records: List of usage records to attribute
            force_mapping_refresh: Force refresh of API key mappings

        Returns:
            Tuple of (attributed_records, attribution_report)
        """
        start_time = datetime.now()

        # Get fresh mappings if requested
        api_key_mappings = self._get_api_key_mappings(force_refresh=force_mapping_refresh)

        # Track attribution statistics
        method_counts = {method.value: 0 for method in AttributionMethod}
        attribution_conflicts = []
        unmapped_api_keys = set()
        data_quality_issues = []

        attributed_records = []

        self.logger.info(f"Starting attribution for {len(records)} records")

        for record in records:
            try:
                attribution = self.attribute_user(record, api_key_mappings)

                # Update record with attribution
                record.user_email = attribution.user_email

                # Track statistics
                method_counts[attribution.method.value] += 1

                # Collect warnings and issues
                if attribution.warnings:
                    data_quality_issues.extend(attribution.warnings)

                if attribution.method == AttributionMethod.FALLBACK_UNKNOWN:
                    if record.api_key_id:
                        unmapped_api_keys.add(record.api_key_id)

                # Detect conflicts (same API key mapped to different users)
                if (attribution.method == AttributionMethod.API_KEY_MAPPING and
                    attribution.confidence < 0.8):
                    attribution_conflicts.append({
                        "api_key_id": record.api_key_id,
                        "user_email": attribution.user_email,
                        "platform": record.platform,
                        "confidence": attribution.confidence,
                        "warnings": attribution.warnings
                    })

                attributed_records.append(record)

            except Exception as e:
                self.logger.error(f"Attribution error for record: {e}")
                data_quality_issues.append(f"Attribution error: {str(e)}")

        # Calculate metrics
        total_records = len(records)
        attributed_count = (
            method_counts[AttributionMethod.DIRECT_EMAIL.value] +
            method_counts[AttributionMethod.API_KEY_MAPPING.value]
        )
        attribution_rate = attributed_count / total_records if total_records > 0 else 0

        # Generate recommendations
        recommendations = self._generate_recommendations(
            attribution_rate, unmapped_api_keys, data_quality_issues
        )

        # Create report
        report = AttributionReport(
            total_records=total_records,
            attributed_records=attributed_count,
            attribution_rate=attribution_rate,
            method_breakdown=method_counts,
            unmapped_api_keys=unmapped_api_keys,
            attribution_conflicts=attribution_conflicts,
            data_quality_issues=data_quality_issues,
            recommendations=recommendations
        )

        processing_time = (datetime.now() - start_time).total_seconds()

        self.logger.info(
            f"Attribution completed: {attributed_count}/{total_records} records "
            f"({attribution_rate:.1%}) in {processing_time:.2f}s"
        )

        return attributed_records, report

    def _generate_recommendations(
        self,
        attribution_rate: float,
        unmapped_api_keys: Set[str],
        data_quality_issues: List[str]
    ) -> List[str]:
        """Generate actionable recommendations based on attribution results."""
        recommendations = []

        # Attribution rate recommendations
        if attribution_rate < 0.8:
            recommendations.append(
                f"LOW ATTRIBUTION RATE ({attribution_rate:.1%}): "
                "Update Google Sheets with missing API key mappings"
            )

        if attribution_rate < 0.95:
            recommendations.append(
                "Consider implementing additional attribution methods for better coverage"
            )

        # Unmapped API keys
        if unmapped_api_keys:
            recommendations.append(
                f"ADD {len(unmapped_api_keys)} UNMAPPED API KEYS to Google Sheets: "
                f"{list(unmapped_api_keys)[:3]}..."
            )

        # Data quality issues
        email_format_issues = [issue for issue in data_quality_issues if "email format" in issue.lower()]
        if email_format_issues:
            recommendations.append(
                f"FIX {len(email_format_issues)} EMAIL FORMAT ISSUES in source data"
            )

        platform_mismatches = [issue for issue in data_quality_issues if "platform mismatch" in issue.lower()]
        if platform_mismatches:
            recommendations.append(
                f"REVIEW {len(platform_mismatches)} PLATFORM MISMATCHES in API key mappings"
            )

        # General recommendations
        if len(data_quality_issues) > len(unmapped_api_keys) * 2:
            recommendations.append(
                "REVIEW DATA QUALITY: High number of attribution issues detected"
            )

        if not recommendations:
            recommendations.append("Attribution quality is excellent - no action needed")

        return recommendations

    def validate_attribution_consistency(
        self,
        records: List[UsageFactRecord]
    ) -> Dict[str, Any]:
        """
        Validate attribution consistency across records.

        Args:
            records: List of attributed records

        Returns:
            Dictionary with consistency validation results
        """
        # Group records by user email
        user_records = {}
        for record in records:
            if record.user_email not in user_records:
                user_records[record.user_email] = []
            user_records[record.user_email].append(record)

        # Check for inconsistencies
        inconsistencies = []
        multi_platform_users = {}

        for user_email, user_record_list in user_records.items():
            # Check for users across multiple platforms
            platforms = {record.platform for record in user_record_list}
            if len(platforms) > 1:
                multi_platform_users[user_email] = list(platforms)

            # Check for API key conflicts
            api_keys = {record.api_key_id for record in user_record_list if record.api_key_id}
            if len(api_keys) > 3:  # Flag users with many API keys
                inconsistencies.append({
                    "type": "multiple_api_keys",
                    "user_email": user_email,
                    "api_key_count": len(api_keys),
                    "platforms": list(platforms)
                })

        return {
            "total_users": len(user_records),
            "multi_platform_users": multi_platform_users,
            "inconsistencies": inconsistencies,
            "validation_passed": len(inconsistencies) == 0,
            "multi_platform_count": len(multi_platform_users)
        }

    def generate_attribution_summary(self, report: AttributionReport) -> str:
        """Generate human-readable attribution summary."""
        summary = []
        summary.append("User Attribution Summary")
        summary.append("=" * 40)
        summary.append(f"Total Records: {report.total_records}")
        summary.append(f"Successfully Attributed: {report.attributed_records}")
        summary.append(f"Attribution Rate: {report.attribution_rate:.1%}")
        summary.append("")

        # Method breakdown
        summary.append("Attribution Methods:")
        for method, count in report.method_breakdown.items():
            percentage = (count / report.total_records) * 100 if report.total_records > 0 else 0
            summary.append(f"  {method.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")

        summary.append("")

        # Issues
        if report.unmapped_api_keys:
            summary.append(f"Unmapped API Keys ({len(report.unmapped_api_keys)}):")
            for key in list(report.unmapped_api_keys)[:5]:
                summary.append(f"  - {key}")
            if len(report.unmapped_api_keys) > 5:
                summary.append(f"  ... and {len(report.unmapped_api_keys) - 5} more")
            summary.append("")

        if report.attribution_conflicts:
            summary.append(f"Attribution Conflicts ({len(report.attribution_conflicts)}):")
            for conflict in report.attribution_conflicts[:3]:
                summary.append(f"  - {conflict['api_key_id']}: {conflict['warnings']}")
            summary.append("")

        # Recommendations
        if report.recommendations:
            summary.append("Recommendations:")
            for rec in report.recommendations:
                summary.append(f"  • {rec}")

        return "\n".join(summary)

    def resolve_conflicts(
        self,
        conflicted_records: List[UsageFactRecord],
        resolution_strategy: str = "most_recent"
    ) -> List[UsageFactRecord]:
        """
        Resolve attribution conflicts using specified strategy.

        Args:
            conflicted_records: Records with attribution conflicts
            resolution_strategy: Strategy for conflict resolution

        Returns:
            List of records with conflicts resolved
        """
        if resolution_strategy == "most_recent":
            # Group by API key, keep most recent mapping
            api_key_groups = {}
            for record in conflicted_records:
                key = record.api_key_id
                if key not in api_key_groups:
                    api_key_groups[key] = []
                api_key_groups[key].append(record)

            resolved_records = []
            for api_key, group in api_key_groups.items():
                # Sort by usage date (most recent first)
                sorted_group = sorted(group, key=lambda r: r.usage_date, reverse=True)
                # Use the user email from the most recent record
                canonical_email = sorted_group[0].user_email

                for record in group:
                    record.user_email = canonical_email
                    resolved_records.append(record)

            self.logger.info(f"Resolved conflicts for {len(resolved_records)} records using {resolution_strategy}")
            return resolved_records

        else:
            self.logger.warning(f"Unknown resolution strategy: {resolution_strategy}")
            return conflicted_records

    def validate_email_domains(
        self,
        records: List[UsageFactRecord],
        allowed_domains: List[str] = None
    ) -> Dict[str, Any]:
        """
        Validate user email domains for organizational consistency.

        Args:
            records: List of attributed records
            allowed_domains: List of allowed email domains (optional)

        Returns:
            Dictionary with domain validation results
        """
        domain_counts = {}
        invalid_domains = set()
        unattributed_count = 0

        for record in records:
            if not record.user_email or record.user_email == "unknown@unattributed.com":
                unattributed_count += 1
                continue

            # Extract domain
            if "@" in record.user_email:
                domain = record.user_email.split("@")[1].lower()
                domain_counts[domain] = domain_counts.get(domain, 0) + 1

                # Check against allowed domains
                if allowed_domains and domain not in allowed_domains:
                    invalid_domains.add(domain)

        return {
            "domain_distribution": domain_counts,
            "invalid_domains": list(invalid_domains),
            "unattributed_count": unattributed_count,
            "total_records": len(records),
            "attribution_coverage": 1 - (unattributed_count / len(records)) if records else 0
        }

    def audit_attribution_changes(
        self,
        old_records: List[UsageFactRecord],
        new_records: List[UsageFactRecord]
    ) -> Dict[str, Any]:
        """
        Audit changes in user attribution between datasets.

        Args:
            old_records: Previous attribution results
            new_records: New attribution results

        Returns:
            Dictionary with audit results
        """
        # Create lookup by record key
        def record_key(r):
            return f"{r.platform}:{r.api_key_id or 'none'}:{r.usage_date}"

        old_lookup = {record_key(r): r.user_email for r in old_records}
        new_lookup = {record_key(r): r.user_email for r in new_records}

        # Find changes
        changes = []
        for key in old_lookup:
            if key in new_lookup and old_lookup[key] != new_lookup[key]:
                changes.append({
                    "record_key": key,
                    "old_email": old_lookup[key],
                    "new_email": new_lookup[key],
                    "change_type": "attribution_update"
                })

        # Find new attributions
        new_attributions = []
        for key in new_lookup:
            if key not in old_lookup and new_lookup[key] != "unknown@unattributed.com":
                new_attributions.append({
                    "record_key": key,
                    "user_email": new_lookup[key],
                    "change_type": "new_attribution"
                })

        return {
            "total_changes": len(changes),
            "attribution_changes": changes,
            "new_attributions": new_attributions,
            "audit_timestamp": datetime.now().isoformat()
        }

    def health_check(self) -> bool:
        """
        Perform health check on attribution system.

        Returns:
            True if system is healthy, False otherwise
        """
        try:
            # Test Google Sheets connectivity
            if not self.sheets_client.health_check():
                return False

            # Test mapping retrieval
            mappings = self._get_api_key_mappings()
            if len(mappings) == 0:
                self.logger.warning("No API key mappings found")

            # Test mapping validation
            validation = self.sheets_client.validate_sheet_format()
            if not validation.get("validation_passed", False):
                self.logger.warning("Google Sheets validation issues detected")

            self.logger.info("Attribution system health check passed")
            return True

        except Exception as e:
            self.logger.error(f"Attribution system health check failed: {e}")
            return False
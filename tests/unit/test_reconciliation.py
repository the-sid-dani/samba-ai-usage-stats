"""Unit tests for vendor invoice reconciliation system."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, timedelta
from decimal import Decimal

from src.processing.reconciliation import (
    VendorInvoiceReconciliationEngine, VarianceAnalysis, ReconciliationReport,
    ReconciliationStatus
)


@pytest.fixture
def reconciliation_engine():
    """Create VendorInvoiceReconciliationEngine instance with mocked dependencies."""
    with patch('src.processing.reconciliation.bigquery.Client'), \
         patch('src.processing.reconciliation.config') as mock_config:
        mock_config.project_id = "test-project"
        mock_config.dataset = "test_dataset"

        return VendorInvoiceReconciliationEngine()


class TestVendorInvoiceReconciliationEngine:
    """Test cases for VendorInvoiceReconciliationEngine."""

    def test_initialization(self, reconciliation_engine):
        """Test reconciliation engine initialization."""
        assert reconciliation_engine.project_id == "test-project"
        assert reconciliation_engine.dataset_id == "test_dataset"
        assert reconciliation_engine.ACCEPTABLE_VARIANCE_PERCENTAGE == 5.0

    def test_analyze_cost_variance_matched(self, reconciliation_engine):
        """Test cost variance analysis for matched costs (AC 2)."""
        # Given: Calculated and vendor costs are within acceptable variance
        calculated_cost = Decimal('1000.00')
        vendor_cost = Decimal('1020.00')  # 2% variance - acceptable

        # When: Analyzing variance
        result = reconciliation_engine._analyze_cost_variance(
            "anthropic", "2025-09", calculated_cost, vendor_cost
        )

        # Then: Should be marked as acceptable variance
        assert result.platform == "anthropic"
        assert result.variance_percentage == -2.0  # Calculated is 2% less than vendor
        assert result.status == ReconciliationStatus.VARIANCE_ACCEPTABLE
        assert not result.threshold_breached

    def test_analyze_cost_variance_warning(self, reconciliation_engine):
        """Test cost variance analysis for warning threshold (AC 2)."""
        # Given: Calculated cost exceeds warning threshold
        calculated_cost = Decimal('1000.00')
        vendor_cost = Decimal('900.00')  # 11.1% variance - warning level

        # When: Analyzing variance
        result = reconciliation_engine._analyze_cost_variance(
            "cursor", "2025-09", calculated_cost, vendor_cost
        )

        # Then: Should be marked as warning variance
        assert result.variance_percentage == pytest.approx(11.1, rel=0.1)
        assert result.status == ReconciliationStatus.VARIANCE_WARNING
        assert result.threshold_breached

    def test_analyze_cost_variance_critical(self, reconciliation_engine):
        """Test cost variance analysis for critical threshold (AC 2)."""
        # Given: Calculated cost exceeds critical threshold
        calculated_cost = Decimal('1000.00')
        vendor_cost = Decimal('750.00')  # 33.3% variance - critical level

        # When: Analyzing variance
        result = reconciliation_engine._analyze_cost_variance(
            "anthropic", "2025-09", calculated_cost, vendor_cost
        )

        # Then: Should be marked as critical variance
        assert result.variance_percentage == pytest.approx(33.3, rel=0.1)
        assert result.status == ReconciliationStatus.VARIANCE_CRITICAL
        assert result.threshold_breached

    def test_analyze_cost_variance_missing_data(self, reconciliation_engine):
        """Test variance analysis for missing calculated data (AC 2)."""
        # Given: No calculated cost but vendor has cost (missing data scenario)
        calculated_cost = Decimal('0.00')
        vendor_cost = Decimal('500.00')

        # When: Analyzing variance
        result = reconciliation_engine._analyze_cost_variance(
            "cursor", "2025-09", calculated_cost, vendor_cost
        )

        # Then: Should be marked as missing data
        assert result.status == ReconciliationStatus.MISSING_DATA
        assert result.threshold_breached

    @patch('src.processing.reconciliation.bigquery.Client')
    def test_get_calculated_monthly_costs(self, mock_client, reconciliation_engine):
        """Test BigQuery cost retrieval for reconciliation (AC 2)."""
        # Given: Mocked BigQuery results
        mock_row1 = Mock()
        mock_row1.platform = "anthropic"
        mock_row1.total_cost = 1234.56

        mock_row2 = Mock()
        mock_row2.platform = "cursor"
        mock_row2.total_cost = 567.89

        mock_client.return_value.query.return_value.result.return_value = [mock_row1, mock_row2]

        # When: Getting calculated costs
        period_start = date(2025, 9, 1)
        period_end = date(2025, 9, 30)
        costs = reconciliation_engine._get_calculated_monthly_costs(period_start, period_end)

        # Then: Should return platform costs as Decimal
        assert costs["anthropic"] == Decimal('1234.56')
        assert costs["cursor"] == Decimal('567.89')
        mock_client.return_value.query.assert_called_once()

    def test_validate_vendor_invoice_data_valid(self, reconciliation_engine):
        """Test vendor invoice data validation with valid data (AC 2)."""
        # Given: Valid vendor invoice data
        vendor_invoices = {
            "anthropic": 1250.00,
            "cursor": 750.50
        }

        # When: Validating invoice data
        issues = reconciliation_engine.validate_vendor_invoice_data(vendor_invoices)

        # Then: Should have no validation issues
        assert len(issues) == 0

    def test_validate_vendor_invoice_data_invalid_platform(self, reconciliation_engine):
        """Test vendor invoice validation with invalid platform name (AC 2)."""
        # Given: Invalid platform identifier
        vendor_invoices = {
            "": 1000.00,  # Empty platform name
            None: 500.00  # None platform name
        }

        # When: Validating invoice data
        issues = reconciliation_engine.validate_vendor_invoice_data(vendor_invoices)

        # Then: Should detect platform validation errors
        assert len(issues) == 2
        assert all(issue["code"] == "INVALID_PLATFORM" for issue in issues)
        assert all(issue["level"] == "error" for issue in issues)

    def test_validate_vendor_invoice_data_negative_amount(self, reconciliation_engine):
        """Test vendor invoice validation with negative amounts (AC 2)."""
        # Given: Negative invoice amount
        vendor_invoices = {
            "anthropic": -100.00
        }

        # When: Validating invoice data
        issues = reconciliation_engine.validate_vendor_invoice_data(vendor_invoices)

        # Then: Should detect negative amount error
        assert len(issues) == 1
        assert issues[0]["code"] == "NEGATIVE_INVOICE_AMOUNT"
        assert issues[0]["level"] == "error"
        assert issues[0]["platform"] == "anthropic"

    def test_validate_vendor_invoice_data_invalid_format(self, reconciliation_engine):
        """Test vendor invoice validation with invalid amount format (AC 2)."""
        # Given: Invalid amount format
        vendor_invoices = {
            "cursor": "invalid_amount",
            "anthropic": None
        }

        # When: Validating invoice data
        issues = reconciliation_engine.validate_vendor_invoice_data(vendor_invoices)

        # Then: Should detect format validation errors
        assert len(issues) == 2
        assert all(issue["code"] == "INVALID_INVOICE_AMOUNT" for issue in issues)
        assert all(issue["level"] == "error" for issue in issues)

    def test_create_variance_alert_critical(self, reconciliation_engine):
        """Test variance alert creation for critical threshold breach (AC 2, 6)."""
        # Given: Critical variance analysis
        variance_analysis = VarianceAnalysis(
            platform="anthropic",
            period="2025-09",
            calculated_cost=Decimal('1000.00'),
            vendor_cost=Decimal('750.00'),
            variance_amount=Decimal('250.00'),
            variance_percentage=33.3,
            status=ReconciliationStatus.VARIANCE_CRITICAL,
            threshold_breached=True
        )

        # When: Creating alert
        alert = reconciliation_engine.create_variance_alert(variance_analysis)

        # Then: Should create critical alert
        assert alert["alert_type"] == "vendor_reconciliation_variance"
        assert alert["severity"] == "critical"
        assert alert["platform"] == "anthropic"
        assert alert["variance_percentage"] == 33.3
        assert alert["requires_action"] is True
        assert "33.3%" in alert["message"]

    def test_create_variance_alert_no_threshold_breach(self, reconciliation_engine):
        """Test variance alert creation when no threshold is breached."""
        # Given: Acceptable variance (no threshold breach)
        variance_analysis = VarianceAnalysis(
            platform="cursor",
            period="2025-09",
            calculated_cost=Decimal('1000.00'),
            vendor_cost=Decimal('1020.00'),
            variance_amount=Decimal('-20.00'),
            variance_percentage=-2.0,
            status=ReconciliationStatus.VARIANCE_ACCEPTABLE,
            threshold_breached=False
        )

        # When: Creating alert
        alert = reconciliation_engine.create_variance_alert(variance_analysis)

        # Then: Should return empty alert (no action needed)
        assert alert == {}

    def test_determine_overall_status_critical(self, reconciliation_engine):
        """Test overall status determination with critical variances."""
        # Given: Mix of variance analyses with critical issues
        analyses = [
            VarianceAnalysis("anthropic", "2025-09", Decimal('1000'), Decimal('750'),
                           Decimal('250'), 33.3, ReconciliationStatus.VARIANCE_CRITICAL, True),
            VarianceAnalysis("cursor", "2025-09", Decimal('500'), Decimal('520'),
                           Decimal('-20'), -4.0, ReconciliationStatus.VARIANCE_ACCEPTABLE, False)
        ]

        # When: Determining overall status
        status = reconciliation_engine._determine_overall_status(analyses)

        # Then: Should return critical (highest priority)
        assert status == ReconciliationStatus.VARIANCE_CRITICAL

    def test_determine_overall_status_matched(self, reconciliation_engine):
        """Test overall status determination with all matched."""
        # Given: All variances are acceptable
        analyses = [
            VarianceAnalysis("anthropic", "2025-09", Decimal('1000'), Decimal('1010'),
                           Decimal('-10'), -1.0, ReconciliationStatus.MATCHED, False),
            VarianceAnalysis("cursor", "2025-09", Decimal('500'), Decimal('495'),
                           Decimal('5'), 1.0, ReconciliationStatus.MATCHED, False)
        ]

        # When: Determining overall status
        status = reconciliation_engine._determine_overall_status(analyses)

        # Then: Should return matched
        assert status == ReconciliationStatus.MATCHED

    def test_generate_reconciliation_report_summary(self, reconciliation_engine):
        """Test reconciliation report summary generation (AC 2)."""
        # Given: Reconciliation report with mixed results
        report = ReconciliationReport(
            reconciliation_id="test_recon_123",
            period_start=date(2025, 9, 1),
            period_end=date(2025, 9, 30),
            total_platforms=2,
            matched_platforms=1,
            variance_analyses=[
                VarianceAnalysis("anthropic", "2025-09", Decimal('1000'), Decimal('1020'),
                               Decimal('-20'), -2.0, ReconciliationStatus.VARIANCE_ACCEPTABLE, False),
                VarianceAnalysis("cursor", "2025-09", Decimal('500'), Decimal('400'),
                               Decimal('100'), 25.0, ReconciliationStatus.VARIANCE_CRITICAL, True)
            ],
            overall_status=ReconciliationStatus.VARIANCE_CRITICAL,
            total_variance_amount=Decimal('80.00'),
            total_variance_percentage=5.6,
            requires_manual_review=True
        )

        # When: Generating summary
        summary = reconciliation_engine.generate_reconciliation_report_summary(report)

        # Then: Should contain key information
        assert "VENDOR INVOICE RECONCILIATION REPORT" in summary
        assert "test_recon_123" in summary
        assert "VARIANCE_CRITICAL" in summary
        assert "anthropic" in summary
        assert "cursor" in summary
        assert "IMMEDIATE ACTION" in summary  # Due to critical variance
        assert "1/2 matched" in summary
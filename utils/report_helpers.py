"""Shared utility functions for CLI and PDF report generators."""

from typing import Dict, Tuple, List
from datetime import datetime
from dateutil.relativedelta import relativedelta


class ReportDataParser:
    """Parse and extract data from report_data structure."""

    @staticmethod
    def parse_report_data(report_data: List) -> Dict:
        """Parse report data into named components.

        Args:
            report_data: List containing [cost_data, total_savings, sp_coverage_with_trend,
                        rds_coverage, quarterly_costs, budget_anomalies]

        Returns:
            Dictionary with named data components
        """
        return {
            'cost_data': report_data[0] if len(report_data) > 0 else {},
            'total_savings': report_data[1] if len(report_data) > 1 else {},
            'sp_coverage_with_trend': report_data[2] if len(report_data) > 2 else {},
            'rds_coverage_with_trend': report_data[3] if len(report_data) > 3 else {},
            'quarterly_costs': report_data[4] if len(report_data) > 4 else {},
            'budget_anomalies': report_data[5] if len(report_data) > 5 else {},
        }

    @staticmethod
    def extract_current_month_coverage(sp_coverage_with_trend: Dict, rds_coverage_with_trend: Dict) -> Tuple[Dict, Dict]:
        """Extract current month coverage from trend data.

        Args:
            sp_coverage_with_trend: Savings Plan coverage with trend
            rds_coverage_with_trend: RDS coverage with trend

        Returns:
            Tuple of (sp_coverage, rds_coverage)
        """
        sp_coverage = sp_coverage_with_trend.get('selected_month', {}) if sp_coverage_with_trend else {}
        rds_coverage = rds_coverage_with_trend.get('selected_month', {}) if rds_coverage_with_trend else {}
        return sp_coverage, rds_coverage


class CostCalculations:
    """Cost calculation utilities."""

    @staticmethod
    def calculate_total_cost(cost_data: Dict) -> float:
        """Calculate total cost from cost data.

        Args:
            cost_data: Cost data dictionary from AWS Cost Explorer

        Returns:
            Total cost amount
        """
        total = 0.0
        cost_results = cost_data.get('cost_data', {}).get('ResultsByTime', [])

        for result in cost_results:
            for group in result.get('Groups', []):
                amount = float(group.get('Metrics', {}).get('BlendedCost', {}).get('Amount', '0'))
                total += amount

        return total

    @staticmethod
    def calculate_mom_change(current_month_cost: float, previous_month_cost: float) -> Tuple[float, float]:
        """Calculate month-over-month change.

        Args:
            current_month_cost: Current month cost
            previous_month_cost: Previous month cost

        Returns:
            Tuple of (absolute_change, percentage_change)
        """
        mom_change = 0.0
        mom_percentage = 0.0

        if previous_month_cost > 0:
            mom_change = current_month_cost - previous_month_cost
            mom_percentage = (mom_change / previous_month_cost) * 100

        return mom_change, mom_percentage

    @staticmethod
    def calculate_optimization_rate(total_savings: float, total_cost: float) -> float:
        """Calculate cost optimization rate.

        Args:
            total_savings: Total monthly savings
            total_cost: Total monthly cost

        Returns:
            Optimization rate as percentage
        """
        if total_cost > 0:
            return (total_savings / total_cost * 100)
        return 0.0

    @staticmethod
    def calculate_quarterly_average(quarterly_total: float) -> float:
        """Calculate quarterly average monthly cost.

        Args:
            quarterly_total: Total quarterly cost

        Returns:
            Average monthly cost
        """
        return quarterly_total / 3 if quarterly_total > 0 else 0


class StatusDetermination:
    """Status and threshold determination utilities."""

    @staticmethod
    def get_coverage_status(coverage_pct: float) -> str:
        """Get coverage status based on percentage.

        Args:
            coverage_pct: Coverage percentage

        Returns:
            Status string: 'Excellent', 'Good', 'Fair', or 'Poor'
        """
        if coverage_pct >= 90:
            return "Excellent"
        elif coverage_pct >= 70:
            return "Good"
        elif coverage_pct >= 50:
            return "Fair"
        else:
            return "Poor"

    @staticmethod
    def get_utilization_status(utilization_pct: float) -> str:
        """Get utilization status based on percentage.

        Args:
            utilization_pct: Utilization percentage

        Returns:
            Status string: 'Excellent', 'Good', 'Fair', or 'Poor'
        """
        if utilization_pct >= 90:
            return "Excellent"
        elif utilization_pct >= 70:
            return "Good"
        elif utilization_pct >= 50:
            return "Fair"
        else:
            return "Poor"

    @staticmethod
    def get_coverage_recommendation(coverage_pct: float, service_type: str = "Savings Plan") -> str:
        """Get recommendation based on coverage percentage.

        Args:
            coverage_pct: Coverage percentage
            service_type: Type of service (e.g., "Savings Plan", "RDS Reserved Instance")

        Returns:
            Recommendation string
        """
        if coverage_pct < 50:
            return f"Low {service_type} coverage - consider purchasing"
        elif coverage_pct >= 90:
            return f"Excellent {service_type} coverage!"
        elif coverage_pct >= 70:
            return f"Good {service_type} coverage"
        else:
            return f"Fair {service_type} coverage"

    @staticmethod
    def get_utilization_recommendation(utilization_pct: float, service_type: str = "Savings Plans") -> str:
        """Get recommendation based on utilization percentage.

        Args:
            utilization_pct: Utilization percentage
            service_type: Type of service

        Returns:
            Recommendation string
        """
        if utilization_pct < 70:
            return f"Low utilization - review {service_type} sizing"
        elif utilization_pct >= 90:
            return f"Excellent utilization of {service_type}!"
        else:
            return f"Good utilization of {service_type}"


class TrendAnalysis:
    """Trend analysis utilities."""

    @staticmethod
    def get_cost_trend(oldest: float, middle: float, newest: float) -> str:
        """Analyze cost trend over three months.

        Args:
            oldest: Oldest month cost
            middle: Middle month cost
            newest: Newest month cost

        Returns:
            Trend description string
        """
        if oldest == 0 and middle == 0 and newest == 0:
            return "No data available"

        if oldest > 0 and middle > 0 and newest > 0:
            overall_change = ((newest - oldest) / oldest) * 100

            if overall_change > 5:
                return f"Increasing ({overall_change:+.1f}% growth)"
            elif overall_change < -5:
                return f"Decreasing ({overall_change:+.1f}% decline)"
            else:
                return f"Stable ({overall_change:+.1f}% change)"
        else:
            return "Insufficient data for trend analysis"

    @staticmethod
    def get_trend_direction_simple(current: float, previous: float) -> str:
        """Get simple trend direction.

        Args:
            current: Current value
            previous: Previous value

        Returns:
            Trend direction: 'Increasing', 'Decreasing', or 'Stable'
        """
        if current > previous:
            return "Increasing"
        elif current < previous:
            return "Decreasing"
        else:
            return "Stable"


class BudgetHelpers:
    """Budget-related helper functions."""

    @staticmethod
    def get_severity_emoji(severity: str) -> str:
        """Get emoji for budget severity.

        Args:
            severity: Severity level (CRITICAL, HIGH, MEDIUM, LOW)

        Returns:
            Emoji string
        """
        severity_map = {
            'CRITICAL': '🔴',
            'HIGH': '🟠',
            'MEDIUM': '🟡',
            'LOW': '🟢'
        }
        return severity_map.get(severity, '⚪')

    @staticmethod
    def categorize_budgets_by_severity(budgets: List[Dict]) -> Dict[str, int]:
        """Categorize budgets by severity level.

        Args:
            budgets: List of budget dictionaries

        Returns:
            Dictionary with counts by severity
        """
        return {
            'critical': len([b for b in budgets if b.get('severity') == 'CRITICAL']),
            'high': len([b for b in budgets if b.get('severity') == 'HIGH']),
            'medium': len([b for b in budgets if b.get('severity') == 'MEDIUM']),
            'low': len([b for b in budgets if b.get('severity') == 'LOW'])
        }


class DateFormatting:
    """Date formatting utilities."""

    @staticmethod
    def get_month_name(date: datetime, format_type: str = 'full') -> str:
        """Get formatted month name.

        Args:
            date: Datetime object
            format_type: Format type ('full' = 'January 2024', 'short' = 'Jan 2024')

        Returns:
            Formatted month string
        """
        if not date:
            return "Unknown Month"

        if format_type == 'short':
            return date.strftime('%b %Y')
        else:
            return date.strftime('%B %Y')

    @staticmethod
    def get_previous_month_name(date: datetime, format_type: str = 'full') -> str:
        """Get previous month name.

        Args:
            date: Current datetime object
            format_type: Format type ('full' or 'short')

        Returns:
            Previous month string
        """
        if not date:
            return "Previous Month"

        previous = date - relativedelta(months=1)
        return DateFormatting.get_month_name(previous, format_type)

    @staticmethod
    def get_month_names_for_quarter(start_date: datetime) -> Tuple[str, str, str]:
        """Get month names for quarterly display.

        Args:
            start_date: Start date of selected month

        Returns:
            Tuple of (current_month, month_minus_1, month_minus_2) in 'Mon YYYY' format
        """
        if not start_date:
            return "Month 0", "Month -1", "Month -2"

        month_0 = start_date.strftime('%b %Y')
        month_1 = (start_date - relativedelta(months=1)).strftime('%b %Y')
        month_2 = (start_date - relativedelta(months=2)).strftime('%b %Y')

        return month_0, month_1, month_2


class SavingsHelpers:
    """Savings-related helper functions."""

    @staticmethod
    def should_display_savings_item(source_name: str, amount: float) -> bool:
        """Determine if a savings item should be displayed.

        Args:
            source_name: Name of the savings source
            amount: Savings amount

        Returns:
            True if should be displayed, False otherwise
        """
        # Always show Savings Plans and Credit Savings, show others only if amount > 0
        if source_name in ["Savings Plans", "Credit Savings"]:
            return True
        return amount > 0

    @staticmethod
    def calculate_savings_percentage(amount: float, total: float) -> float:
        """Calculate percentage of total savings.

        Args:
            amount: Individual savings amount
            total: Total savings amount

        Returns:
            Percentage value
        """
        if total > 0:
            return (amount / total * 100)
        return 0.0

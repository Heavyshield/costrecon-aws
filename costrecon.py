"""Main CLI entry point for CostRecon."""

import click
from datetime import datetime
from dateutil.relativedelta import relativedelta
import re
from aws_client import CostExplorerClient
from utils import PDFReportGenerator, print_console_report
from constants import MONTH_MAPPINGS, DEFAULT_REGION


def parse_month_year(month_input: str, current_year: int = None) -> tuple:
    """Parse month input and return start_date, end_date for that month.
    
    Args:
        month_input: Month name (jan, feb, march, etc.) or month-year (jan2024, feb-2024)
        current_year: Year to use if not specified in month_input
    
    Returns:
        Tuple of (start_date, end_date) for the specified month
    """
    if current_year is None:
        current_year = datetime.now().year
    
    month_input = month_input.lower().strip()
    
    # Handle month-year formats like "jan2024", "jan-2024", "jan 2024"
    year = current_year
    month_str = month_input
    
    # Extract year if present using regex to find 4-digit years
    
    # Look for 4-digit year pattern (19xx or 20xx or 21xx)
    year_pattern = r'(19|20|21)\d{2}'
    year_match = re.search(year_pattern, month_input)
    
    if year_match:
        # Found a year, extract it and the month part
        year_str = year_match.group()
        try:
            year = int(year_str)
            # Remove year from month_input to get just the month
            month_str = re.sub(year_pattern, '', month_input).strip('-').strip()
        except ValueError:
            pass
    else:
        # No year found, check for separators that might indicate month-only format
        for separator in ['-', ' ']:
            if separator in month_input:
                parts = month_input.split(separator)
                if len(parts) >= 1:
                    month_str = parts[0].strip()
                break
    
    # Use month mappings from constants
    month_names = MONTH_MAPPINGS.copy()
    # Add common abbreviation for September
    month_names['sept'] = 9
    
    if month_str not in month_names:
        available_months = ', '.join(sorted(MONTH_MAPPINGS.keys()))
        raise click.BadParameter(f"Invalid month '{month_str}'. Available: {available_months}")
    
    month_num = month_names[month_str]

    # Get first day of the selected month
    start_date = datetime(year, month_num, 1)

    # AWS Cost Explorer API uses exclusive end dates.
    # To include the entire month, set end_date to the first day of the next month.
    # relativedelta handles all edge cases (month boundaries, leap years, etc.)
    end_date = start_date + relativedelta(months=1)

    return start_date, end_date


def calculate_quarterly_costs(selected_month_cost_data, month_one_cost_data, month_two_cost_data):
    """Calculate quarterly cost aggregation from three months of cost data.
    
    Args:
        selected_month_cost_data: Cost data for selected month
        month_one_cost_data: Cost data for month -1
        month_two_cost_data: Cost data for month -2
    
    Returns:
        Dictionary containing quarterly cost totals and breakdown
    """
    def extract_total_cost(cost_data):
        """Extract total cost from cost data structure."""
        total = 0.0
        if 'cost_data' in cost_data:
            for result in cost_data['cost_data'].get('ResultsByTime', []):
                # With SERVICE grouping, sum across all groups
                for group in result.get('Groups', []):
                    amount = float(group.get('Metrics', {}).get('BlendedCost', {}).get('Amount', '0'))
                    total += amount
        return total
    
    selected_month_total = extract_total_cost(selected_month_cost_data)
    month_one_total = extract_total_cost(month_one_cost_data)
    month_two_total = extract_total_cost(month_two_cost_data)
    
    quarterly_total = selected_month_total + month_one_total + month_two_total
    
    return {
        'selected_month_cost': selected_month_total,
        'month_minus_one_cost': month_one_total,
        'month_minus_two_cost': month_two_total,
        'quarterly_total_cost': quarterly_total
    }


def calculate_savings_plan_trend(month_two_coverage, month_one_coverage, selected_month_coverage):
    """Calculate quarterly trend for savings plan coverage.

    Args:
        month_two_coverage: Coverage data for month -2 (oldest)
        month_one_coverage: Coverage data for month -1 (middle)
        selected_month_coverage: Coverage data for selected month (newest)

    Returns:
        Dictionary containing trend analysis
    """
    # Extract coverage percentages
    coverage_values = []
    coverage_labels = []

    for month_data, label in [
        (month_two_coverage, "Month -2"),
        (month_one_coverage, "Month -1"),
        (selected_month_coverage, "Selected Month")
    ]:
        if month_data and 'average_coverage_percentage' in month_data:
            coverage_values.append(month_data['average_coverage_percentage'])
            coverage_labels.append(label)
        else:
            coverage_values.append(0.0)
            coverage_labels.append(f"{label} (No Data)")

    # Calculate trend
    trend_analysis = {
        'coverage_values': coverage_values,
        'coverage_labels': coverage_labels,
        'trend_direction': 'stable',
        'trend_strength': 'none',
        'quarterly_change': 0.0,
        'month_to_month_changes': []
    }

    # Calculate month-to-month changes
    for i in range(1, len(coverage_values)):
        if coverage_values[i-1] > 0 and coverage_values[i] > 0:
            change = coverage_values[i] - coverage_values[i-1]
            trend_analysis['month_to_month_changes'].append({
                'from_month': coverage_labels[i-1],
                'to_month': coverage_labels[i],
                'change': round(change, 2)
            })

    # Calculate overall quarterly change (oldest to newest)
    if coverage_values[0] > 0 and coverage_values[2] > 0:
        quarterly_change = coverage_values[2] - coverage_values[0]
        trend_analysis['quarterly_change'] = round(quarterly_change, 2)

        # Determine trend direction and strength
        abs_change = abs(quarterly_change)

        if abs_change < 2.0:
            trend_analysis['trend_direction'] = 'stable'
            trend_analysis['trend_strength'] = 'minimal'
        elif quarterly_change > 0:
            trend_analysis['trend_direction'] = 'increasing'
            if abs_change > 10.0:
                trend_analysis['trend_strength'] = 'strong'
            elif abs_change > 5.0:
                trend_analysis['trend_strength'] = 'moderate'
            else:
                trend_analysis['trend_strength'] = 'weak'
        else:
            trend_analysis['trend_direction'] = 'decreasing'
            if abs_change > 10.0:
                trend_analysis['trend_strength'] = 'strong'
            elif abs_change > 5.0:
                trend_analysis['trend_strength'] = 'moderate'
            else:
                trend_analysis['trend_strength'] = 'weak'

    # Add summary message
    if trend_analysis['trend_direction'] == 'stable':
        trend_analysis['summary'] = f"Savings Plan coverage has remained stable over the quarter with minimal change ({trend_analysis['quarterly_change']:.1f}%)"
    elif trend_analysis['trend_direction'] == 'increasing':
        trend_analysis['summary'] = f"Savings Plan coverage is trending upward with a {trend_analysis['trend_strength']} increase of {trend_analysis['quarterly_change']:.1f}% over the quarter"
    else:
        trend_analysis['summary'] = f"Savings Plan coverage is trending downward with a {trend_analysis['trend_strength']} decrease of {abs(trend_analysis['quarterly_change']):.1f}% over the quarter"

    return trend_analysis


def calculate_rds_coverage_trend(month_two_coverage, month_one_coverage, selected_month_coverage):
    """Calculate quarterly trend for RDS Reserved Instance coverage.

    Args:
        month_two_coverage: RDS coverage data for month -2 (oldest)
        month_one_coverage: RDS coverage data for month -1 (middle)
        selected_month_coverage: RDS coverage data for selected month (newest)

    Returns:
        Dictionary containing trend analysis
    """
    # Extract coverage percentages (using hours coverage for RDS)
    coverage_values = []
    coverage_labels = []

    for month_data, label in [
        (month_two_coverage, "Month -2"),
        (month_one_coverage, "Month -1"),
        (selected_month_coverage, "Selected Month")
    ]:
        if month_data and 'average_hours_coverage_percentage' in month_data:
            coverage_values.append(month_data['average_hours_coverage_percentage'])
            coverage_labels.append(label)
        else:
            coverage_values.append(0.0)
            coverage_labels.append(f"{label} (No Data)")

    # Calculate trend
    trend_analysis = {
        'coverage_values': coverage_values,
        'coverage_labels': coverage_labels,
        'trend_direction': 'stable',
        'trend_strength': 'none',
        'quarterly_change': 0.0,
        'month_to_month_changes': []
    }

    # Calculate month-to-month changes
    for i in range(1, len(coverage_values)):
        if coverage_values[i-1] > 0 and coverage_values[i] > 0:
            change = coverage_values[i] - coverage_values[i-1]
            trend_analysis['month_to_month_changes'].append({
                'from_month': coverage_labels[i-1],
                'to_month': coverage_labels[i],
                'change': round(change, 2)
            })

    # Calculate overall quarterly change (oldest to newest)
    if coverage_values[0] > 0 and coverage_values[2] > 0:
        quarterly_change = coverage_values[2] - coverage_values[0]
        trend_analysis['quarterly_change'] = round(quarterly_change, 2)

        # Determine trend direction and strength
        abs_change = abs(quarterly_change)

        if abs_change < 2.0:
            trend_analysis['trend_direction'] = 'stable'
            trend_analysis['trend_strength'] = 'minimal'
        elif quarterly_change > 0:
            trend_analysis['trend_direction'] = 'increasing'
            if abs_change > 10.0:
                trend_analysis['trend_strength'] = 'strong'
            elif abs_change > 5.0:
                trend_analysis['trend_strength'] = 'moderate'
            else:
                trend_analysis['trend_strength'] = 'weak'
        else:
            trend_analysis['trend_direction'] = 'decreasing'
            if abs_change > 10.0:
                trend_analysis['trend_strength'] = 'strong'
            elif abs_change > 5.0:
                trend_analysis['trend_strength'] = 'moderate'
            else:
                trend_analysis['trend_strength'] = 'weak'

    # Add summary message
    if trend_analysis['trend_direction'] == 'stable':
        trend_analysis['summary'] = f"RDS Reserved Instance coverage has remained stable over the quarter with minimal change ({trend_analysis['quarterly_change']:.1f}%)"
    elif trend_analysis['trend_direction'] == 'increasing':
        trend_analysis['summary'] = f"RDS Reserved Instance coverage is trending upward with a {trend_analysis['trend_strength']} increase of {trend_analysis['quarterly_change']:.1f}% over the quarter"
    else:
        trend_analysis['summary'] = f"RDS Reserved Instance coverage is trending downward with a {trend_analysis['trend_strength']} decrease of {abs(trend_analysis['quarterly_change']):.1f}% over the quarter"

    return trend_analysis



@click.command()
@click.option('--month', '-m', 
              help='Month for cost analysis (jan, feb, march, etc.). Can include year (jan2024, feb-2024). Defaults to current month.')
@click.option('--output', '-o', default='cost_report.pdf', 
              help='Output PDF filename. Default: cost_report.pdf')
@click.option('--profile', help='AWS profile to use. Uses default profile if not specified.')
@click.option('--region', default=DEFAULT_REGION, help=f'AWS region. Default: {DEFAULT_REGION}')
@click.option('--no-pdf', is_flag=True, help='Skip PDF generation and only show console report.')
def cli(month, output, profile, region, no_pdf):
    """Extract AWS cost data for a specific month and generate comprehensive PDF report.
    
    Examples:
    \b
        costrecon --month jan                 # January of current year
        costrecon --month january2024         # January 2024
        costrecon --month feb-2024            # February 2024
        costrecon -m dec                      # December of current year
        costrecon                             # Current month
        costrecon --no-pdf                    # Skip PDF generation, console only
    """
    
    # Parse month and calculate dates
    if not month:
        # Default to current month
        current_date = datetime.now()
        month = current_date.strftime('%b').lower()
    
    try:
        start_date, end_date = parse_month_year(month)
    except click.BadParameter as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    
    click.echo(f"Generating cost report for {start_date.strftime('%B %Y')}")
    click.echo(f"Period: {start_date.date()} to {end_date.date()}")
    click.echo(f"Output file: {output}")
    
    try:
        # Initialize AWS Cost Explorer client parameters for 3-month analysis
        parameters_selected_month = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        # Calculate previous month -1 dates
        month_one_start = start_date - relativedelta(months=1)
        month_one_end = end_date - relativedelta(months=1)
        parameters_previous_month_one = {
            "start_date": month_one_start,
            "end_date": month_one_end
        }
        
        # Calculate previous month -2 dates
        month_two_start = start_date - relativedelta(months=2)
        month_two_end = end_date - relativedelta(months=2)
        parameters_previous_month_two = {
            "start_date": month_two_start,
            "end_date": month_two_end
        }
        
        # Create 3 Cost Explorer clients for trend analysis
        cost_client_selected_month = CostExplorerClient(profile=profile, region=region, parameters=parameters_selected_month)
        cost_client_month_one = CostExplorerClient(profile=profile, region=region, parameters=parameters_previous_month_one)
        cost_client_month_two = CostExplorerClient(profile=profile, region=region, parameters=parameters_previous_month_two)
        
        # Report raw_data
        report_raw_data = []

        # Fetch cost data for all three months
        click.echo("Fetching cost data from AWS Cost Explorer...")
        click.echo("  - Fetching cost data for selected month...")
        cost_data_month_zero = cost_client_selected_month.get_cost_and_usage()
        
        click.echo("  - Fetching cost data for month -1...")
        try:
            cost_data_month_one = cost_client_month_one.get_cost_and_usage()
        except Exception as e:
            click.echo(f"    Warning: {str(e)}")
            cost_data_month_one = {}
        
        click.echo("  - Fetching cost data for month -2...")
        try:
            cost_data_month_two = cost_client_month_two.get_cost_and_usage()
        except Exception as e:
            click.echo(f"    Warning: {str(e)}")
            cost_data_month_two = {}
        
        # Calculate quarterly costs
        click.echo("Calculating quarterly cost totals...")
        quarterly_costs = calculate_quarterly_costs(cost_data_month_zero, cost_data_month_one, cost_data_month_two)
        
        report_raw_data.append(cost_data_month_zero)

        # Fetch total savings for selected month
        click.echo("Fetching total savings from AWS Cost Explorer...")
        total_savings = cost_client_selected_month.get_total_savings()
        report_raw_data.append(total_savings)

        # Fetch saving plan coverage for 3-month trend analysis
        click.echo("Fetching savings plan coverage for 3-month trend analysis...")
        
        click.echo("  - Fetching coverage for selected month...")
        try:
            sp_coverage_selected = cost_client_selected_month.get_saving_plan_coverage()
        except Exception as e:
            click.echo(f"    Warning: {str(e)}")
            sp_coverage_selected = {}
        
        click.echo("  - Fetching coverage for month -1...")
        try:
            sp_coverage_month_one = cost_client_month_one.get_saving_plan_coverage()
        except Exception as e:
            click.echo(f"    Warning: {str(e)}")
            sp_coverage_month_one = {}
        
        click.echo("  - Fetching coverage for month -2...")
        try:
            sp_coverage_month_two = cost_client_month_two.get_saving_plan_coverage()
        except Exception as e:
            click.echo(f"    Warning: {str(e)}")
            sp_coverage_month_two = {}
        
        # Calculate quarterly trend
        click.echo("Calculating quarterly savings plan trend...")
        sp_trend_analysis = calculate_savings_plan_trend(
            sp_coverage_month_two, 
            sp_coverage_month_one, 
            sp_coverage_selected
        )
        
        # Add coverage data and trend analysis to report
        sp_coverage_with_trend = {
            'selected_month': sp_coverage_selected,
            'month_minus_one': sp_coverage_month_one,
            'month_minus_two': sp_coverage_month_two,
            'trend_analysis': sp_trend_analysis
        }
        report_raw_data.append(sp_coverage_with_trend)

        # Fetch RDS coverage data for 3-month trend analysis
        click.echo("Fetching RDS Reserved Instance coverage for 3-month trend analysis...")

        click.echo("  - Fetching RDS coverage for selected month...")
        try:
            rds_coverage_selected = cost_client_selected_month.get_RDS_coverage()
        except Exception as e:
            click.echo(f"    Warning: {str(e)}")
            rds_coverage_selected = {}

        click.echo("  - Fetching RDS coverage for month -1...")
        try:
            rds_coverage_month_one = cost_client_month_one.get_RDS_coverage()
        except Exception as e:
            click.echo(f"    Warning: {str(e)}")
            rds_coverage_month_one = {}

        click.echo("  - Fetching RDS coverage for month -2...")
        try:
            rds_coverage_month_two = cost_client_month_two.get_RDS_coverage()
        except Exception as e:
            click.echo(f"    Warning: {str(e)}")
            rds_coverage_month_two = {}

        # Calculate quarterly RDS trend
        click.echo("Calculating quarterly RDS Reserved Instance trend...")
        rds_trend_analysis = calculate_rds_coverage_trend(
            rds_coverage_month_two,
            rds_coverage_month_one,
            rds_coverage_selected
        )

        # Add RDS coverage data and trend analysis to report
        rds_coverage_with_trend = {
            'selected_month': rds_coverage_selected,
            'month_minus_one': rds_coverage_month_one,
            'month_minus_two': rds_coverage_month_two,
            'trend_analysis': rds_trend_analysis
        }
        report_raw_data.append(rds_coverage_with_trend)
        
        # Add quarterly costs to report data
        report_raw_data.append(quarterly_costs)

        # Fetch budget anomalies data
        click.echo("Fetching budget anomalies...")
        try:
            budget_anomalies = cost_client_selected_month.get_budgets_anomalies()
        except Exception as e:
            click.echo(f"  Warning: {str(e)}")
            budget_anomalies = {
                'anomaly_budgets': [],
                'total_budgets_checked': 0,
                'anomalies_found': 0,
                'threshold_percentage': 10.0,
                'errors': [f"Budget analysis failed: {str(e)}"]
            }
        report_raw_data.append(budget_anomalies)

        # Print console report
        print_console_report(report_raw_data, start_date, end_date)

        # Generate PDF report (unless --no-pdf flag is used)
        if not no_pdf:
            click.echo("Generating PDF report...")
            pdf_generator = PDFReportGenerator()
            pdf_generator.generate_report(report_raw_data, output, start_date, end_date)
            click.echo(f"✓ Report generated successfully: {output}")
        else:
            click.echo("✓ Console report completed (PDF generation skipped)")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
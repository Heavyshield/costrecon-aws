"""Main CLI entry point for CostRecon."""

import click
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar
from aws_client import CostExplorerClient
from pdf_report_generator import PDFReportGenerator
from cli_report_generator import print_console_report


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
    
    # Extract year if present
    for separator in ['2024', '2023', '2025', '-', ' ']:
        if separator in month_input:
            parts = month_input.replace('-', ' ').replace('2024', ' 2024').replace('2023', ' 2023').replace('2025', ' 2025').split()
            if len(parts) == 2:
                month_str = parts[0]
                try:
                    year = int(parts[1])
                except ValueError:
                    pass
            break
    
    # Month name mappings
    month_names = {
        'jan': 1, 'january': 1,
        'feb': 2, 'february': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'september': 9, 'sept': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12
    }
    
    if month_str not in month_names:
        available_months = ', '.join(sorted(month_names.keys()))
        raise click.BadParameter(f"Invalid month '{month_str}'. Available: {available_months}")
    
    month_num = month_names[month_str]
    
    # Get first and last day of the month
    start_date = datetime(year, month_num, 1)
    last_day = calendar.monthrange(year, month_num)[1]
    end_date = datetime(year, month_num, last_day)
    
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
                total_data = result.get('Total', {})
                
                # Use NetAmortizedCost only
                total_cost_str = total_data.get('NetAmortizedCost', {}).get('Amount', '0')
                
                try:
                    total += float(total_cost_str)
                except ValueError:
                    continue
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



@click.command()
@click.option('--month', '-m', 
              help='Month for cost analysis (jan, feb, march, etc.). Can include year (jan2024, feb-2024). Defaults to current month.')
@click.option('--output', '-o', default='cost_report.pdf', 
              help='Output PDF filename. Default: cost_report.pdf')
@click.option('--profile', help='AWS profile to use. Uses default profile if not specified.')
@click.option('--region', default='us-east-1', help='AWS region. Default: us-east-1')
def cli(month, output, profile, region):
    """Extract AWS cost data for a specific month and generate comprehensive PDF report.
    
    Examples:
    \b
        costrecon --month jan                 # January of current year
        costrecon --month january2024         # January 2024
        costrecon --month feb-2024            # February 2024
        costrecon -m dec                      # December of current year
        costrecon                             # Current month
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

        # Fetch RDS coverage data for selected month
        click.echo("Fetching RDS Reserved Instance coverage...")
        try:
            rds_coverage = cost_client_selected_month.get_RDS_coverage()
        except Exception as e:
            click.echo(f"  Warning: {str(e)}")
            rds_coverage = {}
        report_raw_data.append(rds_coverage)
        
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

        # Generate PDF report
        click.echo("Generating PDF report...")
        pdf_generator = PDFReportGenerator()
        pdf_generator.generate_report(report_raw_data, output, start_date, end_date)
        
        click.echo(f"✓ Report generated successfully: {output}")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
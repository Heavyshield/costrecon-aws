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
        # Initialize AWS Cost Explorer client
        parameters = {
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
        cost_client = CostExplorerClient(profile=profile, region=region, parameters=parameters)
        
        # Report raw_data
        report_raw_data = []

        # Fetch cost data
        click.echo("Fetching cost data from AWS Cost Explorer...")
        cost_data = cost_client.get_cost_and_usage()
        report_raw_data.append(cost_data)

        # Fetch total savings
        click.echo("Fetching total savings from AWS Cost Explorer...")
        total_savings = cost_client.get_total_savings()
        report_raw_data.append(total_savings)

        # Fetch saving plan coverage 
        click.echo("Fetching saving plan coverage from AWS Cost Explorer...")
        sp_coverage = cost_client.get_saving_plan_coverage()
        report_raw_data.append(sp_coverage)

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
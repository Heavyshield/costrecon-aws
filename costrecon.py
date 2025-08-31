"""Main CLI entry point for CostRecon."""

import click
from datetime import datetime, timedelta
from aws_client import CostExplorerClient
from pdf_generator import PDFReportGenerator


@click.command()
@click.option('--start-date', type=click.DateTime(formats=['%Y-%m-%d']), 
              help='Start date for cost analysis (YYYY-MM-DD). Defaults to 30 days ago.')
@click.option('--end-date', type=click.DateTime(formats=['%Y-%m-%d']), 
              help='End date for cost analysis (YYYY-MM-DD). Defaults to today.')
@click.option('--output', '-o', default='cost_report.pdf', 
              help='Output PDF filename. Default: cost_report.pdf')
@click.option('--profile', help='AWS profile to use. Uses default profile if not specified.')
@click.option('--region', default='us-east-1', help='AWS region. Default: us-east-1')
def cli(start_date, end_date, output, profile, region):
    """Extract AWS cost data and generate PDF report."""
    
    # Set default dates if not provided
    if not end_date:
        end_date = datetime.now()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    click.echo(f"Generating cost report from {start_date.date()} to {end_date.date()}")
    click.echo(f"Output file: {output}")
    
    try:
        # Initialize AWS Cost Explorer client
        cost_client = CostExplorerClient(profile=profile, region=region)
        
        # Fetch cost data
        click.echo("Fetching cost data from AWS Cost Explorer...")
        cost_data = cost_client.get_cost_and_usage(start_date, end_date)
        
        # Generate PDF report
        click.echo("Generating PDF report...")
        pdf_generator = PDFReportGenerator()
        pdf_generator.generate_report(cost_data, output, start_date, end_date)
        
        click.echo(f"✓ Report generated successfully: {output}")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
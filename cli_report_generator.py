"""CLI console report generator for CostRecon."""

import click


def print_console_report(report_data, start_date, end_date):
    """Print formatted cost report to console."""
    click.echo("\n" + "="*80)
    click.echo("AWS COST RECONNAISSANCE REPORT".center(80))
    click.echo("="*80)
    click.echo(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    click.echo("="*80)
    
    # Parse report data (expecting list with cost_data, total_savings, sp_coverage)
    cost_data = report_data[0] if len(report_data) > 0 else {}
    total_savings = report_data[1] if len(report_data) > 1 else {}
    sp_coverage = report_data[2] if len(report_data) > 2 else {}
    
    # Cost Summary
    click.echo("\n📊 COST SUMMARY")
    click.echo("-" * 40)
    
    total_cost = 0.0
    service_costs = {}
    
    if 'cost_data' in cost_data:
        for result in cost_data['cost_data'].get('ResultsByTime', []):
            for group in result.get('Groups', []):
                service_name = group.get('Keys', ['Unknown'])[0]
                amount = float(group.get('Metrics', {}).get('BlendedCost', {}).get('Amount', '0'))
                total_cost += amount
                
                if service_name in service_costs:
                    service_costs[service_name] += amount
                else:
                    service_costs[service_name] = amount
    
    click.echo(f"Total Cost: ${total_cost:.2f}")
    
    # Top services by cost
    if service_costs:
        click.echo("\nTop Services by Cost:")
        sorted_services = sorted(service_costs.items(), key=lambda x: x[1], reverse=True)[:10]
        for service, cost in sorted_services:
            percentage = (cost / total_cost * 100) if total_cost > 0 else 0
            click.echo(f"  • {service[:40]:<40} ${cost:>8.2f} ({percentage:>5.1f}%)")
    
    # Savings Summary
    click.echo("\n💰 SAVINGS SUMMARY")
    click.echo("-" * 40)
    
    if 'total_savings' in total_savings:
        total_amount = total_savings.get('total_savings', 0)
        click.echo(f"Total Monthly Savings: ${total_amount:.2f}")
        
        savings_breakdown = [
            ("Savings Plans", total_savings.get('savings_plans', 0)),
            ("EC2 Reservations", total_savings.get('ec2_reservations', 0)),
            ("RDS Reservations", total_savings.get('rds_reservations', 0)),
            ("OpenSearch Reservations", total_savings.get('opensearch_reservations', 0)),
            ("MAP/Rightsizing", total_savings.get('map_savings', 0))
        ]
        
        click.echo("\nSavings Breakdown:")
        for source, amount in savings_breakdown:
            if amount > 0:
                percentage = (amount / total_amount * 100) if total_amount > 0 else 0
                click.echo(f"  • {source:<25} ${amount:>8.2f} ({percentage:>5.1f}%)")
        
        if total_savings.get('errors'):
            click.echo("\n⚠️  Savings Collection Errors:")
            for error in total_savings.get('errors', []):
                click.echo(f"  • {error}")
    
    # Coverage Summary
    click.echo("\n📈 SAVINGS PLANS COVERAGE")
    click.echo("-" * 40)
    
    if 'average_coverage_percentage' in sp_coverage:
        coverage_pct = sp_coverage.get('average_coverage_percentage', 0)
        click.echo(f"Average Coverage: {coverage_pct:.1f}%")
        
        if coverage_pct < 70:
            click.echo("  ⚠️  Coverage below recommended 70% threshold")
        elif coverage_pct >= 90:
            click.echo("  ✅ Excellent coverage!")
        else:
            click.echo("  ✅ Good coverage")
    
    # Additional metrics
    if total_cost > 0 and 'total_savings' in total_savings:
        savings_rate = (total_savings.get('total_savings', 0) / total_cost * 100)
        click.echo(f"\n📊 OPTIMIZATION METRICS")
        click.echo("-" * 40)
        click.echo(f"Cost Optimization Rate: {savings_rate:.1f}%")
        click.echo(f"Potential Monthly Savings: ${total_savings.get('total_savings', 0):.2f}")
        click.echo(f"Annualized Savings: ${total_savings.get('total_savings', 0) * 12:.2f}")
    
    click.echo("\n" + "="*80)
    click.echo("Report complete. PDF generation will follow...")
    click.echo("="*80 + "\n")
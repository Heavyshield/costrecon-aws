"""CLI console report generator for CostRecon."""

import click


def print_console_report(report_data, start_date, end_date):
    """Print formatted cost report to console."""
    click.echo("\n" + "="*80)
    click.echo("AWS COST RECONNAISSANCE REPORT".center(80))
    click.echo("="*80)
    click.echo(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    click.echo("="*80)
    
    # Parse report data (expecting list with cost_data, total_savings, sp_coverage_with_trend, rds_coverage)
    cost_data = report_data[0] if len(report_data) > 0 else {}
    total_savings = report_data[1] if len(report_data) > 1 else {}
    sp_coverage_with_trend = report_data[2] if len(report_data) > 2 else {}
    rds_coverage = report_data[3] if len(report_data) > 3 else {}
    
    # Extract current month coverage for backward compatibility
    sp_coverage = sp_coverage_with_trend.get('selected_month', {}) if sp_coverage_with_trend else {}
    
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
        click.echo(f"Current Month Coverage: {coverage_pct:.1f}%")
        
        if coverage_pct < 70:
            click.echo("  ⚠️  Coverage below recommended 70% threshold")
        elif coverage_pct >= 90:
            click.echo("  ✅ Excellent coverage!")
        else:
            click.echo("  ✅ Good coverage")
    
    # Quarterly Trend Analysis
    if sp_coverage_with_trend and 'trend_analysis' in sp_coverage_with_trend:
        trend_data = sp_coverage_with_trend['trend_analysis']
        
        click.echo("\n📊 3-MONTH SAVINGS PLAN TREND")
        click.echo("-" * 40)
        
        # Display coverage values for all 3 months
        coverage_values = trend_data.get('coverage_values', [])
        coverage_labels = trend_data.get('coverage_labels', [])
        
        if len(coverage_values) == 3:
            click.echo("Monthly Coverage Progression:")
            for i, (label, value) in enumerate(zip(coverage_labels, coverage_values)):
                arrow = ""
                if i > 0 and coverage_values[i-1] > 0 and value > 0:
                    change = value - coverage_values[i-1]
                    if change > 1.0:
                        arrow = " ↗️"
                    elif change < -1.0:
                        arrow = " ↘️"
                    else:
                        arrow = " ➡️"
                click.echo(f"  • {label:<15} {value:>6.1f}%{arrow}")
        
        # Display trend summary
        click.echo(f"\nQuarterly Change: {trend_data.get('quarterly_change', 0):.1f}%")
        click.echo(f"Trend Direction: {trend_data.get('trend_direction', 'unknown').title()}")
        click.echo(f"Trend Strength: {trend_data.get('trend_strength', 'unknown').title()}")
        
        # Display trend summary message
        summary = trend_data.get('summary', '')
        if summary:
            click.echo(f"\n💡 Trend Analysis:")
            click.echo(f"   {summary}")
        
        # Month-to-month changes
        month_changes = trend_data.get('month_to_month_changes', [])
        if month_changes:
            click.echo(f"\nMonth-to-Month Changes:")
            for change in month_changes:
                direction = "↗️" if change['change'] > 0 else "↘️" if change['change'] < 0 else "➡️"
                click.echo(f"  • {change['from_month']} → {change['to_month']}: {change['change']:+.1f}% {direction}")
    else:
        click.echo("\n📊 3-MONTH SAVINGS PLAN TREND")
        click.echo("-" * 40)
        click.echo("Trend analysis not available - insufficient data")
    
    # RDS Coverage Summary
    click.echo("\n🗄️  RDS RESERVED INSTANCES COVERAGE")
    click.echo("-" * 40)
    
    if rds_coverage and 'average_hours_coverage_percentage' in rds_coverage:
        hours_coverage = rds_coverage.get('average_hours_coverage_percentage', 0)
        cost_coverage = rds_coverage.get('average_cost_coverage_percentage', 0)
        utilization = rds_coverage.get('average_utilization_percentage', 0)
        
        click.echo(f"Hours Coverage: {hours_coverage:.1f}%")
        click.echo(f"Cost Coverage: {cost_coverage:.1f}%")
        click.echo(f"Utilization Rate: {utilization:.1f}%")
        
        if hours_coverage < 50:
            click.echo("  ⚠️  Low RDS Reserved Instance coverage - consider purchasing RIs")
        elif hours_coverage >= 80:
            click.echo("  ✅ Excellent RDS Reserved Instance coverage!")
        else:
            click.echo("  ✅ Good RDS Reserved Instance coverage")
        
        if utilization < 70:
            click.echo("  ⚠️  Low utilization - review instance sizing")
        elif utilization >= 90:
            click.echo("  ✅ Excellent utilization of Reserved Instances!")
        else:
            click.echo("  ✅ Good utilization of Reserved Instances")
    else:
        click.echo("No RDS Reserved Instance data available")
    
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
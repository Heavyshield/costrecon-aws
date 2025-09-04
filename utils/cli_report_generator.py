"""CLI console report generator for CostRecon."""

import click
from constants import REPORT_WIDTH, SECTION_SEPARATOR


def print_console_report(report_data, start_date, end_date):
    """Print formatted cost report to console.
    
    Args:
        report_data: List containing [cost_data, total_savings, sp_coverage_with_trend, 
                    rds_coverage, quarterly_costs, budget_anomalies]
        start_date: Report period start date (datetime object)
        end_date: Report period end date (datetime object)
    """
    click.echo("\n" + SECTION_SEPARATOR)
    click.echo("AWS COST RECONNAISSANCE REPORT".center(REPORT_WIDTH))
    click.echo(SECTION_SEPARATOR)
    click.echo(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    click.echo(SECTION_SEPARATOR)
    
    # Parse report data (expecting list with cost_data, total_savings, sp_coverage_with_trend, rds_coverage, quarterly_costs, budget_anomalies)
    cost_data = report_data[0] if len(report_data) > 0 else {}
    total_savings = report_data[1] if len(report_data) > 1 else {}
    sp_coverage_with_trend = report_data[2] if len(report_data) > 2 else {}
    rds_coverage = report_data[3] if len(report_data) > 3 else {}
    quarterly_costs = report_data[4] if len(report_data) > 4 else {}
    budget_anomalies = report_data[5] if len(report_data) > 5 else {}
    
    # Extract current month coverage for backward compatibility
    sp_coverage = sp_coverage_with_trend.get('selected_month', {}) if sp_coverage_with_trend else {}
    
    # 1. EXECUTIVE SUMMARY
    click.echo("\n🎯 EXECUTIVE SUMMARY")
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
    
    quarterly_total = quarterly_costs.get('quarterly_total_cost', 0.0) if quarterly_costs else 0.0
    total_savings_amount = total_savings.get('total_savings', 0.0)
    
    # Get month name from start_date
    month_name = start_date.strftime('%B %Y') if start_date else "Selected Month"
    
    click.echo(f"{month_name} Cost: ${total_cost:.2f}")
    click.echo(f"Quarterly Total (3 months): ${quarterly_total:.2f}")
    click.echo(f"Monthly Savings: ${total_savings_amount:.2f}")
    if total_cost > 0:
        optimization_rate = (total_savings_amount / total_cost * 100)
        click.echo(f"Cost Optimization Rate: {optimization_rate:.1f}%")
    
    # 2. SAVINGS PLAN COVERAGE/UTILIZATION
    click.echo("\n📈 SAVINGS PLAN COVERAGE/UTILIZATION")
    click.echo("-" * 40)
    
    if 'average_coverage_percentage' in sp_coverage:
        coverage_pct = sp_coverage.get('average_coverage_percentage', 0)
        utilization_pct = sp_coverage.get('average_utilization_percentage', 0)
        
        click.echo(f"Coverage: {coverage_pct:.1f}%")
        click.echo(f"Utilization Rate: {utilization_pct:.1f}%")
        
        if coverage_pct < 70:
            click.echo("  ⚠️  Coverage below recommended 70% threshold")
        elif coverage_pct >= 90:
            click.echo("  ✅ Excellent coverage!")
        else:
            click.echo("  ✅ Good coverage")
            
        if utilization_pct < 70:
            click.echo("  ⚠️  Low utilization - review Savings Plans sizing")
        elif utilization_pct >= 90:
            click.echo("  ✅ Excellent utilization of Savings Plans!")
        else:
            click.echo("  ✅ Good utilization of Savings Plans")
    
    # 3-Month Trend Analysis (part of Savings Plan Coverage)
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
    else:
        click.echo("\n📊 3-MONTH SAVINGS PLAN TREND")
        click.echo("-" * 40)
        click.echo("Trend analysis not available - insufficient data")
    
    # 3. RDS RESERVED INSTANCES COVERAGE/UTILIZATION
    click.echo("\n🗄️  RDS RESERVED INSTANCES COVERAGE/UTILIZATION")
    click.echo("-" * 40)
    
    if rds_coverage and 'average_hours_coverage_percentage' in rds_coverage:
        hours_coverage = rds_coverage.get('average_hours_coverage_percentage', 0)
        utilization = rds_coverage.get('average_utilization_percentage', 0)
        
        click.echo(f"Hours Coverage: {hours_coverage:.1f}%")
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
    
    # 4. SAVINGS SUMMARY
    click.echo("\n💰 SAVINGS SUMMARY")
    click.echo("-" * 40)
    
    if 'total_savings' in total_savings:
        total_amount = total_savings.get('total_savings', 0)
        click.echo(f"Total Monthly Savings: ${total_amount:.2f}")
        
        savings_breakdown = [
            ("Savings Plans", total_savings.get('savings_plans', 0)),
            ("RDS Reservations", total_savings.get('rds_reservations', 0)),
            ("OpenSearch Reservations", total_savings.get('opensearch_reservations', 0)),
            ("Credit Savings", total_savings.get('credit_savings', 0))
        ]
        
        click.echo("\nSavings Breakdown:")
        for source, amount in savings_breakdown:
            # Always show Savings Plans and Credit Savings, show others only if amount > 0
            if amount > 0 or source in ["Savings Plans", "Credit Savings"]:
                percentage = (amount / total_amount * 100) if total_amount > 0 else 0
                click.echo(f"  • {source:<25} ${amount:>8.2f} ({percentage:>5.1f}%)")
        
        if total_savings.get('errors'):
            click.echo("\n⚠️  Savings Collection Errors:")
            for error in total_savings.get('errors', []):
                click.echo(f"  • {error}")
    
    # 5. MONTHLY COMPARISON
    # Get month names for comparison
    from dateutil.relativedelta import relativedelta
    current_month = start_date.strftime('%B %Y') if start_date else "Selected Month"
    previous_month = (start_date - relativedelta(months=1)).strftime('%B %Y') if start_date else "Previous Month"
    
    click.echo(f"\n💰 {current_month.upper()} COST VS {previous_month.upper()}")
    click.echo("-" * 40)
    
    if quarterly_costs:
        selected_month_cost = quarterly_costs.get('selected_month_cost', 0.0)
        month_minus_one_cost = quarterly_costs.get('month_minus_one_cost', 0.0)
        
        # Calculate month-over-month change
        mom_change = 0.0
        mom_percentage = 0.0
        if month_minus_one_cost > 0:
            mom_change = selected_month_cost - month_minus_one_cost
            mom_percentage = (mom_change / month_minus_one_cost) * 100
        
        click.echo(f"{current_month} Cost: ${selected_month_cost:.2f}")
        click.echo(f"{previous_month} Cost: ${month_minus_one_cost:.2f}")
        click.echo(f"Month-over-Month Change: ${mom_change:.2f}")
        click.echo(f"Change Percentage: {mom_percentage:+.1f}%")
        
        trend = "Increasing" if mom_change > 0 else "Decreasing" if mom_change < 0 else "Stable"
        click.echo(f"Trend: {trend}")
    else:
        click.echo("No monthly comparison data available")
    
    # 6. QUARTERLY COST SUMMARY
    click.echo("\n📊 QUARTERLY COST SUMMARY (3 MONTHS)")
    click.echo("-" * 40)
    
    if quarterly_costs:
        selected_month_cost = quarterly_costs.get('selected_month_cost', 0.0)
        month_one_cost = quarterly_costs.get('month_minus_one_cost', 0.0) 
        month_two_cost = quarterly_costs.get('month_minus_two_cost', 0.0)
        quarterly_total_cost = quarterly_costs.get('quarterly_total_cost', 0.0)
        
        # Get actual month names for quarterly display
        month_0_name = start_date.strftime('%b %Y') if start_date else "Selected Month"
        month_1_name = (start_date - relativedelta(months=1)).strftime('%b %Y') if start_date else "Month -1"
        month_2_name = (start_date - relativedelta(months=2)).strftime('%b %Y') if start_date else "Month -2"
        
        click.echo(f"{month_0_name:<12}: ${selected_month_cost:.2f}")
        click.echo(f"{month_1_name:<12}: ${month_one_cost:.2f}")
        click.echo(f"{month_2_name:<12}: ${month_two_cost:.2f}")
        click.echo(f"Quarter Total: ${quarterly_total_cost:.2f}")
        
        if quarterly_total_cost > 0:
            avg_monthly = quarterly_total_cost / 3
            click.echo(f"Average Monthly: ${avg_monthly:.2f}")
            
            # Cost trend analysis
            if selected_month_cost > 0 and month_one_cost > 0 and month_two_cost > 0:
                overall_change = ((selected_month_cost - month_two_cost) / month_two_cost) * 100
                if overall_change > 5:
                    trend = f"Increasing ({overall_change:+.1f}% growth)"
                elif overall_change < -5:
                    trend = f"Decreasing ({overall_change:+.1f}% decline)"
                else:
                    trend = f"Stable ({overall_change:+.1f}% change)"
                click.echo(f"Quarterly Trend: {trend}")
    else:
        click.echo("No quarterly cost data available")
    
    # 7. BUDGET ANOMALIES
    click.echo("\n🚨 BUDGET ANOMALIES ANALYSIS")
    click.echo("-" * 40)
    
    if budget_anomalies and 'anomaly_budgets' in budget_anomalies:
        anomaly_budgets = budget_anomalies.get('anomaly_budgets', [])
        total_checked = budget_anomalies.get('total_budgets_checked', 0)
        anomalies_found = budget_anomalies.get('anomalies_found', 0)
        threshold = budget_anomalies.get('threshold_percentage', 10.0)
        
        click.echo(f"Total Budgets Checked: {total_checked}")
        click.echo(f"Anomalies Found: {anomalies_found}")
        click.echo(f"Threshold Used: {threshold}%")
        
        if anomaly_budgets:
            click.echo(f"Budget Health: ⚠️  REQUIRES ATTENTION")
            click.echo("\nBudget Anomalies Details:")
            
            for budget in anomaly_budgets:
                budget_name = budget.get('budget_name', 'Unknown')
                budget_limit = budget.get('budget_limit', 0)
                actual_amount = budget.get('actual_amount', 0)
                above_target = budget.get('actual_above_target', 0)
                above_target_pct = budget.get('actual_above_target_percentage', 0)
                severity = budget.get('severity', 'LOW')
                currency = budget.get('currency', 'USD')
                
                # Severity emoji
                severity_emoji = {
                    'CRITICAL': '🔴',
                    'HIGH': '🟠', 
                    'MEDIUM': '🟡',
                    'LOW': '🟢'
                }.get(severity, '⚪')
                
                click.echo(f"\n  • {budget_name}")
                click.echo(f"    Budget Limit:     {currency} {budget_limit:,.2f}")
                click.echo(f"    Actual Amount:    {currency} {actual_amount:,.2f}")
                click.echo(f"    Above Target:     {currency} {above_target:,.2f} ({above_target_pct:+.1f}%)")
                click.echo(f"    Severity:         {severity_emoji} {severity}")
            
            # Count by severity
            critical_count = len([b for b in anomaly_budgets if b.get('severity') == 'CRITICAL'])
            high_count = len([b for b in anomaly_budgets if b.get('severity') == 'HIGH'])
            
            click.echo("\n💡 Recommendations:")
            if critical_count > 0:
                click.echo(f"  • {critical_count} budget(s) in CRITICAL state - immediate attention required")
            if high_count > 0:
                click.echo(f"  • {high_count} budget(s) in HIGH state - review spending patterns")
            
            if critical_count == 0 and high_count == 0:
                click.echo("  • Monitor budget trends closely to prevent future overages")
            
            click.echo("  • Consider adjusting budget limits or implementing cost controls")
        else:
            click.echo("Budget Health: ✅ GOOD")
            click.echo("All budgets are within acceptable thresholds")
        
        # Show errors if any
        errors = budget_anomalies.get('errors', [])
        if errors:
            click.echo("\n⚠️  Budget Analysis Errors:")
            for error in errors:
                click.echo(f"  • {error}")
                
    else:
        click.echo("No budget data available - Budget analysis requires AWS Budgets to be configured")
    
    # 8. SERVICE ANOMALIES (Work in Progress)
    click.echo("\n🔍 SERVICE ANOMALIES ANALYSIS")
    click.echo("-" * 40)
    click.echo("🚧 This section is currently under development.")
    click.echo("Future functionality will include:")
    click.echo("  • Detection of unusual service cost spikes")
    click.echo("  • Identification of new or discontinued services")
    click.echo("  • Analysis of service cost patterns and trends")
    click.echo("  • Recommendations for cost optimization opportunities")
    
    click.echo("\n" + SECTION_SEPARATOR)
    click.echo("Report complete. PDF generation will follow...")
    click.echo(SECTION_SEPARATOR + "\n")
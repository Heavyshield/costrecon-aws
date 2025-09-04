"""AWS Budget anomalies functionality."""

import boto3
from typing import Dict
from botocore.exceptions import ClientError
from .base import BaseAWSClient


class BudgetMixin:
    """Mixin class for budget-related AWS functionality."""
    
    def get_budgets_anomalies(self, threshold: float = 10.0) -> Dict:
        """Get budgets where forecasted costs are above threshold percentage of target budget.
        
        Args:
            threshold: Percentage threshold above budget limit to flag as anomaly (default: 10%)
        
        Returns:
            Dictionary containing budget anomalies with target and forecast values
        """
        try:
            # Get account ID for budgets API calls
            sts_client = boto3.client('sts')
            account_id = sts_client.get_caller_identity()['Account']
            
            # Get all budgets
            budgets_response = self.budgets_client.describe_budgets(
                AccountId=account_id
            )
            
            budget_anomalies = {
                'anomaly_budgets': [],
                'total_budgets_checked': 0,
                'anomalies_found': 0,
                'threshold_percentage': threshold,
                'period': {
                    'start': self.start_date,
                    'end': self.end_date
                },
                'errors': []
            }
            
            for budget in budgets_response.get('Budgets', []):
                budget_anomalies['total_budgets_checked'] += 1
                budget_name = budget.get('BudgetName', 'Unknown')
                
                try:
                    # Get budget performance (actual and forecasted costs)
                    performance_response = self.budgets_client.describe_budget_performance_history(
                        AccountId=account_id,
                        BudgetName=budget_name,
                        TimePeriod={
                            'Start': self.start_date,
                            'End': self.end_date
                        }
                    )
                    
                    # Extract budget limit
                    budget_limit = 0.0
                    if 'BudgetLimit' in budget:
                        budget_limit = float(budget['BudgetLimit'].get('Amount', '0'))
                    
                    # Get latest performance data
                    performance_history = performance_response.get('BudgetPerformanceHistory', {})
                    budget_performance = performance_history.get('BudgetedAndActualAmountsList', [])
                    
                    if budget_performance:
                        latest_performance = budget_performance[-1]  # Most recent period
                        
                        # Extract forecasted amount
                        forecasted_amount = 0.0
                        if 'BudgetedAmount' in latest_performance:
                            forecasted_amount = float(latest_performance['BudgetedAmount'].get('Amount', '0'))
                        
                        # Extract actual amount
                        actual_amount = 0.0
                        if 'ActualAmount' in latest_performance:
                            actual_amount = float(latest_performance['ActualAmount'].get('Amount', '0'))
                        
                        # Calculate if forecast exceeds threshold
                        if budget_limit > 0:
                            threshold_amount = budget_limit * (1 + threshold / 100)
                            forecast_percentage = (forecasted_amount / budget_limit) * 100 if budget_limit > 0 else 0
                            actual_percentage = (actual_amount / budget_limit) * 100 if budget_limit > 0 else 0
                            
                            # Calculate amounts above target budget
                            actual_above_target = max(actual_amount - budget_limit, 0)
                            forecast_above_target = max(forecasted_amount - budget_limit, 0)
                            
                            # Calculate percentages above target
                            actual_above_target_pct = ((actual_amount - budget_limit) / budget_limit * 100) if budget_limit > 0 and actual_amount > budget_limit else 0
                            forecast_above_target_pct = ((forecasted_amount - budget_limit) / budget_limit * 100) if budget_limit > 0 and forecasted_amount > budget_limit else 0
                            
                            # Check if forecast exceeds threshold
                            if forecasted_amount > threshold_amount or actual_amount > threshold_amount:
                                budget_anomalies['anomaly_budgets'].append({
                                    'budget_name': budget_name,
                                    'budget_limit': budget_limit,
                                    'actual_amount': actual_amount,
                                    'forecasted_amount': forecasted_amount,
                                    'actual_percentage': round(actual_percentage, 2),
                                    'forecast_percentage': round(forecast_percentage, 2),
                                    'actual_above_target': round(actual_above_target, 2),
                                    'forecast_above_target': round(forecast_above_target, 2),
                                    'actual_above_target_percentage': round(actual_above_target_pct, 2),
                                    'forecast_above_target_percentage': round(forecast_above_target_pct, 2),
                                    'threshold_exceeded': forecasted_amount > threshold_amount or actual_amount > threshold_amount,
                                    'excess_amount': round(max(forecasted_amount - budget_limit, actual_amount - budget_limit, 0), 2),
                                    'budget_type': budget.get('BudgetType', 'COST'),
                                    'time_unit': budget.get('TimeUnit', 'MONTHLY'),
                                    'currency': budget.get('BudgetLimit', {}).get('Unit', 'USD'),
                                    'severity': self._calculate_budget_severity(actual_above_target_pct, forecast_above_target_pct, threshold)
                                })
                                budget_anomalies['anomalies_found'] += 1
                    
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    if error_code == 'AccessDeniedException':
                        budget_anomalies['errors'].append(f"Budget '{budget_name}': Access denied to budget performance data")
                    else:
                        budget_anomalies['errors'].append(f"Budget '{budget_name}': {e.response['Error']['Message']}")
                except Exception as e:
                    budget_anomalies['errors'].append(f"Budget '{budget_name}': {str(e)}")
            
            return budget_anomalies
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':
                raise Exception("Access denied. Please ensure your AWS credentials have Budgets permissions (budgets:DescribeBudgets, budgets:DescribeBudgetPerformanceHistory)")
            else:
                raise Exception(f"AWS Budgets API Error: {e.response['Error']['Message']}")
        except Exception as e:
            raise Exception(f"Failed to fetch budget anomalies: {str(e)}")
    
    def _calculate_budget_severity(self, actual_above_pct: float, forecast_above_pct: float, threshold: float) -> str:
        """Calculate severity level of budget anomaly.
        
        Args:
            actual_above_pct: Percentage actual amount is above budget
            forecast_above_pct: Percentage forecast amount is above budget
            threshold: Configured threshold percentage
        
        Returns:
            Severity level: 'CRITICAL', 'HIGH', 'MEDIUM', or 'LOW'
        """
        max_overage = max(actual_above_pct, forecast_above_pct)
        
        if max_overage >= threshold * 3:  # 3x threshold
            return 'CRITICAL'
        elif max_overage >= threshold * 2:  # 2x threshold
            return 'HIGH'
        elif max_overage >= threshold:  # At threshold
            return 'MEDIUM'
        else:
            return 'LOW'
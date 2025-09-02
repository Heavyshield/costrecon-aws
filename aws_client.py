"""AWS Cost Explorer client for fetching cost data."""

import boto3
from datetime import datetime
from typing import Dict, List, Optional
from botocore.exceptions import ClientError, NoCredentialsError
from constants import AWS_SERVICES, SERVICE_DISPLAY_NAMES, DEFAULT_REGION, DEFAULT_GRANULARITY, COST_METRICS


class CostExplorerClient:
    """Client for interacting with AWS Cost Explorer API."""
    
    def __init__(self, profile: Optional[str] = None, region: str = DEFAULT_REGION, parameters: Optional[Dict] = None):
        """Initialize the Cost Explorer client.
        
        Args:
            profile: AWS profile name to use
            region: AWS region
            parameters: Dict containing start_date, end_date, and optional budgets
        """
        try:
            if profile:
                session = boto3.Session(profile_name=profile)
                self.client = session.client('ce', region_name=region)
                self.budgets_client = session.client('budgets', region_name=region)
            else:
                self.client = boto3.client('ce', region_name=region)
                self.budgets_client = boto3.client('budgets', region_name=region)
        except NoCredentialsError:
            raise Exception("AWS credentials not found. Please configure your AWS credentials.")
        except Exception as e:
            raise Exception(f"Failed to initialize AWS client: {str(e)}")
        
        # start and end dates are mandatory and used often so init them within class
        if parameters and 'start_date' in parameters and 'end_date' in parameters:
            self.start_date = parameters["start_date"]
            self.end_date = parameters["end_date"]
        else:
            raise Exception("start_date and end_date must be provided in parameters")
    
    def _get_time_period(self) -> Dict[str, str]:
        """Get formatted time period dict for API calls.
        
        Returns:
            Dictionary with Start and End keys formatted for AWS API
        """
        return {
            'Start': self.start_date.strftime('%Y-%m-%d'),
            'End': self.end_date.strftime('%Y-%m-%d')
        }
    
    def get_saving_plan_coverage(self) -> Dict:
        """Get average Savings Plan coverage for the selected period.
        
        Returns:
            Dictionary containing Savings Plan coverage data
        """
        try:
            response = self.client.get_savings_plans_coverage(
                TimePeriod=self._get_time_period(),
                Granularity=DEFAULT_GRANULARITY
            )
            
            # Calculate average coverage percentage
            total_coverage = 0.0
            total_periods = 0
            
            for result in response.get('SavingsPlansCoverages', []):
                coverage_percentage = float(result.get('Coverage', {}).get('CoveragePercentage', '0'))
                total_coverage += coverage_percentage
                total_periods += 1
            
            average_coverage = total_coverage / total_periods if total_periods > 0 else 0.0
            
            return {
                'average_coverage_percentage': round(average_coverage, 2),
                'detailed_coverage': response.get('SavingsPlansCoverages', []),
                'period': {
                    'start': self.start_date,
                    'end': self.end_date
                }
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            if error_code == 'AccessDenied':
                raise Exception("Access denied. Please ensure your AWS credentials have Savings Plans permissions.")
            elif error_code == 'DataUnavailableException':
                raise Exception(f"No Savings Plans coverage data available for period {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
            elif error_code == 'InvalidParameterValueException':
                raise Exception(f"Invalid date range for Savings Plans coverage: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')} - {error_message}")
            else:
                raise Exception(f"AWS API Error ({error_code}): {error_message}")
        except Exception as e:
            raise Exception(f"Failed to fetch Savings Plan coverage: {str(e)}")
        
    def get_RDS_coverage(self) -> Dict:
        """Get RDS Reserved Instance coverage for the selected period.
        
        Returns:
            Dictionary containing RDS RI coverage data including utilization,
            coverage percentage, and on-demand costs that could be covered
        """
        try:
            # Get RDS coverage without groupBy since we're filtering to RDS only
            response = self.client.get_reservation_coverage(
                TimePeriod={
                    'Start': self.start_date.strftime('%Y-%m-%d'),
                    'End': self.end_date.strftime('%Y-%m-%d')
                },
                Filter={
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': [AWS_SERVICES['RDS']]
                    }
                },
                Granularity=DEFAULT_GRANULARITY
            )
            
            # Calculate average coverage percentages
            total_hours_coverage = 0.0
            total_cost_coverage = 0.0
            total_periods = 0
            coverage_details = []
            
            for result in response.get('CoveragesByTime', []):
                period_start = result.get('TimePeriod', {}).get('Start', '')
                period_end = result.get('TimePeriod', {}).get('End', '')
                
                # Extract coverage data from Total (since we're not grouping)
                coverage = result.get('Total', {})
                
                hours_coverage = float(coverage.get('CoverageHours', {}).get('CoverageHoursPercentage', '0'))
                cost_coverage = float(coverage.get('CoverageCost', {}).get('CoverageCostPercentage', '0'))
                
                total_hours_coverage += hours_coverage
                total_cost_coverage += cost_coverage
                total_periods += 1
                
                coverage_details.append({
                    'period_start': period_start,
                    'period_end': period_end,
                    'hours_coverage_percentage': round(hours_coverage, 2),
                    'cost_coverage_percentage': round(cost_coverage, 2),
                    'coverage_hours': coverage.get('CoverageHours', {}),
                    'coverage_cost': coverage.get('CoverageCost', {})
                })
            
            # Calculate averages
            avg_hours_coverage = total_hours_coverage / total_periods if total_periods > 0 else 0.0
            avg_cost_coverage = total_cost_coverage / total_periods if total_periods > 0 else 0.0
            
            # Get additional RDS utilization data (without groupBy)
            utilization_response = self.client.get_reservation_utilization(
                TimePeriod={
                    'Start': self.start_date.strftime('%Y-%m-%d'),
                    'End': self.end_date.strftime('%Y-%m-%d')
                },
                Filter={
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': [AWS_SERVICES['RDS']]
                    }
                },
                Granularity=DEFAULT_GRANULARITY
            )
            
            utilization_details = []
            total_utilization = 0.0
            utilization_periods = 0
            
            for result in utilization_response.get('UtilizationsByTime', []):
                # Extract utilization from Total (since we're not grouping)
                utilization = result.get('Total', {})
                utilization_percentage = float(utilization.get('UtilizationPercentage', '0'))
                
                total_utilization += utilization_percentage
                utilization_periods += 1
                
                utilization_details.append({
                    'period_start': result.get('TimePeriod', {}).get('Start', ''),
                    'period_end': result.get('TimePeriod', {}).get('End', ''),
                    'utilization_percentage': round(utilization_percentage, 2),
                    'purchased_hours': utilization.get('PurchasedHours', '0'),
                    'used_hours': utilization.get('UsedHours', '0'),
                    'total_actual_hours': utilization.get('TotalActualHours', '0')
                })
            
            avg_utilization = total_utilization / utilization_periods if utilization_periods > 0 else 0.0
            
            return {
                'average_hours_coverage_percentage': round(avg_hours_coverage, 2),
                'average_cost_coverage_percentage': round(avg_cost_coverage, 2),
                'average_utilization_percentage': round(avg_utilization, 2),
                'detailed_coverage': coverage_details,
                'detailed_utilization': utilization_details,
                'period': {
                    'start': self.start_date,
                    'end': self.end_date
                },
                'service': AWS_SERVICES['RDS']
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDenied':
                raise Exception("Access denied. Please ensure your AWS credentials have RDS Reserved Instance permissions.")
            else:
                raise Exception(f"AWS API Error: {e.response['Error']['Message']}")
        except Exception as e:
            raise Exception(f"Failed to fetch RDS coverage data: {str(e)}")
    
    def get_sp_savings(self) -> Dict:
        """Get Savings Plans savings for the selected period.
        
        Returns:
            Dictionary containing Savings Plans savings data
        """
        try:
            response = self.client.get_savings_plans_utilization(
                TimePeriod=self._get_time_period(),
                Granularity=DEFAULT_GRANULARITY
            )
            
            total_savings = 0.0
            utilization_details = []
            
            for result in response.get('SavingsPlansUtilizationsByTime', []):
                savings_amount = float(result.get('Savings', {}).get('NetSavings', '0'))
                total_savings += savings_amount
                
                utilization_details.append({
                    'period_start': result.get('TimePeriod', {}).get('Start', ''),
                    'period_end': result.get('TimePeriod', {}).get('End', ''),
                    'net_savings': round(savings_amount, 2),
                    'utilization_percentage': float(result.get('Utilization', {}).get('UtilizationPercentage', '0')),
                    'total_commitment': result.get('Utilization', {}).get('TotalCommitment', '0'),
                    'used_commitment': result.get('Utilization', {}).get('UsedCommitment', '0')
                })
            
            return {
                'total_savings': round(total_savings, 2),
                'detailed_utilization': utilization_details,
                'period': {
                    'start': self.start_date,
                    'end': self.end_date
                },
                'service_type': 'Savings Plans'
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'DataUnavailableException':
                return {
                    'total_savings': 0.0,
                    'detailed_utilization': [],
                    'period': {'start': self.start_date, 'end': self.end_date},
                    'service_type': 'Savings Plans',
                    'error': 'No Savings Plans data available for this period'
                }
            else:
                raise Exception(f"AWS API Error: {e.response['Error']['Message']}")
        except Exception as e:
            raise Exception(f"Failed to fetch Savings Plans savings: {str(e)}")
    
    def _get_reservation_savings(self, service_name: str, service_display_name: str) -> Dict:
        """Generic method to get Reserved Instance savings for any service.
        
        Args:
            service_name: AWS service name for API filter
            service_display_name: Display name for response
            
        Returns:
            Dictionary containing RI savings data
        """
        try:
            response = self.client.get_reservation_utilization(
                TimePeriod=self._get_time_period(),
                Filter={
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': [service_name]
                    }
                },
                Granularity=DEFAULT_GRANULARITY
            )
            
            total_savings = 0.0
            utilization_details = []
            
            for result in response.get('UtilizationsByTime', []):
                savings_amount = float(result.get('Total', {}).get('NetRISavings', '0'))
                total_savings += savings_amount
                
                utilization_details.append({
                    'period_start': result.get('TimePeriod', {}).get('Start', ''),
                    'period_end': result.get('TimePeriod', {}).get('End', ''),
                    'net_savings': round(savings_amount, 2),
                    'utilization_percentage': float(result.get('Total', {}).get('UtilizationPercentage', '0')),
                    'purchased_hours': result.get('Total', {}).get('PurchasedHours', '0'),
                    'used_hours': result.get('Total', {}).get('UsedHours', '0')
                })
            
            return {
                'total_savings': round(total_savings, 2),
                'detailed_utilization': utilization_details,
                'period': {
                    'start': self.start_date,
                    'end': self.end_date
                },
                'service_type': service_display_name
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ValidationException':
                return {
                    'total_savings': 0.0,
                    'detailed_utilization': [],
                    'period': {'start': self.start_date, 'end': self.end_date},
                    'service_type': service_display_name,
                    'error': f'No {service_display_name} found'
                }
            else:
                raise Exception(f"AWS API Error: {e.response['Error']['Message']}")
        except Exception as e:
            raise Exception(f"Failed to fetch {service_display_name} savings: {str(e)}")
    
    def get_rds_savings(self) -> Dict:
        """Get RDS Reserved Instance savings for the selected period.
        
        Returns:
            Dictionary containing RDS RI savings data
        """
        return self._get_reservation_savings(
            AWS_SERVICES['RDS'], 
            SERVICE_DISPLAY_NAMES['RDS']
        )
    
    def get_os_savings(self) -> Dict:
        """Get OpenSearch Reserved Instance savings for the selected period.
        
        Returns:
            Dictionary containing OpenSearch RI savings data
        """
        return self._get_reservation_savings(
            AWS_SERVICES['OPENSEARCH'], 
            SERVICE_DISPLAY_NAMES['OPENSEARCH']
        )
    
    def get_total_savings(self) -> Dict:
        """Get total savings from all AWS cost optimization services.
        Uses individual service functions for better modularity.
        
        Returns:
            Dictionary containing total savings breakdown with detailed data
        """
        savings_breakdown = {
            'savings_plans': 0.0,
            'rds_reservations': 0.0, 
            'opensearch_reservations': 0.0,
            'total_savings': 0.0,
            'period': {
                'start': self.start_date,
                'end': self.end_date
            },
            'detailed_savings': {},
            'errors': []
        }
        
        # 1. Get Savings Plans savings
        try:
            sp_data = self.get_sp_savings()
            savings_breakdown['savings_plans'] = sp_data['total_savings']
            savings_breakdown['detailed_savings']['savings_plans'] = sp_data
            if 'error' in sp_data:
                savings_breakdown['errors'].append(f"Savings Plans: {sp_data['error']}")
        except Exception as e:
            savings_breakdown['errors'].append(f"Savings Plans: {str(e)}")
        
        # 2. Get RDS Reserved Instance savings
        try:
            rds_data = self.get_rds_savings()
            savings_breakdown['rds_reservations'] = rds_data['total_savings']
            savings_breakdown['detailed_savings']['rds_reservations'] = rds_data
            if 'error' in rds_data:
                savings_breakdown['errors'].append(f"RDS Reservations: {rds_data['error']}")
        except Exception as e:
            savings_breakdown['errors'].append(f"RDS Reservations: {str(e)}")
        
        # 3. Get OpenSearch Reserved Instance savings
        try:
            os_data = self.get_os_savings()
            savings_breakdown['opensearch_reservations'] = os_data['total_savings']
            savings_breakdown['detailed_savings']['opensearch_reservations'] = os_data
            if 'error' in os_data:
                savings_breakdown['errors'].append(f"OpenSearch Reservations: {os_data['error']}")
        except Exception as e:
            savings_breakdown['errors'].append(f"OpenSearch Reservations: {str(e)}")
        
        # Calculate total savings
        total = (savings_breakdown['savings_plans'] + 
                savings_breakdown['rds_reservations'] +
                savings_breakdown['opensearch_reservations'])
        
        savings_breakdown['total_savings'] = round(total, 2)
        
        return savings_breakdown

    def get_cost_and_usage(self) -> Dict:
        """Fetch cost and usage data from AWS Cost Explorer.
        Uses class-level start_date and end_date.
        Returns cost data with SERVICE grouping using configured metrics.
        
        Returns:
            Dictionary containing cost and usage data
        """
        try:
            response = self.client.get_cost_and_usage(
                TimePeriod=self._get_time_period(),
                Granularity='DAILY',
                Metrics=COST_METRICS,
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    }
                ]
            )
            
            # Also get dimension values for services
            services_response = self.client.get_dimension_values(
                TimePeriod={
                    'Start': self.start_date.strftime('%Y-%m-%d'),
                    'End': self.end_date.strftime('%Y-%m-%d')
                },
                Dimension='SERVICE'
            )
            
            return {
                'cost_data': response,
                'services': services_response,
                'period': {
                    'start': self.start_date,
                    'end': self.end_date
                }
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDenied':
                raise Exception("Access denied. Please ensure your AWS credentials have Cost Explorer permissions.")
            else:
                raise Exception(f"AWS API Error: {e.response['Error']['Message']}")
        except Exception as e:
            raise Exception(f"Failed to fetch cost data: {str(e)}")
    
    def get_monthly_costs(self) -> Dict:
        """Get monthly cost breakdown.
        Uses class-level start_date and end_date.
        
        Returns:
            Dictionary containing monthly cost data
        """
        try:
            response = self.client.get_cost_and_usage(
                TimePeriod=self._get_time_period(),
                Granularity=DEFAULT_GRANULARITY,
                Metrics=['BlendedCost']
            )
            
            return response
            
        except Exception as e:
            raise Exception(f"Failed to fetch monthly costs: {str(e)}")
    
    def get_service_costs(self) -> List[Dict]:
        """Get cost breakdown by service.
        Uses class-level start_date and end_date.
        
        Returns:
            List of service cost data
        """
        try:
            response = self.client.get_cost_and_usage(
                TimePeriod=self._get_time_period(),
                Granularity=DEFAULT_GRANULARITY,
                Metrics=COST_METRICS,
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    }
                ]
            )
            
            return response.get('ResultsByTime', [])
            
        except Exception as e:
            raise Exception(f"Failed to fetch service costs: {str(e)}")

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
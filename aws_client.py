"""AWS Cost Explorer client for fetching cost data."""

import boto3
from datetime import datetime
from typing import Dict, List, Optional
from botocore.exceptions import ClientError, NoCredentialsError


class CostExplorerClient:
    """Client for interacting with AWS Cost Explorer API."""
    
    def __init__(self, profile: Optional[str] = None, region: str = 'eu-west-1', parameters: Optional[Dict] = None):
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
            else:
                self.client = boto3.client('ce', region_name=region)
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
    
    def get_saving_plan_coverage(self) -> Dict:
        """Get average Savings Plan coverage for the selected period.
        
        Returns:
            Dictionary containing Savings Plan coverage data
        """
        try:
            response = self.client.get_savings_plans_coverage(
                TimePeriod={
                    'Start': self.start_date.strftime('%Y-%m-%d'),
                    'End': self.end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY'
            )
            
            # Calculate average coverage percentage
            total_coverage = 0.0
            total_periods = 0
            
            for result in response.get('SavingsPlansUtilizations', []):
                coverage_percentage = float(result.get('Coverage', {}).get('CoverageHoursPercentage', '0'))
                total_coverage += coverage_percentage
                total_periods += 1
            
            average_coverage = total_coverage / total_periods if total_periods > 0 else 0.0
            
            return {
                'average_coverage_percentage': round(average_coverage, 2),
                'detailed_coverage': response.get('SavingsPlansUtilizations', []),
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
                        'Values': ['Amazon Relational Database Service']
                    }
                },
                Granularity='MONTHLY'
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
                        'Values': ['Amazon Relational Database Service']
                    }
                },
                Granularity='MONTHLY'
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
                'service': 'Amazon Relational Database Service'
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDenied':
                raise Exception("Access denied. Please ensure your AWS credentials have RDS Reserved Instance permissions.")
            else:
                raise Exception(f"AWS API Error: {e.response['Error']['Message']}")
        except Exception as e:
            raise Exception(f"Failed to fetch RDS coverage data: {str(e)}")
    
    def get_total_savings(self) -> Dict:
        """Get total savings from all AWS cost optimization services.
        
        Aggregates savings from:
        1. Savings Plans utilization
        2. RDS Reserved Instances  
        3. OpenSearch Reserved Instances
        4. EC2 Reserved Instances
        5. MAP (Migration Acceleration Program) savings
        
        Returns:
            Dictionary containing total savings breakdown
        """
        savings_breakdown = {
            'savings_plans': 0.0,
            'rds_reservations': 0.0, 
            'opensearch_reservations': 0.0,
            'ec2_reservations': 0.0,
            'map_savings': 0.0,
            'total_savings': 0.0,
            'period': {
                'start': self.start_date,
                'end': self.end_date
            },
            'errors': []
        }
        
        # 1. Get Savings Plans utilization and savings
        try:
            sp_response = self.client.get_savings_plans_utilization(
                TimePeriod={
                    'Start': self.start_date.strftime('%Y-%m-%d'),
                    'End': self.end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY'
            )
            
            sp_savings = 0.0
            for result in sp_response.get('SavingsPlansUtilizations', []):
                savings_amount = float(result.get('Savings', {}).get('NetSavings', '0'))
                sp_savings += savings_amount
            
            savings_breakdown['savings_plans'] = round(sp_savings, 2)
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'DataUnavailableException':
                savings_breakdown['errors'].append("Savings Plans: No Savings Plans data available for this period")
            else:
                savings_breakdown['errors'].append(f"Savings Plans: {e.response['Error']['Message']}")
        except Exception as e:
            savings_breakdown['errors'].append(f"Savings Plans: {str(e)}")
        
        # 2. Get RDS Reserved Instance savings
        try:
            rds_response = self.client.get_reservation_utilization(
                TimePeriod={
                    'Start': self.start_date.strftime('%Y-%m-%d'),
                    'End': self.end_date.strftime('%Y-%m-%d')
                },
                Filter={
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': ['Amazon Relational Database Service']
                    }
                },
                Granularity='MONTHLY'
            )
            
            rds_savings = 0.0
            for result in rds_response.get('UtilizationsByTime', []):
                total_savings = result.get('Total', {}).get('NetRISavings', '0')
                rds_savings += float(total_savings)
            
            savings_breakdown['rds_reservations'] = round(rds_savings, 2)
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ValidationException':
                savings_breakdown['errors'].append("RDS Reservations: No RDS Reserved Instances found")
            else:
                savings_breakdown['errors'].append(f"RDS Reservations: {e.response['Error']['Message']}")
        except Exception as e:
            savings_breakdown['errors'].append(f"RDS Reservations: {str(e)}")
        
        # 3. Get OpenSearch Reserved Instance savings
        try:
            opensearch_response = self.client.get_reservation_utilization(
                TimePeriod={
                    'Start': self.start_date.strftime('%Y-%m-%d'),
                    'End': self.end_date.strftime('%Y-%m-%d')
                },
                Filter={
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': ['Amazon OpenSearch Service']
                    }
                },
                Granularity='MONTHLY'
            )
            
            opensearch_savings = 0.0
            for result in opensearch_response.get('UtilizationsByTime', []):
                total_savings = result.get('Total', {}).get('NetRISavings', '0')
                opensearch_savings += float(total_savings)
            
            savings_breakdown['opensearch_reservations'] = round(opensearch_savings, 2)
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ValidationException':
                savings_breakdown['errors'].append("OpenSearch Reservations: No OpenSearch Reserved Instances found")
            else:
                savings_breakdown['errors'].append(f"OpenSearch Reservations: {e.response['Error']['Message']}")
        except Exception as e:
            savings_breakdown['errors'].append(f"OpenSearch Reservations: {str(e)}")
        
        # 4. Get EC2 Reserved Instance savings
        try:
            ec2_response = self.client.get_reservation_utilization(
                TimePeriod={
                    'Start': self.start_date.strftime('%Y-%m-%d'),
                    'End': self.end_date.strftime('%Y-%m-%d')
                },
                Filter={
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': ['Amazon Elastic Compute Cloud - Compute']
                    }
                },
                Granularity='MONTHLY'
            )
            
            ec2_savings = 0.0
            for result in ec2_response.get('UtilizationsByTime', []):
                total_savings = result.get('Total', {}).get('NetRISavings', '0')
                ec2_savings += float(total_savings)
            
            savings_breakdown['ec2_reservations'] = round(ec2_savings, 2)
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ValidationException':
                savings_breakdown['errors'].append("EC2 Reservations: No EC2 Reserved Instances found")
            else:
                savings_breakdown['errors'].append(f"EC2 Reservations: {e.response['Error']['Message']}")
        except Exception as e:
            savings_breakdown['errors'].append(f"EC2 Reservations: {str(e)}")
        
        # 5. Get MAP savings (using rightsizing recommendations as proxy)
        try:
            rightsizing_response = self.client.get_rightsizing_recommendation(
                Service='EC2',
                Configuration={
                    'BenefitsConsidered': False,
                    'RecommendationTarget': 'SAME_INSTANCE_FAMILY'
                }
            )
            
            map_savings = 0.0
            for recommendation in rightsizing_response.get('RightsizingRecommendations', []):
                estimated_savings = float(
                    recommendation.get('EstimatedMonthlySavings', '0')
                )
                map_savings += estimated_savings
            
            savings_breakdown['map_savings'] = round(map_savings, 2)
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':
                savings_breakdown['errors'].append("MAP/Rightsizing: Feature not enabled - can be enabled in Cost Explorer Preferences")
            elif error_code == 'DataUnavailableException':
                savings_breakdown['errors'].append("MAP/Rightsizing: No rightsizing recommendations available yet (requires 24h+ data)")
            else:
                savings_breakdown['errors'].append(f"MAP/Rightsizing: {e.response['Error']['Message']}")
        except Exception as e:
            savings_breakdown['errors'].append(f"MAP/Rightsizing: {str(e)}")
        
        # Calculate total savings
        total = (savings_breakdown['savings_plans'] + 
                savings_breakdown['rds_reservations'] +
                savings_breakdown['opensearch_reservations'] + 
                savings_breakdown['ec2_reservations'] +
                savings_breakdown['map_savings'])
        
        savings_breakdown['total_savings'] = round(total, 2)
        
        return savings_breakdown

    def get_cost_and_usage(self) -> Dict:
        """Fetch cost and usage data from AWS Cost Explorer.
        Uses class-level start_date and end_date.
        
        Returns:
            Dictionary containing cost and usage data
        """
        try:
            response = self.client.get_cost_and_usage(
                TimePeriod={
                    'Start': self.start_date.strftime('%Y-%m-%d'),
                    'End': self.end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['BlendedCost', 'UnblendedCost', 'UsageQuantity'],
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
                TimePeriod={
                    'Start': self.start_date.strftime('%Y-%m-%d'),
                    'End': self.end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
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
                TimePeriod={
                    'Start': self.start_date.strftime('%Y-%m-%d'),
                    'End': self.end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['BlendedCost'],
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
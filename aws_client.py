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
            if error_code == 'AccessDenied':
                raise Exception("Access denied. Please ensure your AWS credentials have Savings Plans permissions.")
            else:
                raise Exception(f"AWS API Error: {e.response['Error']['Message']}")
        except Exception as e:
            raise Exception(f"Failed to fetch Savings Plan coverage: {str(e)}")
        
    # TODO
    def get_RDS_coverage(self) -> Dict:

        return 'todo'
    
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
            
        except Exception as e:
            savings_breakdown['errors'].append(f"Savings Plans: {str(e)}")
        
        # 2. Get RDS Reserved Instance savings
        try:
            rds_response = self.client.get_reservation_utilization(
                TimePeriod={
                    'Start': self.start_date.strftime('%Y-%m-%d'),
                    'End': self.end_date.strftime('%Y-%m-%d')
                },
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    }
                ],
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
                for group in result.get('Groups', []):
                    savings_amount = float(group.get('Attributes', {}).get('NetRISavings', '0'))
                    rds_savings += savings_amount
            
            savings_breakdown['rds_reservations'] = round(rds_savings, 2)
            
        except Exception as e:
            savings_breakdown['errors'].append(f"RDS Reservations: {str(e)}")
        
        # 3. Get OpenSearch Reserved Instance savings
        try:
            opensearch_response = self.client.get_reservation_utilization(
                TimePeriod={
                    'Start': self.start_date.strftime('%Y-%m-%d'),
                    'End': self.end_date.strftime('%Y-%m-%d')
                },
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    }
                ],
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
                for group in result.get('Groups', []):
                    savings_amount = float(group.get('Attributes', {}).get('NetRISavings', '0'))
                    opensearch_savings += savings_amount
            
            savings_breakdown['opensearch_reservations'] = round(opensearch_savings, 2)
            
        except Exception as e:
            savings_breakdown['errors'].append(f"OpenSearch Reservations: {str(e)}")
        
        # 4. Get EC2 Reserved Instance savings
        try:
            ec2_response = self.client.get_reservation_utilization(
                TimePeriod={
                    'Start': self.start_date.strftime('%Y-%m-%d'),
                    'End': self.end_date.strftime('%Y-%m-%d')
                },
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    }
                ],
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
                for group in result.get('Groups', []):
                    savings_amount = float(group.get('Attributes', {}).get('NetRISavings', '0'))
                    ec2_savings += savings_amount
            
            savings_breakdown['ec2_reservations'] = round(ec2_savings, 2)
            
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
"""AWS Cost Explorer client for fetching cost data."""

import boto3
from datetime import datetime
from typing import Dict, List, Optional
from botocore.exceptions import ClientError, NoCredentialsError


class CostExplorerClient:
    """Client for interacting with AWS Cost Explorer API."""
    
    def __init__(self, profile: Optional[str] = None, region: str = 'us-east-1'):
        """Initialize the Cost Explorer client.
        
        Args:
            profile: AWS profile name to use
            region: AWS region
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
    
    def get_cost_and_usage(self, start_date: datetime, end_date: datetime) -> Dict:
        """Fetch cost and usage data from AWS Cost Explorer.
        
        Args:
            start_date: Start date for the cost analysis
            end_date: End date for the cost analysis
            
        Returns:
            Dictionary containing cost and usage data
        """
        try:
            response = self.client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
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
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Dimension='SERVICE'
            )
            
            return {
                'cost_data': response,
                'services': services_response,
                'period': {
                    'start': start_date,
                    'end': end_date
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
    
    def get_monthly_costs(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get monthly cost breakdown.
        
        Args:
            start_date: Start date for the cost analysis
            end_date: End date for the cost analysis
            
        Returns:
            Dictionary containing monthly cost data
        """
        try:
            response = self.client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['BlendedCost']
            )
            
            return response
            
        except Exception as e:
            raise Exception(f"Failed to fetch monthly costs: {str(e)}")
    
    def get_service_costs(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get cost breakdown by service.
        
        Args:
            start_date: Start date for the cost analysis
            end_date: End date for the cost analysis
            
        Returns:
            List of service cost data
        """
        try:
            response = self.client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
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
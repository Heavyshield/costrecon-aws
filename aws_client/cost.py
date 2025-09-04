"""AWS Cost Explorer cost and usage functionality."""

from typing import Dict, List
from botocore.exceptions import ClientError
from constants import COST_METRICS, DEFAULT_GRANULARITY
from .base import BaseAWSClient


class CostMixin:
    """Mixin class for cost and usage-related AWS Cost Explorer functionality."""
    
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
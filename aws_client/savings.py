"""AWS Cost Explorer savings-related functionality."""

from typing import Dict
from botocore.exceptions import ClientError
from constants import AWS_SERVICES, SERVICE_DISPLAY_NAMES, DEFAULT_GRANULARITY
from .base import BaseAWSClient


class SavingsMixin:
    """Mixin class for savings-related AWS Cost Explorer functionality."""
    
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
    
    def get_credit_savings(self) -> Dict:
        """Get credit savings from all AWS credits for the selected period.
        
        Returns:
            Dictionary containing credit savings data
        """
        try:
            response = self.client.get_cost_and_usage(
                TimePeriod=self._get_time_period(),
                Granularity=DEFAULT_GRANULARITY,
                Metrics=['UNBLENDED_COST'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    },
                    {
                        'Type': 'DIMENSION',
                        'Key': 'USAGE_TYPE'
                    }
                ],
                Filter={
                    'Dimensions': {
                        'Key': 'RECORD_TYPE',
                        'Values': ['Credit']
                    }
                }
            )
            
            total_credit_savings = 0.0
            credit_details = []
            
            for result in response.get('ResultsByTime', []):
                period_start = result.get('TimePeriod', {}).get('Start', '')
                period_end = result.get('TimePeriod', {}).get('End', '')
                
                period_credit_total = 0.0
                
                for group in result.get('Groups', []):
                    # Extract service and usage type from Keys
                    keys = group.get('Keys', [])
                    service = keys[0] if len(keys) > 0 else 'Unknown'
                    usage_type = keys[1] if len(keys) > 1 else 'Unknown'
                    
                    # Get cost amounts (credits are typically negative values)
                    unblended_cost = abs(float(group.get('Metrics', {}).get('UnblendedCost', {}).get('Amount', '0')))
                    
                    # Use unblended cost as primary metric
                    credit_amount = unblended_cost
                    period_credit_total += credit_amount
                    
                    if credit_amount > 0:
                        credit_details.append({
                            'period_start': period_start,
                            'period_end': period_end,
                            'service': service,
                            'usage_type': usage_type,
                            'credit_amount': round(credit_amount, 2),
                            'unblended_cost': round(unblended_cost, 2)
                        })
                
                total_credit_savings += period_credit_total
            
            return {
                'total_savings': round(total_credit_savings, 2),
                'detailed_credits': credit_details,
                'period': {
                    'start': self.start_date,
                    'end': self.end_date
                },
                'charge_type': 'Credits'
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'DataUnavailableException':
                return {
                    'total_savings': 0.0,
                    'detailed_credits': [],
                    'period': {'start': self.start_date, 'end': self.end_date},
                    'charge_type': 'Credits',
                    'error': 'No credit data available for this period'
                }
            else:
                raise Exception(f"AWS API Error: {e.response['Error']['Message']}")
        except Exception as e:
            raise Exception(f"Failed to fetch credit savings: {str(e)}")
    
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
            'credit_savings': 0.0,
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
        
        # 4. Get Credit savings
        try:
            credit_data = self.get_credit_savings()
            savings_breakdown['credit_savings'] = credit_data['total_savings']
            savings_breakdown['detailed_savings']['credit_savings'] = credit_data
            if 'error' in credit_data:
                savings_breakdown['errors'].append(f"Credit Savings: {credit_data['error']}")
        except Exception as e:
            savings_breakdown['errors'].append(f"Credit Savings: {str(e)}")
        
        # Calculate total savings
        total = (savings_breakdown['savings_plans'] + 
                savings_breakdown['rds_reservations'] +
                savings_breakdown['opensearch_reservations'] +
                savings_breakdown['credit_savings'])
        
        savings_breakdown['total_savings'] = round(total, 2)
        
        return savings_breakdown
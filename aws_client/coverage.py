"""AWS Cost Explorer coverage and utilization functionality."""

from typing import Dict
from botocore.exceptions import ClientError
from constants import AWS_SERVICES, DEFAULT_GRANULARITY
from .base import BaseAWSClient


class CoverageMixin:
    """Mixin class for coverage/utilization-related AWS Cost Explorer functionality."""
    
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
"""Base AWS client with common functionality."""

import boto3
from datetime import datetime
from typing import Dict, Optional
from botocore.exceptions import ClientError, NoCredentialsError
from constants import DEFAULT_REGION


class BaseAWSClient:
    """Base client for AWS Cost Explorer API with common functionality."""
    
    def __init__(self, profile: Optional[str] = None, region: str = DEFAULT_REGION, parameters: Optional[Dict] = None):
        """Initialize the AWS client.
        
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
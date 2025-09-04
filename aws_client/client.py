"""Main AWS Cost Explorer client combining all functionality."""

from .base import BaseAWSClient
from .savings import SavingsMixin
from .coverage import CoverageMixin
from .budget import BudgetMixin
from .cost import CostMixin


class CostExplorerClient(BaseAWSClient, SavingsMixin, CoverageMixin, BudgetMixin, CostMixin):
    """Client for interacting with AWS Cost Explorer API.
    
    This class combines all the functionality from different mixins:
    - BaseAWSClient: Common AWS client initialization and utilities
    - SavingsMixin: Savings Plans, Reserved Instances, and Credit savings
    - CoverageMixin: Coverage and utilization analysis
    - BudgetMixin: Budget anomaly detection
    - CostMixin: Cost and usage data retrieval
    """
    
    def __init__(self, profile=None, region=None, parameters=None):
        """Initialize the Cost Explorer client.
        
        Args:
            profile: AWS profile name to use
            region: AWS region
            parameters: Dict containing start_date, end_date, and optional budgets
        """
        super().__init__(profile=profile, region=region, parameters=parameters)
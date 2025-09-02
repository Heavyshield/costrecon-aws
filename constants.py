"""Constants and configuration for CostRecon."""

# AWS Service names for API calls
AWS_SERVICES = {
    'RDS': 'Amazon Relational Database Service',
    'OPENSEARCH': 'Amazon OpenSearch Service',
    'EC2_COMPUTE': 'Amazon Elastic Compute Cloud - Compute'
}

# Report display names
SERVICE_DISPLAY_NAMES = {
    'RDS': 'RDS Reserved Instances',
    'OPENSEARCH': 'OpenSearch Reserved Instances'
}

# Month name mappings for CLI input
MONTH_MAPPINGS = {
    'jan': 1, 'january': 1,
    'feb': 2, 'february': 2,
    'mar': 3, 'march': 3,
    'apr': 4, 'april': 4,
    'may': 5,
    'jun': 6, 'june': 6,
    'jul': 7, 'july': 7,
    'aug': 8, 'august': 8,
    'sep': 9, 'september': 9,
    'oct': 10, 'october': 10,
    'nov': 11, 'november': 11,
    'dec': 12, 'december': 12
}

# Default configurations
DEFAULT_REGION = 'eu-west-1'
DEFAULT_GRANULARITY = 'MONTHLY'
COST_METRICS = ['BlendedCost']

# Report formatting
REPORT_WIDTH = 80
SECTION_SEPARATOR = "=" * REPORT_WIDTH
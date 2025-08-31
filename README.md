# CostRecon

AWS Cost Explorer data extraction and PDF reporting tool.

## Overview

CostRecon is a Python CLI application that connects to AWS Cost Explorer API to fetch cost and usage data, then generates comprehensive PDF reports. It's designed to help you analyze and visualize your AWS spending patterns.

## Features

- Extract cost data from AWS Cost Explorer API
- Generate professional PDF reports with cost breakdowns
- Support for custom date ranges
- Service-level cost analysis
- Daily and monthly cost trends
- Multiple output formats

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd costrecon
```

2. Install the package:
<Optional>
```bash
source .venv/bin/activate
```
```bash
pip install -e .
```

## Prerequisites

- Python 3.12+
- AWS credentials configured (via AWS CLI, environment variables, or IAM roles)
- AWS Cost Explorer API access permissions

## Usage

### Default Mode (Last 30 days)
```bash
costrecon
```

### Custom Date Range
```bash
costrecon --start-date 2024-01-01 --end-date 2024-01-31
```

### Specify Output File
```bash
costrecon --output my_cost_report.pdf
```

### Use Specific AWS Profile
```bash
costrecon --profile myprofile --region us-west-2
```

### All Options
```bash
costrecon --help
```

## AWS Permissions Required

Your AWS credentials need the following permissions:
- `ce:GetCostAndUsage`
- `ce:GetDimensionValues`

Example IAM policy:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ce:GetCostAndUsage",
                "ce:GetDimensionValues"
            ],
            "Resource": "*"
        }
    ]
}
```

## Development

Run locally during development:
```bash
python main.py
```

Install in development mode:
```bash
pip install -e .
```

## Dependencies

- **boto3**: AWS SDK for Python
- **click**: Command line interface creation
- **reportlab**: PDF generation
- **python-dateutil**: Date parsing utilities
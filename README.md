# CostRecon

AWS Cost Explorer data extraction and comprehensive reporting tool with 3-month trend analysis.

## Overview

CostRecon is a Python CLI application that connects to AWS Cost Explorer API to fetch comprehensive cost and usage data, then generates both console and PDF reports with advanced analytics. It provides deep insights into AWS spending patterns, cost optimization opportunities, and savings plan trends.

## Features

- **Month-based Analysis**: Simple month input (jan, feb, march) with automatic date calculation
- **Flexible Year Support**: Supports any year format (jan2026, feb-2030, etc.) with future-proof parsing
- **3-Month Trend Analysis**: Quarterly savings plan coverage trends with directional indicators
- **Comprehensive Cost Data**: Service breakdowns, total costs, and optimization metrics
- **Savings Analysis**: Detailed breakdown of Savings Plans, Reserved Instances, and MAP opportunities
- **Coverage Metrics**: Savings Plan and RDS Reserved Instance coverage analysis
- **Dual Output Options**: Choose between console-only reports or full PDF generation
- **Amazon Color Scheme**: Reports use official Amazon branding colors
- **Error Handling**: Graceful handling of missing data and AWS API limitations

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

### Current Month Analysis (Default)
```bash
python3 costrecon.py
```
Analyzes the current month with 3-month trend analysis (current month + 2 previous months).

### Specific Month Analysis
```bash
# January of current year
python3 costrecon.py --month jan

# Full month names work too
python3 costrecon.py --month january

# Specify year explicitly (supports any year)
python3 costrecon.py --month jan2024
python3 costrecon.py --month february-2026
python3 costrecon.py --month march-2030

# Previous months
python3 costrecon.py -m dec
```

### Custom Output and AWS Settings
```bash
# Specify output filename
python3 costrecon.py --month feb --output february_costs.pdf

# Use specific AWS profile and region
python3 costrecon.py --month jan --profile myprofile --region us-west-2

# Skip PDF generation (console report only)
python3 costrecon.py --month jan --no-pdf

# Get help
python3 costrecon.py --help
```

### Example Outputs

**Console Report Features:**
- 📊 Cost summary with service breakdowns
- 💰 Savings analysis (Savings Plans, Reserved Instances, MAP)
- 📈 3-month savings plan trend with directional arrows (↗️↘️➡️)
- 🗄️ RDS Reserved Instance coverage analysis
- 📊 Optimization metrics and recommendations

**PDF Report Includes:**
- Executive summary with key metrics
- Detailed savings breakdown tables
- 3-month trend analysis charts
- RDS coverage analysis
- Service breakdown details
- Professional Amazon-branded color scheme

**Output Options:**
- Default: Console report + PDF generation
- `--no-pdf`: Console report only (faster, no file output)

## AWS Permissions Required

Your AWS credentials need the following permissions for full functionality:

### Required Permissions:
- `ce:GetCostAndUsage` - Basic cost data
- `ce:GetDimensionValues` - Service information
- `ce:GetSavingsPlansUtilization` - Savings Plans data
- `ce:GetSavingsPlansUsage` - Savings Plans usage
- `ce:GetSavingsPlansCoverage` - Savings Plans coverage
- `ce:GetReservationUtilization` - Reserved Instance data
- `ce:GetReservationCoverage` - Reserved Instance coverage

### Optional Permissions (for MAP analysis):
- `ce:GetRightsizingRecommendation` - Rightsizing recommendations (requires opt-in)

### Example IAM Policy:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ce:GetCostAndUsage",
                "ce:GetDimensionValues",
                "ce:GetSavingsPlansUtilization",
                "ce:GetSavingsPlansUsage", 
                "ce:GetSavingsPlansCoverage",
                "ce:GetReservationUtilization",
                "ce:GetReservationCoverage",
                "ce:GetRightsizingRecommendation"
            ],
            "Resource": "*"
        }
    ]
}
```

**Note**: Some features like rightsizing recommendations require opt-in from the AWS Cost Explorer console and may take 24+ hours to generate initial data.

## Development

Run locally during development:
```bash
python3 costrecon.py --month jan
```

Install in development mode:
```bash
pip install -e .
```

## Project Structure

```
costrecon-aws/
├── costrecon.py              # Main CLI entry point with month parsing
├── aws_client.py             # AWS Cost Explorer API client
├── pdf_report_generator.py   # PDF generation with Amazon branding
├── cli_report_generator.py   # Console report formatting
├── pyproject.toml            # Project dependencies and metadata
└── README.md                 # This file
```

## Dependencies

- **boto3**: AWS SDK for Python (>=1.40.21)
- **click**: Command line interface creation (>=8.1.0)
- **reportlab**: PDF generation with Amazon colors (>=4.0.0)
- **python-dateutil**: Date parsing utilities (>=2.8.0)
- **calendar**: Python standard library for month calculations

## Troubleshooting

### Common Issues:

1. **"No Savings Plans data available"**: Your account may not have active Savings Plans
2. **"Feature not enabled"**: Rightsizing recommendations need to be enabled in Cost Explorer
3. **"Access denied"**: Check IAM permissions listed above
4. **Invalid month input**: Use formats like 'jan', 'january', 'jan2024', or 'feb-2024'

### Data Availability:
- Cost data: Available within 24 hours
- Savings Plans data: Available if you have active plans
- Reserved Instance data: Available if you have active RIs
- Rightsizing recommendations: Requires 24+ hours after opt-in
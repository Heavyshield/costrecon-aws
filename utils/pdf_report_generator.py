"""PDF report generator for AWS cost data."""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.flowables import HRFlowable
from datetime import datetime
from typing import Dict, List
from utils.report_helpers import (
    ReportDataParser,
    CostCalculations,
    StatusDetermination,
    TrendAnalysis,
    BudgetHelpers,
    DateFormatting,
    SavingsHelpers
)


class PDFReportGenerator:
    """Generates PDF reports from AWS cost data."""
    
    def __init__(self):
        """Initialize the PDF generator."""
        self.styles = getSampleStyleSheet()
        self.custom_styles = self._create_custom_styles()
        
        # Amazon color scheme
        self.amazon_orange = HexColor('#FF9900')
        self.amazon_dark_blue = HexColor('#232F3E')
        self.amazon_light_blue = HexColor('#5294E8')
        self.amazon_gray = HexColor('#EAEDED')
        self.amazon_dark_gray = HexColor('#687078')
    
    def _create_custom_styles(self) -> Dict:
        """Create custom paragraph styles."""
        styles = {}
        
        styles['CustomTitle'] = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Center alignment
            textColor=HexColor('#232F3E')  # Amazon dark blue
        )
        
        styles['SectionHeader'] = ParagraphStyle(
            'SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=HexColor('#FF9900')  # Amazon orange
        )
        
        styles['SubHeader'] = ParagraphStyle(
            'SubHeader',
            parent=self.styles['Heading3'],
            fontSize=14,
            spaceAfter=8,
            spaceBefore=12,
            textColor=HexColor('#232F3E')  # Amazon dark blue
        )
        
        return styles
    
    def generate_report(self, report_data: List[Dict], output_filename: str, 
                       start_date: datetime, end_date: datetime) -> None:
        """Generate a PDF report from complete report data.
        
        Args:
            report_data: Complete report data list [cost_data, total_savings, sp_coverage]
            output_filename: Output PDF filename
            start_date: Report start date
            end_date: Report end date
        """
        doc = SimpleDocTemplate(
            output_filename,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Parse report data using shared utility
        parsed_data = ReportDataParser.parse_report_data(report_data)
        cost_data = parsed_data['cost_data']
        total_savings = parsed_data['total_savings']
        sp_coverage_with_trend = parsed_data['sp_coverage_with_trend']
        rds_coverage_with_trend = parsed_data['rds_coverage_with_trend']
        quarterly_costs = parsed_data['quarterly_costs']
        budget_anomalies = parsed_data['budget_anomalies']

        # Extract current month coverage
        sp_coverage, rds_coverage = ReportDataParser.extract_current_month_coverage(
            sp_coverage_with_trend, rds_coverage_with_trend
        )
        
        story = []
        
        # Title page
        story.extend(self._create_title_page(start_date, end_date))
        
        # 1. Executive summary
        story.extend(self._create_executive_summary(cost_data, total_savings, quarterly_costs, start_date))
        
        # 2. Savings Plan Coverage/Utilization
        story.extend(self._create_coverage_summary(sp_coverage))
        story.extend(self._create_trend_analysis(sp_coverage_with_trend))

        # 3. RDS Reserved Instances Coverage/Utilization
        story.extend(self._create_rds_coverage_summary(rds_coverage))
        story.extend(self._create_rds_trend_analysis(rds_coverage_with_trend))
        
        # 4. Savings Summary (with total and breakdown)
        story.extend(self._create_savings_summary(total_savings, sp_coverage))
        
        # 5. Selected Month Cost vs Previous Month
        story.extend(self._create_monthly_comparison(cost_data, quarterly_costs, start_date))
        
        # 6. Quarterly Cost Summary
        story.extend(self._create_quarterly_cost_summary(quarterly_costs))
        
        # 7. Budget Anomalies
        story.extend(self._create_budget_anomalies_summary(budget_anomalies))
        
        # 8. Service Anomalies (Work in Progress)
        story.extend(self._create_service_anomalies_summary())
        
        
        # Build the PDF
        doc.build(story)
    
    def _create_title_page(self, start_date: datetime, end_date: datetime) -> List:
        """Create the title page."""
        story = []
        
        # Title
        title = Paragraph("AWS Cost Analysis Report", self.custom_styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 30))
        
        # Date range
        date_range = f"Period: {start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
        date_para = Paragraph(date_range, self.styles['Normal'])
        story.append(date_para)
        story.append(Spacer(1, 20))
        
        # Generation timestamp
        generated_at = f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
        gen_para = Paragraph(generated_at, self.styles['Normal'])
        story.append(gen_para)
        story.append(Spacer(1, 40))
        
        # Add horizontal line
        story.append(HRFlowable(width="100%", thickness=1, lineCap='round', 
                               color=self.amazon_orange, spaceBefore=20, spaceAfter=20))
        
        return story
    
    def _create_executive_summary(self, cost_data: Dict, total_savings: Dict, quarterly_costs: Dict, start_date: datetime = None) -> List:
        """Create executive summary section."""
        story = []
        
        story.append(Paragraph("Executive Summary", self.custom_styles['SectionHeader']))

        # Calculate total costs using shared utility
        total_cost = CostCalculations.calculate_total_cost(cost_data)
        quarterly_total = quarterly_costs.get('quarterly_total_cost', 0.0) if quarterly_costs else 0.0
        total_savings_amount = total_savings.get('total_savings', 0.0)

        # Get month name
        month_name = DateFormatting.get_month_name(start_date, 'full')

        # Calculate optimization rate
        optimization_rate = CostCalculations.calculate_optimization_rate(total_savings_amount, total_cost)

        summary_data = [
            [f"{month_name} Cost", f"${total_cost:.2f}"],
            ["Quarterly Total Cost (3 months)", f"${quarterly_total:.2f}"],
            ["Monthly Savings", f"${total_savings_amount:.2f}"],
            ["Cost Optimization Rate", f"{optimization_rate:.1f}%" if total_cost > 0 else "N/A"],
            ["Report Period", f"{(cost_data['period']['end'] - cost_data['period']['start']).days} days" if cost_data.get('period') else "N/A"]
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.amazon_orange),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), self.amazon_gray),
            ('GRID', (0, 0), (-1, -1), 1, self.amazon_dark_gray)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        return story
    
    def _create_savings_summary(self, total_savings: Dict, sp_coverage: Dict = None) -> List:
        """Create savings summary section."""
        story = []
        
        story.append(Paragraph("Savings Summary", self.custom_styles['SectionHeader']))
        
        if not total_savings or 'total_savings' not in total_savings:
            story.append(Paragraph("No savings data available.", self.styles['Normal']))
            story.append(Spacer(1, 20))
            return story
        
        # Savings breakdown table
        savings_data = [["Savings Source", "Monthly Amount", "Percentage"]]
        total_amount = total_savings.get('total_savings', 0)
        
        savings_items = [
            ("Savings Plans", total_savings.get('savings_plans', 0)),
            ("RDS Reservations", total_savings.get('rds_reservations', 0)),
            ("OpenSearch Reservations", total_savings.get('opensearch_reservations', 0)),
            ("Credit Savings", total_savings.get('credit_savings', 0))
        ]
        
        for source, amount in savings_items:
            # Use shared helper to determine if item should be displayed
            if SavingsHelpers.should_display_savings_item(source, amount):
                percentage = SavingsHelpers.calculate_savings_percentage(amount, total_amount)
                savings_data.append([source, f"${amount:.2f}", f"{percentage:.1f}%"])
        
        # Add total row
        savings_data.append(["TOTAL", f"${total_amount:.2f}", "100.0%"])
        
        savings_table = Table(savings_data, colWidths=[2.5*inch, 1.5*inch, 1*inch])
        savings_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.amazon_dark_blue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), self.amazon_gray),
            ('BACKGROUND', (0, -1), (-1, -1), self.amazon_light_blue),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, self.amazon_dark_gray)
        ]))
        
        story.append(savings_table)
        story.append(Spacer(1, 10))
        
        # Add errors if any
        if total_savings.get('errors'):
            story.append(Paragraph("Savings Collection Errors:", self.custom_styles['SubHeader']))
            for error in total_savings.get('errors', []):
                story.append(Paragraph(f"• {error}", self.styles['Normal']))
            story.append(Spacer(1, 10))
        
        story.append(Spacer(1, 20))
        return story
    
    def _create_coverage_summary(self, sp_coverage: Dict) -> List:
        """Create savings plans coverage summary section."""
        story = []
        
        story.append(Paragraph("Savings Plans Coverage", self.custom_styles['SectionHeader']))
        
        if not sp_coverage or 'average_coverage_percentage' not in sp_coverage:
            story.append(Paragraph("No Savings Plans coverage data available.", self.styles['Normal']))
            story.append(Spacer(1, 20))
            return story
        
        coverage_pct = sp_coverage.get('average_coverage_percentage', 0)
        utilization_pct = sp_coverage.get('average_utilization_percentage', 0)
        
        coverage_data = [
            ["Metric", "Value"],
            ["Average Coverage", f"{coverage_pct:.1f}%"],
            ["Utilization Rate", f"{utilization_pct:.1f}%"],
            ["Coverage Status", self._get_coverage_status(coverage_pct)]
        ]
        
        coverage_table = Table(coverage_data, colWidths=[2*inch, 3*inch])
        coverage_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.amazon_light_blue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), self.amazon_gray),
            ('GRID', (0, 0), (-1, -1), 1, self.amazon_dark_gray),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ]))
        
        story.append(coverage_table)
        story.append(Spacer(1, 20))
        
        return story
    
    def _get_coverage_status(self, coverage_pct: float) -> str:
        """Get coverage status based on percentage."""
        return StatusDetermination.get_coverage_status(coverage_pct)
    
    
    def _create_trend_analysis(self, sp_coverage_with_trend: Dict) -> List:
        """Create savings plans trend analysis section."""
        story = []
        
        story.append(Paragraph("3-Month Savings Plan Trend Analysis", self.custom_styles['SectionHeader']))
        
        if not sp_coverage_with_trend or 'trend_analysis' not in sp_coverage_with_trend:
            story.append(Paragraph("Trend analysis not available - insufficient data.", self.styles['Normal']))
            story.append(Spacer(1, 20))
            return story
        
        trend_data = sp_coverage_with_trend['trend_analysis']
        coverage_values = trend_data.get('coverage_values', [])
        coverage_labels = trend_data.get('coverage_labels', [])
        
        # Monthly progression table
        if len(coverage_values) == 3:
            progression_data = [["Month", "Coverage %", "Change from Previous"]]
            
            for i, (label, value) in enumerate(zip(coverage_labels, coverage_values)):
                change_text = "N/A"
                if i > 0 and coverage_values[i-1] > 0 and value > 0:
                    change = value - coverage_values[i-1]
                    change_text = f"{change:+.1f}%"
                
                progression_data.append([label, f"{value:.1f}%", change_text])
            
            progression_table = Table(progression_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
            progression_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.amazon_orange),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), self.amazon_gray),
                ('GRID', (0, 0), (-1, -1), 1, self.amazon_dark_gray)
            ]))
            
            story.append(progression_table)
            story.append(Spacer(1, 15))
        
        # Trend summary table
        quarterly_change = trend_data.get('quarterly_change', 0)
        trend_direction = trend_data.get('trend_direction', 'unknown').title()
        trend_strength = trend_data.get('trend_strength', 'unknown').title()
        
        summary_data = [
            ["Metric", "Value"],
            ["Quarterly Change", f"{quarterly_change:+.1f}%"],
            ["Trend Direction", trend_direction],
            ["Trend Strength", trend_strength]
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.amazon_dark_blue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), self.amazon_gray),
            ('GRID', (0, 0), (-1, -1), 1, self.amazon_dark_gray)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 15))
        
        # Trend summary message
        summary_message = trend_data.get('summary', '')
        if summary_message:
            story.append(Paragraph("Trend Summary:", self.custom_styles['SubHeader']))
            story.append(Paragraph(summary_message, self.styles['Normal']))
        
        story.append(Spacer(1, 20))
        return story
    
    def _create_rds_coverage_summary(self, rds_coverage: Dict) -> List:
        """Create RDS Reserved Instance coverage summary section."""
        story = []
        
        story.append(Paragraph("RDS Reserved Instances Coverage", self.custom_styles['SectionHeader']))
        
        if not rds_coverage or 'average_hours_coverage_percentage' not in rds_coverage:
            story.append(Paragraph("No RDS Reserved Instance coverage data available.", self.styles['Normal']))
            story.append(Spacer(1, 20))
            return story
        
        hours_coverage = rds_coverage.get('average_hours_coverage_percentage', 0)
        utilization = rds_coverage.get('average_utilization_percentage', 0)
        
        coverage_data = [
            ["Metric", "Value", "Status"],
            ["Hours Coverage", f"{hours_coverage:.1f}%", self._get_coverage_status(hours_coverage)],
            ["Utilization Rate", f"{utilization:.1f}%", self._get_utilization_status(utilization)]
        ]
        
        coverage_table = Table(coverage_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        coverage_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.amazon_orange),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), self.amazon_gray),
            ('GRID', (0, 0), (-1, -1), 1, self.amazon_dark_gray)
        ]))
        
        story.append(coverage_table)
        story.append(Spacer(1, 15))
        
        # Recommendations
        recommendations = []
        if hours_coverage < 50:
            recommendations.append("Consider purchasing RDS Reserved Instances to reduce costs")
        if utilization < 70:
            recommendations.append("Review RDS instance sizing - low utilization detected")
        if not recommendations:
            recommendations.append("RDS Reserved Instance coverage and utilization are optimal")
        
        story.append(Paragraph("Recommendations:", self.custom_styles['SubHeader']))
        for rec in recommendations:
            story.append(Paragraph(f"• {rec}", self.styles['Normal']))
        
        story.append(Spacer(1, 20))
        return story
    
    def _get_utilization_status(self, utilization_pct: float) -> str:
        """Get utilization status based on percentage."""
        return StatusDetermination.get_utilization_status(utilization_pct)

    def _create_rds_trend_analysis(self, rds_coverage_with_trend: Dict) -> List:
        """Create RDS Reserved Instance trend analysis section."""
        story = []

        story.append(Paragraph("3-Month RDS Reserved Instance Trend Analysis", self.custom_styles['SectionHeader']))

        if not rds_coverage_with_trend or 'trend_analysis' not in rds_coverage_with_trend:
            story.append(Paragraph("Trend analysis not available - insufficient data.", self.styles['Normal']))
            story.append(Spacer(1, 20))
            return story

        trend_data = rds_coverage_with_trend['trend_analysis']
        coverage_values = trend_data.get('coverage_values', [])
        coverage_labels = trend_data.get('coverage_labels', [])

        # Monthly progression table
        if len(coverage_values) == 3:
            progression_data = [["Month", "Coverage %", "Change from Previous"]]

            for i, (label, value) in enumerate(zip(coverage_labels, coverage_values)):
                change_text = "N/A"
                if i > 0 and coverage_values[i-1] > 0 and value > 0:
                    change = value - coverage_values[i-1]
                    change_text = f"{change:+.1f}%"

                progression_data.append([label, f"{value:.1f}%", change_text])

            progression_table = Table(progression_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
            progression_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.amazon_orange),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), self.amazon_gray),
                ('GRID', (0, 0), (-1, -1), 1, self.amazon_dark_gray)
            ]))

            story.append(progression_table)
            story.append(Spacer(1, 15))

        # Trend summary table
        quarterly_change = trend_data.get('quarterly_change', 0)
        trend_direction = trend_data.get('trend_direction', 'unknown').title()
        trend_strength = trend_data.get('trend_strength', 'unknown').title()

        summary_data = [
            ["Metric", "Value"],
            ["Quarterly Change", f"{quarterly_change:+.1f}%"],
            ["Trend Direction", trend_direction],
            ["Trend Strength", trend_strength]
        ]

        summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.amazon_dark_blue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), self.amazon_gray),
            ('GRID', (0, 0), (-1, -1), 1, self.amazon_dark_gray)
        ]))

        story.append(summary_table)
        story.append(Spacer(1, 15))

        # Trend summary message
        summary_message = trend_data.get('summary', '')
        if summary_message:
            story.append(Paragraph("Trend Summary:", self.custom_styles['SubHeader']))
            story.append(Paragraph(summary_message, self.styles['Normal']))

        story.append(Spacer(1, 20))
        return story

    def _calculate_total_cost(self, cost_data: Dict) -> float:
        """Calculate total cost from cost data."""
        return CostCalculations.calculate_total_cost(cost_data)
    
    def _create_quarterly_cost_summary(self, quarterly_costs: Dict) -> List:
        """Create quarterly cost summary section."""
        story = []
        
        story.append(Paragraph("Quarterly Cost Summary (3 Months)", self.custom_styles['SectionHeader']))
        
        if not quarterly_costs:
            story.append(Paragraph("No quarterly cost data available.", self.styles['Normal']))
            story.append(Spacer(1, 20))
            return story
        
        selected_month = quarterly_costs.get('selected_month_cost', 0.0)
        month_minus_one = quarterly_costs.get('month_minus_one_cost', 0.0)
        month_minus_two = quarterly_costs.get('month_minus_two_cost', 0.0)
        quarterly_total = quarterly_costs.get('quarterly_total_cost', 0.0)
        
        quarterly_data = [
            ["Period", "Cost", "% of Quarter"],
            ["Selected Month", f"${selected_month:.2f}", f"{(selected_month/quarterly_total*100):.1f}%" if quarterly_total > 0 else "0.0%"],
            ["Month -1", f"${month_minus_one:.2f}", f"{(month_minus_one/quarterly_total*100):.1f}%" if quarterly_total > 0 else "0.0%"],
            ["Month -2", f"${month_minus_two:.2f}", f"{(month_minus_two/quarterly_total*100):.1f}%" if quarterly_total > 0 else "0.0%"],
            ["QUARTERLY TOTAL", f"${quarterly_total:.2f}", "100.0%"]
        ]
        
        quarterly_table = Table(quarterly_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        quarterly_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.amazon_orange),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), self.amazon_gray),
            ('BACKGROUND', (0, -1), (-1, -1), self.amazon_dark_blue),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, self.amazon_dark_gray)
        ]))
        
        story.append(quarterly_table)
        story.append(Spacer(1, 15))

        # Add quarterly insights using shared utilities
        avg_monthly = CostCalculations.calculate_quarterly_average(quarterly_total)
        story.append(Paragraph("Quarterly Insights:", self.custom_styles['SubHeader']))
        story.append(Paragraph(f"• Average monthly cost: ${avg_monthly:.2f}", self.styles['Normal']))
        trend = TrendAnalysis.get_cost_trend(month_minus_two, month_minus_one, selected_month)
        story.append(Paragraph(f"• Quarterly spending trend: {trend}", self.styles['Normal']))
        
        story.append(Spacer(1, 20))
        return story
    
    def _get_cost_trend(self, oldest: float, middle: float, newest: float) -> str:
        """Analyze cost trend over three months."""
        return TrendAnalysis.get_cost_trend(oldest, middle, newest)
    
    def _create_monthly_comparison(self, cost_data: Dict, quarterly_costs: Dict, start_date: datetime = None) -> List:
        """Create monthly cost comparison section."""
        story = []
        
        # Get month names using shared utility
        current_month = DateFormatting.get_month_name(start_date, 'full')
        previous_month = DateFormatting.get_previous_month_name(start_date, 'full')

        story.append(Paragraph(f"{current_month} Cost vs {previous_month}", self.custom_styles['SectionHeader']))

        if not quarterly_costs:
            story.append(Paragraph("No monthly comparison data available.", self.styles['Normal']))
            story.append(Spacer(1, 20))
            return story

        selected_month_cost = quarterly_costs.get('selected_month_cost', 0.0)
        month_minus_one_cost = quarterly_costs.get('month_minus_one_cost', 0.0)

        # Calculate month-over-month change using shared utility
        mom_change, mom_percentage = CostCalculations.calculate_mom_change(
            selected_month_cost, month_minus_one_cost
        )

        # Get trend direction
        trend = TrendAnalysis.get_trend_direction_simple(selected_month_cost, month_minus_one_cost)

        comparison_data = [
            ["Metric", "Value"],
            [f"{current_month} Cost", f"${selected_month_cost:.2f}"],
            [f"{previous_month} Cost", f"${month_minus_one_cost:.2f}"],
            ["Month-over-Month Change", f"${mom_change:.2f}"],
            ["Change Percentage", f"{mom_percentage:+.1f}%"],
            ["Trend", trend]
        ]
        
        comparison_table = Table(comparison_data, colWidths=[2.5*inch, 2*inch])
        comparison_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.amazon_orange),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), self.amazon_gray),
            ('GRID', (0, 0), (-1, -1), 1, self.amazon_dark_gray)
        ]))
        
        story.append(comparison_table)
        story.append(Spacer(1, 20))
        
        return story
    
    def _create_service_anomalies_summary(self) -> List:
        """Create service anomalies summary section (work in progress)."""
        story = []
        
        story.append(Paragraph("Service Anomalies Analysis", self.custom_styles['SectionHeader']))
        story.append(Paragraph("🚧 This section is currently under development.", self.styles['Normal']))
        story.append(Paragraph("Future functionality will include:", self.styles['Normal']))
        story.append(Paragraph("• Detection of unusual service cost spikes", self.styles['Normal']))
        story.append(Paragraph("• Identification of new or discontinued services", self.styles['Normal']))
        story.append(Paragraph("• Analysis of service cost patterns and trends", self.styles['Normal']))
        story.append(Paragraph("• Recommendations for cost optimization opportunities", self.styles['Normal']))
        
        story.append(Spacer(1, 20))
        return story
    
    def _create_budget_anomalies_summary(self, budget_anomalies: Dict) -> List:
        """Create budget anomalies summary section."""
        story = []
        
        story.append(Paragraph("Budget Anomalies Analysis", self.custom_styles['SectionHeader']))
        
        if not budget_anomalies or 'anomaly_budgets' not in budget_anomalies:
            story.append(Paragraph("No budget data available - Budget analysis requires AWS Budgets to be configured.", self.styles['Normal']))
            story.append(Spacer(1, 20))
            return story
        
        anomaly_budgets = budget_anomalies.get('anomaly_budgets', [])
        total_checked = budget_anomalies.get('total_budgets_checked', 0)
        anomalies_found = budget_anomalies.get('anomalies_found', 0)
        threshold = budget_anomalies.get('threshold_percentage', 10.0)
        
        # Summary statistics
        summary_data = [
            ["Metric", "Value"],
            ["Total Budgets Checked", str(total_checked)],
            ["Anomalies Found", str(anomalies_found)],
            ["Threshold Used", f"{threshold}%"],
            ["Budget Health", "GOOD" if anomalies_found == 0 else "REQUIRES ATTENTION"]
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.amazon_orange),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), self.amazon_gray),
            ('GRID', (0, 0), (-1, -1), 1, self.amazon_dark_gray)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 15))
        
        # Detailed anomalies if any
        if anomaly_budgets:
            story.append(Paragraph("Budget Anomalies Details:", self.custom_styles['SubHeader']))
            
            # Create detailed table
            anomalies_data = [["Budget Name", "Limit", "Actual", "Above Target", "Severity"]]
            
            for budget in anomaly_budgets:
                budget_name = budget.get('budget_name', 'Unknown')[:25]  # Truncate long names
                budget_limit = budget.get('budget_limit', 0)
                actual_amount = budget.get('actual_amount', 0)
                above_target = budget.get('actual_above_target', 0)
                severity = budget.get('severity', 'LOW')
                currency = budget.get('currency', 'USD')
                
                anomalies_data.append([
                    budget_name,
                    f"{currency} {budget_limit:.0f}",
                    f"{currency} {actual_amount:.0f}",
                    f"{currency} {above_target:.0f}",
                    severity
                ])
            
            anomalies_table = Table(anomalies_data, colWidths=[2*inch, 1*inch, 1*inch, 1*inch, 0.8*inch])
            anomalies_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), self.amazon_dark_blue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), self.amazon_gray),
                ('GRID', (0, 0), (-1, -1), 1, self.amazon_dark_gray),
                ('VALIGN', (0, 0), (-1, -1), 'TOP')
            ]))
            
            # Color code severity
            for i, budget in enumerate(anomaly_budgets, 1):
                severity = budget.get('severity', 'LOW')
                if severity == 'CRITICAL':
                    anomalies_table.setStyle(TableStyle([('BACKGROUND', (4, i), (4, i), colors.red)]))
                elif severity == 'HIGH':
                    anomalies_table.setStyle(TableStyle([('BACKGROUND', (4, i), (4, i), colors.orange)]))
                elif severity == 'MEDIUM':
                    anomalies_table.setStyle(TableStyle([('BACKGROUND', (4, i), (4, i), colors.yellow)]))
            
            story.append(anomalies_table)
            story.append(Spacer(1, 15))
            
            # Recommendations
            story.append(Paragraph("Recommendations:", self.custom_styles['SubHeader']))
            
            critical_budgets = [b for b in anomaly_budgets if b.get('severity') == 'CRITICAL']
            high_budgets = [b for b in anomaly_budgets if b.get('severity') == 'HIGH']
            
            if critical_budgets:
                story.append(Paragraph(f"• {len(critical_budgets)} budget(s) in CRITICAL state - immediate attention required", self.styles['Normal']))
            if high_budgets:
                story.append(Paragraph(f"• {len(high_budgets)} budget(s) in HIGH state - review spending patterns", self.styles['Normal']))
            
            if not critical_budgets and not high_budgets:
                story.append(Paragraph("• Monitor budget trends closely to prevent future overages", self.styles['Normal']))
            
            story.append(Paragraph("• Consider adjusting budget limits or implementing cost controls", self.styles['Normal']))
        else:
            story.append(Paragraph("✅ All budgets are within acceptable thresholds.", self.styles['Normal']))
        
        # Add errors if any
        errors = budget_anomalies.get('errors', [])
        if errors:
            story.append(Spacer(1, 10))
            story.append(Paragraph("Budget Analysis Errors:", self.custom_styles['SubHeader']))
            for error in errors:
                story.append(Paragraph(f"• {error}", self.styles['Normal']))
        
        story.append(Spacer(1, 20))
        return story
    

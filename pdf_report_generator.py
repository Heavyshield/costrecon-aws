"""PDF report generator for AWS cost data."""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus.flowables import HRFlowable
from datetime import datetime
from typing import Dict, List


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
        
        # Extract data components
        cost_data = report_data[0] if len(report_data) > 0 else {}
        total_savings = report_data[1] if len(report_data) > 1 else {}
        sp_coverage_with_trend = report_data[2] if len(report_data) > 2 else {}
        rds_coverage = report_data[3] if len(report_data) > 3 else {}
        
        # Extract current month coverage for backward compatibility
        sp_coverage = sp_coverage_with_trend.get('selected_month', {}) if sp_coverage_with_trend else {}
        
        story = []
        
        # Title page
        story.extend(self._create_title_page(start_date, end_date))
        
        # Executive summary
        story.extend(self._create_executive_summary(cost_data, total_savings))
        
        # Savings summary
        story.extend(self._create_savings_summary(total_savings))
        
        # Coverage summary
        story.extend(self._create_coverage_summary(sp_coverage))
        
        # Trend analysis
        story.extend(self._create_trend_analysis(sp_coverage_with_trend))
        
        # RDS coverage analysis
        story.extend(self._create_rds_coverage_summary(rds_coverage))
        
        # Service details
        story.extend(self._create_service_details(cost_data))
        
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
    
    def _create_executive_summary(self, cost_data: Dict, total_savings: Dict) -> List:
        """Create executive summary section."""
        story = []
        
        story.append(Paragraph("Executive Summary", self.custom_styles['SectionHeader']))
        
        # Calculate total costs
        total_cost = self._calculate_total_cost(cost_data)
        total_savings_amount = total_savings.get('total_savings', 0.0)
        
        summary_data = [
            ["Total Cost", f"${total_cost:.2f}"],
            ["Total Monthly Savings", f"${total_savings_amount:.2f}"],
            ["Cost Optimization Rate", f"{(total_savings_amount/total_cost*100):.1f}%" if total_cost > 0 else "N/A"],
            ["Number of Services", str(len(cost_data.get('services', {}).get('DimensionValues', [])))],
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
    
    def _create_savings_summary(self, total_savings: Dict) -> List:
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
            ("EC2 Reservations", total_savings.get('ec2_reservations', 0)),
            ("RDS Reservations", total_savings.get('rds_reservations', 0)),
            ("OpenSearch Reservations", total_savings.get('opensearch_reservations', 0)),
            ("MAP/Rightsizing", total_savings.get('map_savings', 0))
        ]
        
        for source, amount in savings_items:
            if amount > 0:
                percentage = (amount / total_amount * 100) if total_amount > 0 else 0
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
        
        coverage_data = [
            ["Metric", "Value"],
            ["Average Coverage", f"{coverage_pct:.1f}%"],
            ["Coverage Status", self._get_coverage_status(coverage_pct)],
            ["Recommendation", self._get_coverage_recommendation(coverage_pct)]
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
        if coverage_pct >= 90:
            return "Excellent"
        elif coverage_pct >= 70:
            return "Good" 
        elif coverage_pct >= 50:
            return "Fair"
        else:
            return "Poor"
    
    def _get_coverage_recommendation(self, coverage_pct: float) -> str:
        """Get coverage recommendation based on percentage."""
        if coverage_pct >= 90:
            return "Maintain current coverage levels"
        elif coverage_pct >= 70:
            return "Consider increasing coverage for additional savings"
        else:
            return "Review workload patterns and consider Savings Plans"
    
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
        cost_coverage = rds_coverage.get('average_cost_coverage_percentage', 0)
        utilization = rds_coverage.get('average_utilization_percentage', 0)
        
        coverage_data = [
            ["Metric", "Value", "Status"],
            ["Hours Coverage", f"{hours_coverage:.1f}%", self._get_coverage_status(hours_coverage)],
            ["Cost Coverage", f"{cost_coverage:.1f}%", self._get_coverage_status(cost_coverage)],
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
        if utilization_pct >= 90:
            return "Excellent"
        elif utilization_pct >= 70:
            return "Good"
        elif utilization_pct >= 50:
            return "Fair"
        else:
            return "Poor"
    
    def _create_service_details(self, cost_data: Dict) -> List:
        """Create service details section."""
        story = []
        
        story.append(Paragraph("Service Breakdown", self.custom_styles['SectionHeader']))
        
        services = cost_data.get('services', {}).get('DimensionValues', [])
        
        if services:
            table_data = [["Service", "Description"]]
            for service in services[:20]:  # Limit to top 20 services
                service_name = service.get('Value', 'Unknown')
                table_data.append([service_name, service.get('Attributes', {}).get('description', 'N/A')])
            
            service_table = Table(table_data, colWidths=[2.5*inch, 3.5*inch])
            service_table.setStyle(TableStyle([
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
            
            story.append(service_table)
        else:
            story.append(Paragraph("No service data available.", self.styles['Normal']))
        
        return story
    
    def _calculate_total_cost(self, cost_data: Dict) -> float:
        """Calculate total cost from cost data."""
        total = 0.0
        
        cost_results = cost_data.get('cost_data', {}).get('ResultsByTime', [])
        
        for result in cost_results:
            total_cost = result.get('Total', {}).get('BlendedCost', {}).get('Amount', '0')
            try:
                total += float(total_cost)
            except ValueError:
                continue
        
        return total
    

"""PDF report generator for AWS cost data."""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
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
    
    def _create_custom_styles(self) -> Dict:
        """Create custom paragraph styles."""
        styles = {}
        
        styles['CustomTitle'] = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Center alignment
            textColor=colors.darkblue
        )
        
        styles['SectionHeader'] = ParagraphStyle(
            'SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.darkblue
        )
        
        styles['SubHeader'] = ParagraphStyle(
            'SubHeader',
            parent=self.styles['Heading3'],
            fontSize=14,
            spaceAfter=8,
            spaceBefore=12,
            textColor=colors.black
        )
        
        return styles
    
    def generate_report(self, cost_data: Dict, output_filename: str, 
                       start_date: datetime, end_date: datetime) -> None:
        """Generate a PDF report from cost data.
        
        Args:
            cost_data: Cost data from AWS Cost Explorer
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
        
        story = []
        
        # Title page
        story.extend(self._create_title_page(start_date, end_date))
        
        # Executive summary
        story.extend(self._create_executive_summary(cost_data))
        
        # Cost breakdown
        story.extend(self._create_cost_breakdown(cost_data))
        
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
                               color=colors.darkblue, spaceBefore=20, spaceAfter=20))
        
        return story
    
    def _create_executive_summary(self, cost_data: Dict) -> List:
        """Create executive summary section."""
        story = []
        
        story.append(Paragraph("Executive Summary", self.custom_styles['SectionHeader']))
        
        # Calculate total costs
        total_cost = self._calculate_total_cost(cost_data)
        
        summary_data = [
            ["Total Cost", f"${total_cost:.2f}"],
            ["Number of Services", str(len(cost_data.get('services', {}).get('DimensionValues', [])))],
            ["Report Period", f"{(cost_data['period']['end'] - cost_data['period']['start']).days} days"]
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.darkblue),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        return story
    
    def _create_cost_breakdown(self, cost_data: Dict) -> List:
        """Create cost breakdown section."""
        story = []
        
        story.append(Paragraph("Daily Cost Breakdown", self.custom_styles['SectionHeader']))
        
        # Extract daily costs from the cost data
        daily_costs = self._extract_daily_costs(cost_data)
        
        if daily_costs:
            table_data = [["Date", "Cost (USD)"]]
            for date, cost in daily_costs:
                table_data.append([date, f"${cost:.2f}"])
            
            cost_table = Table(table_data, colWidths=[2*inch, 2*inch])
            cost_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.darkblue),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(cost_table)
        else:
            story.append(Paragraph("No daily cost data available.", self.styles['Normal']))
        
        story.append(Spacer(1, 20))
        
        return story
    
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
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.darkblue),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
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
    
    def _extract_daily_costs(self, cost_data: Dict) -> List[tuple]:
        """Extract daily costs from cost data."""
        daily_costs = []
        
        cost_results = cost_data.get('cost_data', {}).get('ResultsByTime', [])
        
        for result in cost_results:
            start_date = result.get('TimePeriod', {}).get('Start', '')
            total_cost = result.get('Total', {}).get('BlendedCost', {}).get('Amount', '0')
            
            try:
                cost_amount = float(total_cost)
                daily_costs.append((start_date, cost_amount))
            except ValueError:
                continue
        
        return sorted(daily_costs)  # Sort by date
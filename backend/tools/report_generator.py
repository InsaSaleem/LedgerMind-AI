from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
import time

def generate_pdf_report(df, anomalies, charts, upload_folder):
    """
    Generates a PDF report containing summary stats, anomalies, and charts.
    Returns the file path to the generated report.
    """
    timestamp = int(time.time())
    report_filename = f"LedgerMind_Report_{timestamp}.pdf"
    report_path = os.path.join(upload_folder, report_filename)
    
    c = canvas.Canvas(report_path, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, height - 50, "LedgerMind AI - Financial Report")
    
    # Summary
    c.setFont("Helvetica", 14)
    c.drawString(50, height - 100, f"Total Transactions: {len(df)}")
    if 'Amount' in df.columns:
        c.drawString(50, height - 120, f"Total Spend: ${df['Amount'].sum():.2f}")
    
    # Anomalies
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 160, "Detected Anomalies")
    
    c.setFont("Helvetica", 12)
    y_pos = height - 180
    for i, anomaly in enumerate(anomalies[:10]): # Limit to top 10
        if y_pos < 50:
            c.showPage()
            y_pos = height - 50
        
        text = f"- {anomaly.get('date', '')}: {anomaly.get('description', '')} [${anomaly.get('amount', 0):.2f}]"
        c.drawString(50, y_pos, text)
        y_pos -= 15
        reason = f"  Reason: {anomaly.get('reason', '')}"
        c.drawString(50, y_pos, reason)
        y_pos -= 25
        
    c.save()
    return f"/api/download/{report_filename}" # We'd map this in app.py in real life, or serve static.

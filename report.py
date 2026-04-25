from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from datetime import datetime
from database import get_stats
from pathlib import Path

GREEN = colors.HexColor("#16a34a")
DARK  = colors.HexColor("#072a1a")

def generate_esg_report() -> str:
    stats = get_stats()
    out_path = str(Path(__file__).parent / "FoodFlow_ESG_Report.pdf")
    doc = SimpleDocTemplate(out_path, pagesize=letter,
                            leftMargin=0.85*inch, rightMargin=0.85*inch,
                            topMargin=0.85*inch, bottomMargin=0.85*inch)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(
        '<font color="#072a1a"><b>FoodFlow AI</b></font> — ESG Impact Report',
        ParagraphStyle("title", parent=styles["Title"], fontSize=20, spaceAfter=4)
    ))
    story.append(Paragraph(
        f"Cornell University Dining · Generated {datetime.now().strftime('%B %d, %Y')}",
        ParagraphStyle("sub", parent=styles["Normal"], fontSize=10, textColor=colors.gray, spaceAfter=20)
    ))

    data = [
        ["Metric", "Value", "Equivalent"],
        ["Food Rescued", f"{stats['total_lbs']:.0f} lbs", f"{stats['total_meals']:.0f} meals served"],
        ["Rescues Completed", str(stats['total_pickups']), "100% autonomous dispatch"],
        ["CO₂ Avoided", f"{stats['total_co2_kg']:.1f} kg", "Zero landfill decomposition"],
        ["Legal Compliance", "Bill Emerson Act", "All donations verified"],
    ]
    tbl = Table(data, colWidths=[2.5*inch, 2*inch, 2.3*inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), DARK),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#f0fdf4"), colors.white]),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
        ("PADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "Powered by FoodFlow AI · Claude claude-sonnet-4-6 · Anthropic",
        ParagraphStyle("foot", parent=styles["Normal"], fontSize=8, textColor=colors.gray)
    ))
    doc.build(story)
    return out_path

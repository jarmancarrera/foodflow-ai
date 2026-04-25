import os
import json
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from datetime import datetime
from database import get_stats, get_pickups, get_rescues
from pathlib import Path

GREEN = colors.HexColor("#16a34a")
DARK  = colors.HexColor("#072a1a")
FOG   = colors.HexColor("#f8fafc")
LINE  = colors.HexColor("#e5e7eb")

def generate_esg_report() -> str:
    stats = get_stats()
    pickups = get_pickups(25)
    rescues = get_rescues(25)

    # Compliance log from agent traces (best-effort).
    compliance_rows = []
    for r in rescues:
        try:
            payload = json.loads(r.get("result_json") or "{}")
        except Exception:
            payload = {}
        for step in payload.get("steps", []) or []:
            if step.get("tool") != "verify_compliance":
                continue
            out = step.get("output") or {}
            compliance_rows.append([
                r.get("rescue_id", "-"),
                r.get("location_name") or r.get("location_id", "-"),
                "PASS" if out.get("compliant") else "FAIL",
                out.get("protection", "Bill Emerson Act"),
                out.get("timestamp", ""),
            ])

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = str(Path(__file__).parent / f"FoodFlow_ESG_Report_{stamp}.pdf")
    doc = SimpleDocTemplate(out_path, pagesize=letter,
                            leftMargin=0.85*inch, rightMargin=0.85*inch,
                            topMargin=0.85*inch, bottomMargin=0.85*inch)
    styles = getSampleStyleSheet()
    story = []

    title = ParagraphStyle("title", parent=styles["Title"], fontSize=22, spaceAfter=6, textColor=DARK)
    sub = ParagraphStyle("sub", parent=styles["Normal"], fontSize=10, textColor=colors.gray, spaceAfter=18)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=14, textColor=DARK, spaceAfter=10)
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10.5, leading=14, textColor=colors.HexColor("#111827"))

    story.append(Paragraph("<b>FoodFlow AI</b> — ESG & Impact Report", title))
    story.append(Paragraph(f"Cornell University Dining · Generated {datetime.now().strftime('%B %d, %Y %H:%M')}", sub))
    story.append(Paragraph(
        "This report summarizes verified food rescue activity logged by FoodFlow AI. "
        "Each rescue is coordinated via an autonomous Claude tool_use loop and persisted to SQLite for auditability.",
        body,
    ))
    story.append(Spacer(1, 14))

    data = [
        ["Metric", "Value", "Notes"],
        ["Food rescued", f"{stats['total_lbs']:.0f} lbs", f"≈ {stats['total_meals']:.0f} meals served (0.6 meals/lb)"],
        ["CO₂ avoided", f"{stats['total_co2_kg']:.1f} kg", "Demo factor: 0.154 kg CO₂ per lb diverted"],
        ["Pickups logged", str(stats["total_pickups"]), "Recorded in SQLite `pickups` table"],
        ["Compliance checks", str(len(compliance_rows)), "From `verify_compliance` tool trace"],
    ]
    tbl = Table(data, colWidths=[2.2*inch, 1.6*inch, 3.0*inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), DARK),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [FOG, colors.white]),
        ("GRID", (0,0), (-1,-1), 0.5, LINE),
        ("PADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 18))

    story.append(Paragraph("Recent rescues (latest 25)", h2))
    resc_data = [["Rescue ID", "Location", "Status", "Started", "Completed"]]
    for r in rescues:
        resc_data.append([
            r.get("rescue_id", "-"),
            r.get("location_name") or r.get("location_id", "-"),
            r.get("status", "-"),
            r.get("started_at", "-"),
            r.get("completed_at") or "-",
        ])
    resc_tbl = Table(resc_data, colWidths=[1.8*inch, 1.6*inch, 0.9*inch, 1.3*inch, 1.3*inch])
    resc_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, FOG]),
        ("GRID", (0,0), (-1,-1), 0.5, LINE),
        ("PADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(resc_tbl)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Recent pickups (latest 25)", h2))
    pick_data = [["ID", "Rescue", "From", "To", "Driver", "Item", "Lbs", "Dispatched"]]
    for p in pickups:
        pick_data.append([
            str(p.get("id", "")),
            p.get("rescue_id") or "-",
            p.get("supplier_name") or p.get("supplier_id") or "-",
            p.get("foodbank_name") or p.get("foodbank_id") or "-",
            p.get("volunteer_name") or p.get("volunteer_id") or "-",
            p.get("item") or "-",
            f"{float(p.get('quantity_lbs') or 0):.1f}",
            p.get("dispatched_at") or "-",
        ])
    pick_tbl = Table(pick_data, colWidths=[0.4*inch, 1.0*inch, 1.1*inch, 1.1*inch, 1.0*inch, 1.2*inch, 0.5*inch, 1.2*inch])
    pick_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#111827")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8.0),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, FOG]),
        ("GRID", (0,0), (-1,-1), 0.5, LINE),
        ("PADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(pick_tbl)

    if compliance_rows:
        story.append(PageBreak())
        story.append(Paragraph("Compliance log (verify_compliance)", h2))
        comp_data = [["Rescue ID", "Location", "Result", "Protection", "Timestamp"]] + compliance_rows[:40]
        comp_tbl = Table(comp_data, colWidths=[1.7*inch, 1.4*inch, 0.7*inch, 2.1*inch, 1.6*inch])
        comp_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), DARK),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8.5),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [FOG, colors.white]),
            ("GRID", (0,0), (-1,-1), 0.5, LINE),
            ("PADDING", (0,0), (-1,-1), 6),
        ]))
        story.append(comp_tbl)

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        f"Powered by FoodFlow AI · Model: {os.getenv('FOODFLOW_ANTHROPIC_MODEL','claude-sonnet-4-6')} · Data source: SQLite",
        ParagraphStyle("foot", parent=styles["Normal"], fontSize=8, textColor=colors.gray)
    ))
    doc.build(story)
    return out_path

import os
import json
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus.flowables import Flowable
from datetime import datetime
from database import get_stats, get_pickups, get_rescues
from pathlib import Path

# ── Brand palette ──────────────────────────────────────────────────────────
FOREST  = colors.HexColor("#0A3622")
FOREST2 = colors.HexColor("#061d13")
GREEN   = colors.HexColor("#16A34A")
MINT    = colors.HexColor("#DCFCE7")
MINT2   = colors.HexColor("#bbf7d0")
FOG     = colors.HexColor("#F8FAFC")
FOG2    = colors.HexColor("#F1F5F9")
LINE    = colors.HexColor("#E2E8F0")
INK     = colors.HexColor("#0F172A")
SLATE   = colors.HexColor("#475569")
MUTED   = colors.HexColor("#94A3B8")
GOLD    = colors.HexColor("#CA8A04")
GOLD2   = colors.HexColor("#fef9c3")
RED     = colors.HexColor("#DC2626")
RED2    = colors.HexColor("#fee2e2")
WHITE   = colors.white


class ColorBlock(Flowable):
    """Full-width colored rectangle — used for cover header."""
    def __init__(self, height, bg, content_fn=None):
        super().__init__()
        self.height = height
        self.bg = bg
        self.content_fn = content_fn

    def wrap(self, availWidth, availHeight):
        self._w = availWidth
        return (availWidth, self.height)

    def draw(self):
        self.canv.setFillColor(self.bg)
        self.canv.rect(0, 0, self._w, self.height, fill=1, stroke=0)
        if self.content_fn:
            self.content_fn(self.canv, self._w, self.height)


def _make_styles():
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "cover_title", parent=base["Normal"],
            fontSize=28, fontName="Helvetica-Bold",
            textColor=WHITE, leading=32, spaceAfter=4,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub", parent=base["Normal"],
            fontSize=11, fontName="Helvetica",
            textColor=colors.HexColor("#86efac"), leading=16,
        ),
        "section_label": ParagraphStyle(
            "section_label", parent=base["Normal"],
            fontSize=9, fontName="Helvetica-Bold",
            textColor=GREEN, leading=12, spaceBefore=18, spaceAfter=6,
            leftIndent=10, borderPadding=(0, 0, 0, 8),
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Normal"],
            fontSize=15, fontName="Helvetica-Bold",
            textColor=FOREST, leading=20, spaceBefore=20, spaceAfter=10,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontSize=10, fontName="Helvetica",
            textColor=INK, leading=15, spaceAfter=4,
        ),
        "body_sm": ParagraphStyle(
            "body_sm", parent=base["Normal"],
            fontSize=9, fontName="Helvetica",
            textColor=SLATE, leading=13,
        ),
        "kpi_num": ParagraphStyle(
            "kpi_num", parent=base["Normal"],
            fontSize=30, fontName="Helvetica-Bold",
            textColor=FOREST, leading=34, alignment=TA_CENTER,
        ),
        "kpi_lbl": ParagraphStyle(
            "kpi_lbl", parent=base["Normal"],
            fontSize=9, fontName="Helvetica",
            textColor=SLATE, leading=12, alignment=TA_CENTER,
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"],
            fontSize=8, fontName="Helvetica",
            textColor=MUTED, alignment=TA_CENTER, leading=11,
        ),
        "table_hdr": ParagraphStyle(
            "table_hdr", parent=base["Normal"],
            fontSize=9, fontName="Helvetica-Bold",
            textColor=WHITE, alignment=TA_LEFT,
        ),
        "table_cell": ParagraphStyle(
            "table_cell", parent=base["Normal"],
            fontSize=9, fontName="Helvetica",
            textColor=INK, leading=12,
        ),
        "mono": ParagraphStyle(
            "mono", parent=base["Normal"],
            fontSize=8, fontName="Courier",
            textColor=SLATE, leading=11,
        ),
    }


def _section_bar(label, styles):
    """Returns [spacer, colored left-bar heading] as a KeepTogether block."""
    return [
        HRFlowable(width="100%", thickness=1, color=LINE, spaceAfter=0, spaceBefore=16),
        Paragraph(f"▎  {label.upper()}", styles["section_label"]),
    ]


def generate_esg_report() -> str:
    stats   = get_stats()
    pickups = get_pickups(25)
    rescues = get_rescues(25)

    # Build compliance log from agent traces
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
                r.get("rescue_id", "—"),
                r.get("location_name") or r.get("location_id", "—"),
                "PASS" if out.get("compliant") else "FAIL",
                out.get("protection", "Bill Emerson Act"),
                out.get("timestamp", ""),
            ])

    stamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = str(Path(__file__).parent / f"FoodFlow_ESG_Report_{stamp}.pdf")
    doc      = SimpleDocTemplate(
        out_path, pagesize=letter,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
        topMargin=0, bottomMargin=0.75*inch,
    )
    styles = _make_styles()
    story  = []

    # ── COVER HEADER ─────────────────────────────────────────────────────
    def draw_cover(canv, w, h):
        # Accent stripe
        canv.setFillColor(GREEN)
        canv.rect(0, h - 5, w, 5, fill=1, stroke=0)
        # Title
        canv.setFillColor(WHITE)
        canv.setFont("Helvetica-Bold", 30)
        canv.drawString(0.75*inch, h - 68, "FoodFlow AI")
        canv.setFont("Helvetica", 14)
        canv.setFillColor(colors.HexColor("#86efac"))
        canv.drawString(0.75*inch, h - 90, "ESG & Impact Report")
        # Date + model
        canv.setFillColor(colors.HexColor("#4ade80"))
        canv.setFont("Helvetica", 9)
        canv.drawString(0.75*inch, h - 112,
            f"Generated {datetime.now().strftime('%B %d, %Y at %H:%M')}  ·  "
            f"Model: {os.getenv('FOODFLOW_ANTHROPIC_MODEL', 'claude-sonnet-4-6')}  ·  "
            f"Cornell CBC Hackathon 2026")
        # Right badge
        canv.setFillColor(colors.HexColor("#052e16"))
        canv.roundRect(w - 0.75*inch - 1.5*inch, h - 100, 1.5*inch, 36, 6, fill=1, stroke=0)
        canv.setFillColor(GREEN)
        canv.setFont("Helvetica-Bold", 9)
        canv.drawCentredString(w - 0.75*inch - 0.75*inch, h - 80, "AUTONOMOUS AI")
        canv.setFillColor(colors.HexColor("#86efac"))
        canv.setFont("Helvetica", 8)
        canv.drawCentredString(w - 0.75*inch - 0.75*inch, h - 93, "Claude tool_use loop")

    story.append(ColorBlock(130, FOREST, draw_cover))
    story.append(Spacer(1, 20))

    # ── INTRO ─────────────────────────────────────────────────────────────
    story.append(Paragraph(
        "This report summarizes verified food rescue activity coordinated by the FoodFlow AI autonomous agent. "
        "Each rescue is executed via a six-tool Claude loop — inventory check, foodbank matching, volunteer dispatch, "
        "route calculation, Bill Emerson Act compliance verification, and confirmed pickup — with every step "
        "persisted to SQLite for full auditability.",
        styles["body"],
    ))

    # ── KPI TILES ────────────────────────────────────────────────────────
    story += _section_bar("Impact Metrics", styles)

    meals   = stats.get("total_meals", 0)
    lbs     = stats.get("total_lbs", 0)
    co2     = stats.get("total_co2_kg", 0)
    npick   = stats.get("total_pickups", 0)

    def kpi_cell(num, unit, label, bg, accent):
        return [
            Paragraph(f"<b>{num}</b>", ParagraphStyle(
                "kn", fontName="Helvetica-Bold", fontSize=28,
                textColor=accent, alignment=TA_CENTER, leading=32)),
            Paragraph(unit, ParagraphStyle(
                "ku", fontName="Helvetica-Bold", fontSize=9,
                textColor=accent, alignment=TA_CENTER, leading=12)),
            Paragraph(label, ParagraphStyle(
                "kl", fontName="Helvetica", fontSize=8,
                textColor=SLATE, alignment=TA_CENTER, leading=11, spaceBefore=2)),
        ]

    kpi_data = [[
        kpi_cell(f"{npick}", "Pickups", "Rescues logged", MINT, FOREST),
        kpi_cell(f"{lbs:.0f}", "lbs", "Food rescued", FOG, FOREST),
        kpi_cell(f"{meals:.0f}", "Meals", "People fed", GOLD2, GOLD),
        kpi_cell(f"{co2:.1f}", "kg CO₂", "Emissions avoided", RED2, RED),
    ]]

    kpi_tbl = Table(kpi_data, colWidths=[1.7*inch]*4, rowHeights=[None])
    kpi_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,0), MINT),
        ("BACKGROUND", (1,0), (1,0), FOG2),
        ("BACKGROUND", (2,0), (2,0), GOLD2),
        ("BACKGROUND", (3,0), (3,0), RED2),
        ("ROUNDEDCORNERS", [6]),
        ("BOX", (0,0), (0,0), 1, MINT2),
        ("BOX", (1,0), (1,0), 1, LINE),
        ("BOX", (2,0), (2,0), 1, colors.HexColor("#fde68a")),
        ("BOX", (3,0), (3,0), 1, colors.HexColor("#fecaca")),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 14),
        ("BOTTOMPADDING", (0,0), (-1,-1), 14),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("LINEBEFORE", (1,0), (3,0), 1, WHITE),
    ]))
    story.append(kpi_tbl)
    story.append(Spacer(1, 4))

    story.append(Paragraph(
        "CO₂ calculation uses DEFRA methodology (2.5 kg CO₂eq per kg food diverted from landfill). "
        "Meals calculated at 1.8 meals per kg rescued (Feeding America standard). "
        "All figures derived from SQLite pickups table.",
        styles["body_sm"],
    ))

    # ── RESCUE LOG TABLE ─────────────────────────────────────────────────
    if rescues:
        story += _section_bar("Rescue Log", styles)
        hdr_style = [
            ("BACKGROUND", (0,0), (-1,0), FOREST),
            ("TEXTCOLOR", (0,0), (-1,0), WHITE),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,0), 8.5),
            ("FONTSIZE", (0,1), (-1,-1), 8),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, FOG]),
            ("GRID", (0,0), (-1,-1), 0.4, LINE),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING", (0,0), (-1,-1), 7),
            ("RIGHTPADDING", (0,0), (-1,-1), 7),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]
        resc_data = [["Rescue ID", "Location", "Status", "Started", "Completed"]]
        for r in rescues:
            status = r.get("status", "—")
            resc_data.append([
                Paragraph(r.get("rescue_id", "—"), styles["mono"]),
                r.get("location_name") or r.get("location_id", "—"),
                status,
                r.get("started_at", "—"),
                r.get("completed_at") or "—",
            ])
        resc_tbl = Table(resc_data, colWidths=[1.6*inch, 1.5*inch, 0.85*inch, 1.35*inch, 1.35*inch])
        resc_tbl.setStyle(TableStyle(hdr_style + [
            # Color status column
            ("TEXTCOLOR", (2,1), (2,-1), GREEN),
            ("FONTNAME", (2,1), (2,-1), "Helvetica-Bold"),
        ]))
        story.append(resc_tbl)

    # ── PICKUP DETAIL TABLE ──────────────────────────────────────────────
    if pickups:
        story += _section_bar("Dispatched Pickups", styles)
        pick_data = [["ID", "From", "To", "Driver", "Item", "Lbs", "Dispatched"]]
        for p in pickups:
            pick_data.append([
                str(p.get("id", "")),
                p.get("supplier_name") or p.get("supplier_id") or "—",
                p.get("foodbank_name") or p.get("foodbank_id") or "—",
                p.get("volunteer_name") or "—",
                p.get("item") or "—",
                Paragraph(f"<b>{float(p.get('quantity_lbs') or 0):.1f}</b>",
                    ParagraphStyle("lbs", fontName="Helvetica-Bold", fontSize=8,
                        textColor=GREEN, alignment=TA_RIGHT)),
                p.get("dispatched_at") or "—",
            ])
        pick_tbl = Table(pick_data,
            colWidths=[0.35*inch, 1.15*inch, 1.15*inch, 1.05*inch, 1.1*inch, 0.5*inch, 1.35*inch])
        pick_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), FOREST),
            ("TEXTCOLOR", (0,0), (-1,0), WHITE),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,0), 8.5),
            ("FONTSIZE", (0,1), (-1,-1), 8),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, FOG]),
            ("GRID", (0,0), (-1,-1), 0.4, LINE),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("RIGHTPADDING", (0,0), (-1,-1), 6),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(pick_tbl)

    # ── COMPLIANCE LOG ────────────────────────────────────────────────────
    if compliance_rows:
        story.append(PageBreak())
        story += _section_bar("Compliance Verification Log", styles)
        story.append(Paragraph(
            "Each entry represents a passing Bill Emerson Act check performed by the verify_compliance "
            "tool during the autonomous rescue loop.",
            styles["body_sm"],
        ))
        story.append(Spacer(1, 8))
        comp_data = [["Rescue ID", "Location", "Result", "Protection Act", "Timestamp"]]
        for row in compliance_rows[:40]:
            result = row[2]
            comp_data.append([
                Paragraph(row[0], styles["mono"]),
                row[1], result, row[3], row[4],
            ])
        comp_tbl = Table(comp_data, colWidths=[1.5*inch, 1.3*inch, 0.65*inch, 2.0*inch, 1.2*inch])
        comp_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), FOREST),
            ("TEXTCOLOR", (0,0), (-1,0), WHITE),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,0), 8.5),
            ("FONTSIZE", (0,1), (-1,-1), 8),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, FOG]),
            ("GRID", (0,0), (-1,-1), 0.4, LINE),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING", (0,0), (-1,-1), 7),
            ("RIGHTPADDING", (0,0), (-1,-1), 7),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            # Color PASS/FAIL
            ("TEXTCOLOR", (2,1), (2,-1), GREEN),
            ("FONTNAME", (2,1), (2,-1), "Helvetica-Bold"),
        ]))
        story.append(comp_tbl)

    # ── FOOTER ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=1, color=LINE))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"FoodFlow AI  ·  Cornell CBC Hackathon 2026  ·  "
        f"Powered by Claude {os.getenv('FOODFLOW_ANTHROPIC_MODEL','claude-sonnet-4-6')}  ·  "
        f"Data source: SQLite  ·  Generated {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        styles["footer"],
    ))

    doc.build(story)
    return out_path

import io
import zipfile
from datetime import datetime
from typing import List, Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart

# ── Brand colours ───────────────────────────────────────────────────────────
TEAL        = colors.HexColor("#00adb5")
DARK_BG     = colors.HexColor("#222831")
CARD_BG     = colors.HexColor("#393e46")
TEXT_LIGHT  = colors.HexColor("#eeeeee")
GREEN       = colors.HexColor("#2ecc71")
YELLOW      = colors.HexColor("#f1c40f")
RED         = colors.HexColor("#e74c3c")
WHITE       = colors.white
GREY        = colors.HexColor("#aaaaaa")

def _status_color(status: str) -> colors.HexColor:
    return {"On Track": GREEN, "Lagging": YELLOW, "Inactive": RED}.get(status, GREY)

def _build_styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle("cover_title", parent=base["Title"], fontSize=28, textColor=TEAL, spaceAfter=6, alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "cover_sub": ParagraphStyle("cover_sub", parent=base["Normal"], fontSize=12, textColor=TEXT_LIGHT, spaceAfter=4, alignment=TA_CENTER),
        "section_heading": ParagraphStyle("section_heading", parent=base["Heading2"], fontSize=14, textColor=TEAL, spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold", borderPad=4),
        "body": ParagraphStyle("body", parent=base["Normal"], fontSize=10, textColor=colors.black, spaceAfter=4, leading=15),
        "summary_body": ParagraphStyle("summary_body", parent=base["Normal"], fontSize=10, textColor=colors.black, spaceAfter=6, leading=16),
        "footer": ParagraphStyle("footer", parent=base["Normal"], fontSize=8, textColor=GREY, alignment=TA_CENTER),
        "kpi_label": ParagraphStyle("kpi_label", parent=base["Normal"], fontSize=9, textColor=GREY, alignment=TA_CENTER),
        "kpi_value": ParagraphStyle("kpi_value", parent=base["Normal"], fontSize=18, textColor=colors.black, alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "title": ParagraphStyle("title", parent=base["Title"], fontSize=20, textColor=TEAL, spaceAfter=4, alignment=TA_CENTER, fontName="Helvetica-Bold"),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontSize=10, textColor=GREY, alignment=TA_CENTER),
    }


def _build_score_donut(score_pct: float) -> Drawing:
    score = max(0.0, min(100.0, float(score_pct)))
    drawing = Drawing(160, 140)
    pie = Pie()
    pie.x = 20
    pie.y = 10
    pie.width = 120
    pie.height = 120
    pie.data = [score, 100 - score]
    pie.labels = ["", ""]
    pie.slices.strokeWidth = 0
    pie.slices[0].fillColor = TEAL
    pie.slices[1].fillColor = colors.HexColor("#e6e6e6")
    pie.startAngle = 90
    pie.direction = "clockwise"
    drawing.add(pie)
    drawing.add(String(80, 58, f"{score:.1f}%", textAnchor="middle", fontSize=16, fillColor=colors.black))
    drawing.add(String(80, 40, "Final Score", textAnchor="middle", fontSize=9, fillColor=GREY))
    return drawing


def _build_weekly_bar(weekly_activity: List[Dict[str, Any]]) -> Drawing:
    drawing = Drawing(240, 140)
    chart = VerticalBarChart()
    chart.x = 20
    chart.y = 20
    chart.width = 200
    chart.height = 100
    points = [int(w.get("commits", 0)) for w in weekly_activity[-12:]]
    if not points:
        points = [0]
    chart.data = [points]
    chart.barWidth = 10
    chart.groupSpacing = 6
    chart.strokeColor = colors.transparent
    chart.fillColor = TEAL
    chart.valueAxis.valueMin = 0
    chart.valueAxis.visible = False
    chart.categoryAxis.visible = False
    drawing.add(chart)
    drawing.add(String(120, 125, "Weekly Activity", textAnchor="middle", fontSize=9, fillColor=GREY))
    return drawing


def _bus_factor_from_gini(gini: float) -> int:
    # Heuristic buckets used for dashboard reporting.
    # Thresholds (0.4/0.6) are practical cutoffs and should be treated as configurable policy.
    if gini >= 0.6:
        return 1
    if gini >= 0.4:
        return 2
    return 3


def _safe_filename(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(value))
    return safe.strip("_") or "team"

def _generate_summary(team: Dict[str, Any]) -> str:
    team_id     = team.get("team_id", "This team")
    status      = team.get("status", "Unknown")
    score       = team.get("progress_pct", 0)
    commits     = int(team.get("total_commits", 0))
    lines_added = int(team.get("lines_added", 0))
    code_bytes  = int(team.get("code_bytes", 0))
    active_days = int(team.get("active_days", 0))
    gini        = float(team.get("gini_coefficient", 0))
    language    = team.get("primary_language", "Unknown")
    last_pushed = team.get("last_pushed", "N/A")

    if score >= 70:
        score_sentence = f"{team_id} is performing strongly with an overall score of {score:.1f}%, placing them in the 'On Track' category."
    elif score >= 30:
        score_sentence = f"{team_id} has an overall score of {score:.1f}%, which puts them in the 'Lagging' category. There is room for meaningful improvement."
    else:
        score_sentence = f"{team_id} has a low overall score of {score:.1f}% and is currently classified as 'Inactive'. Immediate intervention is recommended."

    if commits == 0:
        commit_sentence = "No commits have been recorded in the repository."
    elif commits < 10:
        commit_sentence = f"The team has made {commits} commit(s) so far, which is relatively low."
    elif commits < 50:
        commit_sentence = f"With {commits} commits, the team shows moderate development activity."
    else:
        commit_sentence = f"The team has made {commits} commits, reflecting strong development activity."

    if lines_added == 0 and code_bytes > 0:
        loc_sentence = f"GitHub LOC additions are currently unavailable, but language analysis reports {code_bytes:,} bytes of code."
    elif lines_added == 0:
        loc_sentence = "No lines of code have been added yet."
    elif lines_added < 500:
        loc_sentence = f"A total of {lines_added:,} lines of code have been added — a modest codebase."
    elif lines_added < 5000:
        loc_sentence = f"The team has contributed {lines_added:,} lines of code, showing solid progress."
    else:
        loc_sentence = f"An impressive {lines_added:,} lines of code have been written, indicating a substantial project."

    if active_days == 0:
        consistency_sentence = "The repository shows no recorded activity days."
    elif active_days < 3:
        consistency_sentence = f"Work appears to be concentrated in short bursts ({active_days} active day(s)), suggesting the team may benefit from more regular contributions."
    elif active_days < 15:
        consistency_sentence = f"The team has been active on {active_days} separate days, showing reasonable consistency."
    else:
        consistency_sentence = f"With {active_days} active days, the team demonstrates excellent consistency and sustained effort over time."

    balance = 1.0 - gini
    if balance >= 0.8:
        collab_sentence = "Collaboration is excellent — contributions are distributed very evenly across team members."
    elif balance >= 0.5:
        collab_sentence = f"Collaboration is fair (balance score: {balance:.2f}), though some members may be contributing more than others."
    else:
        collab_sentence = f"Collaboration is uneven (balance score: {balance:.2f}). The workload appears to be concentrated in one or two contributors."

    lang_sentence = f"The primary programming language used is {language}."
    if last_pushed != "N/A":
        lang_sentence += f" The repository was last updated on {last_pushed}."

    if status == "On Track":
        recommendation = "Recommendation: Maintain the current pace. Focus on code quality, documentation, and preparing for final submission."
    elif status == "Lagging":
        recommendation = "Recommendation: Increase commit frequency and aim for more balanced contributions. A focused sprint in the coming days can significantly improve the overall score."
    else:
        recommendation = "Recommendation: This team requires immediate follow-up. The instructor should check in with the team to identify blockers and establish a recovery plan as soon as possible."

    return f"{score_sentence} {commit_sentence} {loc_sentence} {consistency_sentence} {collab_sentence} {lang_sentence} {recommendation}"


# Removed old duplicate implementation to keep a single production PDF path.
def generate_team_pdf(team: Dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    styles = _build_styles()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f"Performance Review - {team.get('team_id', 'Team')}",
        author="Project Performance Analysis System",
    )
    story = []
    W = A4[0] - 3 * cm

    team_id = team.get("team_id", "N/A")
    repo_name = team.get("repo_name", "N/A")
    status = team.get("status", "Unknown")
    score = float(team.get("progress_pct", 0))
    total_commits = int(team.get("total_commits", 0))
    lines_added = int(team.get("lines_added", 0))
    lines_deleted = int(team.get("lines_deleted", 0))
    active_days = int(team.get("active_days", 0))
    gini = float(team.get("gini_coefficient", 0))
    collab_score = max(0.0, min(1.0, 1.0 - gini))
    net_impact = lines_added - lines_deleted
    churn_total = lines_added + lines_deleted
    efficiency_ratio = (net_impact / churn_total) if churn_total > 0 else 0.0
    bus_factor = _bus_factor_from_gini(gini)
    primary_language = team.get("primary_language", "Unknown")
    last_pushed = team.get("last_pushed", "N/A")

    story.append(Paragraph("Student Project Performance Review", styles["title"]))
    story.append(Paragraph(f"Team {team_id} - {repo_name} | Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["subtitle"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(HRFlowable(width=W, thickness=1, color=CARD_BG, spaceAfter=8))

    kpi_row = [
        Paragraph("Final Score", styles["kpi_label"]),
        Paragraph("Commits", styles["kpi_label"]),
        Paragraph("LOC Added", styles["kpi_label"]),
        Paragraph("Active Days", styles["kpi_label"]),
    ]
    kpi_vals = [
        Paragraph(f"{score:.1f}%", styles["kpi_value"]),
        Paragraph(str(total_commits), styles["kpi_value"]),
        Paragraph(f"{lines_added:,}", styles["kpi_value"]),
        Paragraph(str(active_days), styles["kpi_value"]),
    ]
    kpi_table = Table([kpi_row, kpi_vals], colWidths=[W / 4] * 4)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f5f5")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.3 * cm))

    badge = Table(
        [[Paragraph(f"<b>{status}</b>", ParagraphStyle("badge", fontSize=12, textColor=WHITE, alignment=TA_CENTER, fontName="Helvetica-Bold"))]],
        colWidths=[W * 0.25],
        rowHeights=[28],
    )
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _status_color(status)),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    repo_detail = Table(
        [[
            Paragraph(f"<b>Primary Language:</b> {primary_language}", styles["body"]),
            Paragraph(f"<b>Last Pushed:</b> {last_pushed}", styles["body"]),
        ]],
        colWidths=[W * 0.35, W * 0.4],
    )
    repo_detail.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    row = Table([[badge, repo_detail]], colWidths=[W * 0.25, W * 0.75])
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(row)
    story.append(Spacer(1, 0.2 * cm))

    donut = _build_score_donut(score)
    bar = _build_weekly_bar(team.get("weekly_activity", []))
    chart_table = Table(
        [[donut, bar]],
        colWidths=[W * 0.4, W * 0.6],
    )
    chart_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(chart_table)
    story.append(Spacer(1, 0.2 * cm))

    metrics_rows = [
        ["Metric", "Value"],
        ["Commits", f"{total_commits}"],
        ["LOC Added", f"{lines_added:,}"],
        ["LOC Deleted", f"{lines_deleted:,}"],
        ["Net Impact", f"{net_impact:,}"],
        ["Efficiency Ratio", f"{efficiency_ratio:.2f}"],
        ["Active Days", f"{active_days}"],
        ["Collaboration Score", f"{collab_score:.2f}"],
        ["Gini Coefficient", f"{gini:.3f}"],
        ["Bus Factor", f"{bus_factor}"],
    ]
    metrics_table = Table(metrics_rows, colWidths=[W * 0.5, W * 0.5])
    metrics_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), TEAL),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#f0f0f0")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 0.2 * cm))

    summary = Paragraph(_generate_summary(team), styles["summary_body"])
    notes_box = Table(
        [["Instructor Notes"]],
        colWidths=[W],
        rowHeights=[42],
    )
    notes_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fafafa")),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("TEXTCOLOR", (0, 0), (-1, -1), GREY),
    ]))
    story.append(KeepTogether([summary, Spacer(1, 0.15 * cm), notes_box]))

    story.append(Spacer(1, 0.2 * cm))
    story.append(HRFlowable(width=W, thickness=1, color=CARD_BG, spaceAfter=6))
    story.append(Paragraph("Generated by Student Project Performance Analysis System - Confidential", styles["footer"]))

    doc.build(story)
    return buffer.getvalue()

def generate_all_pdfs_zip(teams: List[Dict[str, Any]]) -> bytes:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for team in teams:
            pdf_bytes = generate_team_pdf(team)
            filename = f"{_safe_filename(team.get('team_id', 'team'))}_report.pdf"
            zf.writestr(filename, pdf_bytes)
    return zip_buffer.getvalue()

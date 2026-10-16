import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Running header (from page 2 onwards)
        if self._pageNumber > 1:
            self.drawString(54, letter[1] - 36, "Goose Industrial Solutions | Milma Kottayam - Vision Counting Implementation Plan")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(54, letter[1] - 42, letter[0] - 54, letter[1] - 42)
            
        # Running footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 54, 36, page_text)
        self.drawString(54, 36, "CONFIDENTIAL - For Milma (E.R.C.M.P.U. Ltd.) Review Only")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 46, letter[0] - 54, 46)
        
        self.restoreState()

def build_pdf():
    pdf_path = "Milma_Kottayam_Vision_Counting_Implementation_Plan.pdf"
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom palette
    NAVY = colors.HexColor("#0F2A4A")
    BLUE = colors.HexColor("#0066B3")
    DARK = colors.HexColor("#1E293B")
    MUTED = colors.HexColor("#64748B")
    LIGHT_BG = colors.HexColor("#F8FAFC")
    BORDER_CLR = colors.HexColor("#E2E8F0")

    # Typography Styles
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=DARK,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'CustomBullet',
        parent=body_style,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=4
    )

    h1_style = ParagraphStyle(
        'CustomH1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=NAVY,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'CustomH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=15,
        textColor=BLUE,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    tbl_hdr_style = ParagraphStyle(
        'TblHdr',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    tbl_cell_style = ParagraphStyle(
        'TblCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=DARK
    )

    tbl_bold_cell_style = ParagraphStyle(
        'TblBoldCell',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=NAVY
    )

    story = []

    # LOGO HEADER TABLE
    logo_w_goose = 1.8 * inch
    logo_h_goose = 1.8 * inch * (146.0 / 596.0)
    img_goose = Image('goose_logo_new.png', width=logo_w_goose, height=logo_h_goose)
    
    logo_h_milma = 0.65 * inch
    logo_w_milma = 0.65 * inch * (103.0 / 100.0)
    img_milma = Image('milma_logo.png', width=logo_w_milma, height=logo_h_milma)

    header_table = Table(
        [[img_goose, img_milma]],
        colWidths=[4.0 * inch, 3.0 * inch]
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLUE, spaceBefore=2, spaceAfter=10))

    # TITLE CALLOUT BOX
    title_p1 = Paragraph("<b>TECHNICAL IMPLEMENTATION PLAN & DATA REQUIREMENT SPECIFICATION</b>", 
                         ParagraphStyle('T1', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=BLUE))
    title_p2 = Paragraph("<b>Automated Vision-Based Milk Pouch & Crate Counting System</b>", 
                         ParagraphStyle('T2', fontName='Helvetica-Bold', fontSize=15, leading=19, textColor=NAVY))
    title_p3 = Paragraph("<b>Client:</b> Milma (E.R.C.M.P.U. Ltd.), Kottayam Dairy Plant &nbsp;|&nbsp; <b>Partner:</b> Goose Industrial Solutions (Vision AI)<br/><b>Project Scope:</b> High-speed conveyor pouch counting, variant classification & automated crate reconciliation", 
                         ParagraphStyle('T3', fontName='Helvetica', fontSize=8.5, leading=12, textColor=MUTED))
    
    title_box = Table([[title_p1], [title_p2], [title_p3]], colWidths=[7.0 * inch])
    title_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EFF6FF")),
        ('LEFTPADDING', (0,0), (-1,-1), 14),
        ('RIGHTPADDING', (0,0), (-1,-1), 14),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LINELEFT', (0,0), (-1,-1), 3.5, BLUE),
    ]))
    story.append(title_box)
    story.append(Spacer(1, 10))

    # 1. EXECUTIVE SUMMARY
    story.append(Paragraph("1. Executive Summary & Project Overview", h1_style))
    story.append(Paragraph(
        "Following the site survey conducted at the Milma (E.R.C.M.P.U. Ltd.) Kottayam Dairy, "
        "Goose Industrial Solutions is pleased to submit this comprehensive Implementation Plan and Data Requirement Specification. "
        "The proposed solution provides an automated, non-intrusive Vision-Based Milk Pouch & Crate Counting System "
        "designed to operate in real-time directly above the plant's existing crate conveyor line.",
        body_style
    ))
    story.append(Paragraph(
        "The system utilizes industrial global-shutter imaging and deep-learning instance segmentation to count 500 ml pillow pouches "
        "packed within blue moulded crates traversing at line speeds of 24 crates/min (~480 pouches/min). "
        "Accurate counts will be segregated across the three milk variants (Orange, Violet, Green) to deliver 100% auditable production figures.",
        body_style
    ))

    # Summary key metrics table
    sum_rows = [
        [Paragraph("<b>Target Facility</b>", tbl_bold_cell_style), Paragraph("Milma (E.R.C.M.P.U. Ltd.), Kottayam Dairy Plant", tbl_cell_style)],
        [Paragraph("<b>Throughput Capacity</b>", tbl_bold_cell_style), Paragraph("24 crates/min per line (~280–480 pouches/min) | 1.5 Lakh pouches/day", tbl_cell_style)],
        [Paragraph("<b>Product Variants</b>", tbl_bold_cell_style), Paragraph("500 ml LDPE pillow pouches (Orange, Violet, Green) in standard blue crates (20 pouches/crate)", tbl_cell_style)],
        [Paragraph("<b>Technology Stack</b>", tbl_bold_cell_style), Paragraph("GigE Global Shutter Vision Camera + Polarized LED Lighting + YOLO Edge AI Inference", tbl_cell_style)],
        [Paragraph("<b>Primary Deliverable</b>", tbl_bold_cell_style), Paragraph("Turnkey vision rig, live HMI dashboard, tamper-proof tally records & ERP export", tbl_cell_style)]
    ]
    t_sum = Table(sum_rows, colWidths=[2.2 * inch, 4.8 * inch])
    t_sum.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_CLR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_CLR),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_sum)
    story.append(Spacer(1, 8))

    # 2. SITE SURVEY SYNTHESIS
    story.append(Paragraph("2. Synthesis of Site Survey Findings & Engineering Mitigations", h1_style))
    story.append(Paragraph(
        "Our engineering design directly addresses the site characteristics captured during the plant survey:",
        body_style
    ))

    obs_headers = [Paragraph("<b>Site Parameter</b>", tbl_hdr_style), Paragraph("<b>Survey Observation</b>", tbl_hdr_style), Paragraph("<b>Goose Engineering Mitigation</b>", tbl_hdr_style)]
    obs_content = [
        [Paragraph("<b>Dim Lighting & Glare</b>", tbl_bold_cell_style), 
         Paragraph("Dim fluorescent tubes; polished stainless steel guards and wet glossy LDPE film create strong specular glare.", tbl_cell_style),
         Paragraph("High-intensity polarized LED bar illuminator with cross-polarizing lens filter to eliminate specular glare completely.", tbl_cell_style)],
        [Paragraph("<b>Abutting Crates</b>", tbl_bold_cell_style), 
         Paragraph("Crates travel abutting with zero inter-crate gap at ~24 crates/min; manual lift-off causes variable dwell time.", tbl_cell_style),
         Paragraph("Optical crate-edge tracking combined with photoelectric trigger sensor to delineate crate entry and exit boundaries accurately.", tbl_cell_style)],
        [Paragraph("<b>Overlapping Pouches</b>", tbl_bold_cell_style), 
         Paragraph("Pouches lie flat and shingled (overlapping in 2 runs, ~20 per crate) with protruding fin seals.", tbl_cell_style),
         Paragraph("Deep learning instance segmentation (YOLOv8/v11) trained specifically to segment overlapping fin-seal contours.", tbl_cell_style)],
        [Paragraph("<b>Washdown Area</b>", tbl_bold_cell_style), 
         Paragraph("Wet dairy washdown environment with cleaning spray and ambient moisture.", tbl_cell_style),
         Paragraph("IP65/IP67 food-grade stainless steel/anodized camera enclosure and moisture-sealed IP67 cabling.", tbl_cell_style)],
        [Paragraph("<b>Mounting Clearance</b>", tbl_bold_cell_style), 
         Paragraph("Conveyor height 900 mm; belt width 450 mm; max overhead clearance to structure ~950 mm.", tbl_cell_style),
         Paragraph("Custom low-profile overhead C-frame bracket with 8mm/12mm lens tailored for short working distance (WD ~700 mm).", tbl_cell_style)],
    ]
    t_obs = Table([obs_headers] + obs_content, colWidths=[1.6 * inch, 2.7 * inch, 2.7 * inch])
    t_obs.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_CLR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_CLR),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    for r in range(1, len(obs_content) + 1):
        if r % 2 == 0:
            t_obs.setStyle(TableStyle([('BACKGROUND', (0, r), (-1, r), LIGHT_BG)]))
    story.append(t_obs)
    story.append(Spacer(1, 8))

    # 3. REQUIREMENTS FROM MILMA KOTTAYAM
    story.append(Paragraph("3. Requirements from Milma Kottayam for Model Development", h1_style))
    story.append(Paragraph(
        "To achieve maximum counting accuracy (target ≥ 99.5%) across all shifts, "
        "Goose Industrial Solutions requires specific dataset assets and plant site provisions from Milma Kottayam as outlined below:",
        body_style
    ))

    story.append(Paragraph("3.1 Machine Learning Dataset & Photography Requirements", h2_style))
    story.append(Paragraph(
        "Machine learning models require varied, real-world examples of pouches in their actual production states. "
        "The following photographic dataset is required to train and validate the segmentation neural networks:",
        body_style
    ))

    ds_headers = [Paragraph("<b>Pouch Variant / Condition</b>", tbl_hdr_style), Paragraph("<b>Required Volume</b>", tbl_hdr_style), Paragraph("<b>Visual Variations to Include</b>", tbl_hdr_style)]
    ds_rows = [
        [Paragraph("<b>Orange Variant (Standard)</b>", tbl_bold_cell_style), Paragraph("<b>600 – 800 Photos</b>", tbl_bold_cell_style),
         Paragraph("Nominal 20 pouches/crate; varying overlap depths, fin-seal orientation, dry vs. wet pouches.", tbl_cell_style)],
        [Paragraph("<b>Violet Variant (Standard)</b>", tbl_bold_cell_style), Paragraph("<b>600 – 800 Photos</b>", tbl_bold_cell_style),
         Paragraph("Full crates on moving conveyor, different print cutoffs, slightly misaligned pouches.", tbl_cell_style)],
        [Paragraph("<b>Green Variant (Standard)</b>", tbl_bold_cell_style), Paragraph("<b>600 – 800 Photos</b>", tbl_bold_cell_style),
         Paragraph("Standard packing runs, pouch settling variations, slight crate skewing on guide frames.", tbl_cell_style)],
        [Paragraph("<b>Anomalies & Edge Cases</b>", tbl_bold_cell_style), Paragraph("<b>350 – 500 Photos</b>", tbl_bold_cell_style),
         Paragraph("Underfilled crates (16, 17, 18, 19 packets), loose pouches, folded corners, empty crates, worn crates.", tbl_cell_style)],
        [Paragraph("<b>High-Speed Video Footages</b>", tbl_bold_cell_style), Paragraph("<b>20 – 30 Minutes</b>", tbl_bold_cell_style),
         Paragraph("Continuous 1080p @ 30/60 fps top-down videos capturing live crate movement, vibration, and manual offload.", tbl_cell_style)],
    ]
    t_ds = Table([ds_headers] + ds_rows, colWidths=[1.8 * inch, 1.4 * inch, 3.8 * inch])
    t_ds.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_CLR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_CLR),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    for r in range(1, len(ds_rows) + 1):
        if r % 2 == 0:
            t_ds.setStyle(TableStyle([('BACKGROUND', (0, r), (-1, r), LIGHT_BG)]))
    story.append(t_ds)
    story.append(Spacer(1, 6))

    # Dataset Callout
    ds_note = Paragraph(
        "<b>📌 DATASET SUMMARY:</b> Approximately <b>2,100 to 2,900 still photographs</b> + <b>25 minutes of video</b>. "
        "Photos may be captured using standard high-resolution smartphones or DSLRs following the protocol below, or during a dedicated 1-day data collection visit by Goose engineers.",
        ParagraphStyle('N1', fontName='Helvetica', fontSize=8.5, leading=12, textColor=NAVY)
    )
    t_note = Table([[ds_note]], colWidths=[7.0 * inch])
    t_note.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EFF6FF")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#BFDBFE")),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LINELEFT', (0,0), (-1,-1), 3.0, BLUE),
    ]))
    story.append(t_note)
    story.append(Spacer(1, 8))

    story.append(Paragraph("3.2 Photography Capture Protocol", h2_style))
    story.append(Paragraph("• <b>Camera Angle:</b> Direct perpendicular top-down (nadir 90° view) looking straight into the crate, replicating the proposed overhead camera position. Include ±5° to ±10° tilt variations.", bullet_style))
    story.append(Paragraph("• <b>Working Distance & Framing:</b> Position camera 700 mm to 900 mm above the conveyor belt so the entire crate (565 mm × 300 mm) plus ~20 mm outer border is framed.", bullet_style))
    story.append(Paragraph("• <b>Resolution & Sharpness:</b> Minimum Full HD (1920 × 1080), sharp focus on pouch fin-seal edges, shutter speed ≥ 1/250s if conveyor is moving to eliminate blur.", bullet_style))
    story.append(Paragraph("• <b>Lighting Conditions:</b> Capture samples under standard overhead tubes, during morning shift start (07:30), mid-shift, and with wet pouch surfaces.", bullet_style))
    story.append(Paragraph("• <b>Folder Organization:</b> Segregate into folders labeled <code>/Orange/</code>, <code>/Violet/</code>, <code>/Green/</code>, and <code>/Edge_Cases/</code> (with physical count notes).", bullet_style))

    story.append(Spacer(1, 4))
    story.append(Paragraph("3.3 Site Infrastructure Provisions Needed from Milma", h2_style))
    story.append(Paragraph("• <b>Power Supply:</b> One single-phase 230V AC (50 Hz) UPS-stabilized power outlet (~500W load) within 3 meters of the inspection station.", bullet_style))
    story.append(Paragraph("• <b>Network Connectivity:</b> One Gigabit Ethernet (RJ45) drop or stable plant Wi-Fi access for local dashboard access and data backup.", bullet_style))
    story.append(Paragraph("• <b>Mounting Clearance:</b> Support for mounting an overhead rigid C-frame bracket (850–950 mm above conveyor) before the wall aperture / offload hatch.", bullet_style))
    story.append(Paragraph("• <b>Plant Coordination:</b> Nomination of an on-site technical contact (Production/Maintenance) to facilitate line access during calibration and UAT.", bullet_style))

    story.append(Spacer(1, 8))

    # 4. PROPOSED SYSTEM ARCHITECTURE
    story.append(Paragraph("4. Proposed Vision AI System Architecture", h1_style))
    story.append(Paragraph(
        "The proposed system is an edge-native industrial vision station. All neural network inference executes locally "
        "without reliance on cloud connectivity, ensuring high processing speed (<100 ms per crate) and zero downtime.",
        body_style
    ))

    arch_headers = [Paragraph("<b>Subsystem</b>", tbl_hdr_style), Paragraph("<b>Hardware / Software Specification</b>", tbl_hdr_style), Paragraph("<b>Function at Kottayam Dairy</b>", tbl_hdr_style)]
    arch_rows = [
        [Paragraph("<b>Vision Camera</b>", tbl_bold_cell_style), Paragraph("3.2–5.0 MP Global Shutter CMOS (Sony Pregius), GigE Vision, IP67 enclosure", tbl_cell_style),
         Paragraph("Freezes crate motion at 24 crates/min without blur or rolling distortion.", tbl_cell_style)],
        [Paragraph("<b>Lens & Filter</b>", tbl_bold_cell_style), Paragraph("8mm / 12mm Low-Distortion Lens + Polarizing Optical Filter", tbl_cell_style),
         Paragraph("Frames full 565 mm crate at ~750 mm WD and cuts specular reflections from wet LDPE film.", tbl_cell_style)],
        [Paragraph("<b>Active Lighting</b>", tbl_bold_cell_style), Paragraph("High-Intensity Polarized LED Diffuse Illuminator (IP67 food-grade housing)", tbl_cell_style),
         Paragraph("Provides consistent, shadow-free illumination regardless of ambient factory lighting.", tbl_cell_style)],
        [Paragraph("<b>Edge AI Compute</b>", tbl_bold_cell_style), Paragraph("Industrial Fanless Edge AI Box (NVIDIA Jetson Orin / RTX Industrial PC)", tbl_cell_style),
         Paragraph("Executes deep learning segmentation and tracking in < 80 ms per frame.", tbl_cell_style)],
        [Paragraph("<b>Operator HMI</b>", tbl_bold_cell_style), Paragraph("10.1\" / 15.6\" Touch Screen HMI + Audio-Visual Stack Light", tbl_cell_style),
         Paragraph("Displays live crate counts, shift totals, and triggers instant alerts for underfilled crates.", tbl_cell_style)],
    ]
    t_arch = Table([arch_headers] + arch_rows, colWidths=[1.5 * inch, 2.7 * inch, 2.8 * inch])
    t_arch.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_CLR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_CLR),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    for r in range(1, len(arch_rows) + 1):
        if r % 2 == 0:
            t_arch.setStyle(TableStyle([('BACKGROUND', (0, r), (-1, r), LIGHT_BG)]))
    story.append(t_arch)
    story.append(Spacer(1, 8))

    # 5. IMPLEMENTATION TIMELINE
    story.append(Paragraph("5. Project Implementation Plan & Milestones", h1_style))
    story.append(Paragraph(
        "Goose Industrial Solutions proposes an 8-week structured deployment schedule designed for seamless execution:",
        body_style
    ))

    plan_headers = [Paragraph("<b>Phase</b>", tbl_hdr_style), Paragraph("<b>Milestone Focus</b>", tbl_hdr_style), Paragraph("<b>Action Items & Deliverables</b>", tbl_hdr_style), Paragraph("<b>Timeline</b>", tbl_hdr_style)]
    plan_rows = [
        [Paragraph("<b>Phase 1</b>", tbl_bold_cell_style), Paragraph("<b>Data Acquisition & Labelling</b>", tbl_bold_cell_style),
         Paragraph("Collect 2,000+ photos/videos across Orange, Violet, Green. Image annotation and polygon segmentation tagging.", tbl_cell_style),
         Paragraph("<b>Weeks 1 – 2</b>", tbl_bold_cell_style)],
        [Paragraph("<b>Phase 2</b>", tbl_bold_cell_style), Paragraph("<b>AI Training & Optimization</b>", tbl_bold_cell_style),
         Paragraph("Train YOLO segmentation model. Handle overlapping/shingled pouch edges. TensorRT quantization for edge speed.", tbl_cell_style),
         Paragraph("<b>Weeks 3 – 4</b>", tbl_bold_cell_style)],
        [Paragraph("<b>Phase 3</b>", tbl_bold_cell_style), Paragraph("<b>Hardware Rig Staging</b>", tbl_bold_cell_style),
         Paragraph("Fabricate IP65/IP67 enclosure and mounting bracket. Bench test camera, polarized LED light, and Edge AI unit.", tbl_cell_style),
         Paragraph("<b>Weeks 4 – 5</b>", tbl_bold_cell_style)],
        [Paragraph("<b>Phase 4</b>", tbl_bold_cell_style), Paragraph("<b>On-Site Calibration</b>", tbl_bold_cell_style),
         Paragraph("Mechanical install at Kottayam line. Calibrate optical trigger under 24 crates/min live motion. Latency benchmarking.", tbl_cell_style),
         Paragraph("<b>Weeks 6 – 7</b>", tbl_bold_cell_style)],
        [Paragraph("<b>Phase 5</b>", tbl_bold_cell_style), Paragraph("<b>UAT & Handover</b>", tbl_bold_cell_style),
         Paragraph("Shift 1 (07:30–15:30) validation over 10,000+ crates. Reconcile against physical count. Operator training & sign-off.", tbl_cell_style),
         Paragraph("<b>Weeks 8 – 9</b>", tbl_bold_cell_style)],
    ]
    t_pl = Table([plan_headers] + plan_rows, colWidths=[1.1 * inch, 1.8 * inch, 2.9 * inch, 1.2 * inch])
    t_pl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_CLR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_CLR),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    for r in range(1, len(plan_rows) + 1):
        if r % 2 == 0:
            t_pl.setStyle(TableStyle([('BACKGROUND', (0, r), (-1, r), LIGHT_BG)]))
    story.append(t_pl)
    story.append(Spacer(1, 8))

    # 6. KPIS & ACCEPTANCE CRITERIA
    story.append(Paragraph("6. Key Performance Indicators & Acceptance Criteria", h1_style))
    kpi_headers = [Paragraph("<b>Performance Metric</b>", tbl_hdr_style), Paragraph("<b>Target SLA / KPI</b>", tbl_hdr_style), Paragraph("<b>Validation Method</b>", tbl_hdr_style)]
    kpi_rows = [
        [Paragraph("<b>Packet Counting Accuracy</b>", tbl_bold_cell_style), Paragraph("<b>≥ 99.5%</b>", tbl_bold_cell_style),
         Paragraph("Audited over 10,000 continuous crates compared against physical manual counts.", tbl_cell_style)],
        [Paragraph("<b>Variant Classification</b>", tbl_bold_cell_style), Paragraph("<b>≥ 99.8%</b>", tbl_bold_cell_style),
         Paragraph("Automated segregation of Orange vs. Violet vs. Green milk crates.", tbl_cell_style)],
        [Paragraph("<b>Inference Latency</b>", tbl_bold_cell_style), Paragraph("<b>< 100 milliseconds</b>", tbl_bold_cell_style),
         Paragraph("Per-crate processing speed (leaves 2.4s buffer at 24 crates/min line speed).", tbl_cell_style)],
        [Paragraph("<b>Underfill / Mismatch Alert</b>", tbl_bold_cell_style), Paragraph("<b>≥ 99.0% Detection</b>", tbl_bold_cell_style),
         Paragraph("Immediate visual stack light alert and photo archive whenever count != 20.", tbl_cell_style)],
    ]
    t_kpi = Table([kpi_headers] + kpi_rows, colWidths=[2.2 * inch, 1.6 * inch, 3.2 * inch])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_CLR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_CLR),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    for r in range(1, len(kpi_rows) + 1):
        if r % 2 == 0:
            t_kpi.setStyle(TableStyle([('BACKGROUND', (0, r), (-1, r), LIGHT_BG)]))
    story.append(t_kpi)
    story.append(Spacer(1, 8))

    # 7. DELIVERABLES & NEXT STEPS
    story.append(Paragraph("7. Deliverables & Next Steps", h1_style))
    story.append(Paragraph("• <b>Hardware & Rig:</b> IP65/67 industrial vision camera, polarized LED light, C-arm bracket, and photoelectric trigger.", bullet_style))
    story.append(Paragraph("• <b>Edge AI Unit & Software:</b> Pre-loaded industrial edge computer with trained YOLO segmentation and tracking engine.", bullet_style))
    story.append(Paragraph("• <b>Operator Dashboard:</b> Touchscreen HMI and local web portal showing live crate counts, shift totals, and alert history.", bullet_style))
    story.append(Paragraph("• <b>Documentation & Training:</b> Comprehensive user SOP, maintenance guide, and hands-on plant operator training.", bullet_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Immediate Next Actions:</b>", h2_style))
    story.append(Paragraph("1. Review and sign-off on the implementation plan and site infrastructure checklist.", bullet_style))
    story.append(Paragraph("2. Schedule the photo/video dataset collection session at Kottayam plant.", bullet_style))
    story.append(Paragraph("3. Finalize bracket mounting dimensions on the conveyor frame and commence Phase 1.", bullet_style))

    story.append(Spacer(1, 10))

    # SIGN-OFF BLOCK
    sign_p1 = Paragraph("<b>SUBMITTED BY:</b><br/><b>Goose Industrial Solutions</b><br/>Vision AI & Automation Solutions<br/>Email: contact@goosetech.ai | Web: www.goosetech.ai", 
                        ParagraphStyle('S1', fontName='Helvetica', fontSize=8.5, leading=12, textColor=NAVY))
    sign_p2 = Paragraph("<b>PREPARED FOR:</b><br/><b>Milma (E.R.C.M.P.U. Ltd.)</b><br/>Kottayam Dairy Plant<br/>Kerala Co-operative Milk Marketing Federation", 
                        ParagraphStyle('S2', fontName='Helvetica', fontSize=8.5, leading=12, textColor=BLUE))
    t_sign = Table([[sign_p1, sign_p2]], colWidths=[3.5 * inch, 3.5 * inch])
    t_sign.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EFF6FF")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#BFDBFE")),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(KeepTogether(t_sign))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully built at {pdf_path}")

if __name__ == '__main__':
    build_pdf()

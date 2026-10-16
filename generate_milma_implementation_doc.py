import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn
import os

def create_milma_implementation_doc():
    doc = docx.Document()

    # Page Margins (0.75 in)
    for s in doc.sections:
        s.top_margin = Inches(0.75)
        s.bottom_margin = Inches(0.75)
        s.left_margin = Inches(0.75)
        s.right_margin = Inches(0.75)

    # Styles & Colors
    NAVY_HEX = "0F2A4A"        # Primary Goose Navy
    BLUE_HEX = "0066B3"        # Milma Royal Blue
    ACCENT_HEX = "0284C7"      # Sky Blue Accent
    BG_LIGHT_HEX = "F8FAFC"    # Clean light slate background
    BG_CARD_HEX = "EFF6FF"     # Subtle blue tint
    BORDER_HEX = "CBD5E1"      # Subtle border
    TEXT_DARK_HEX = "1E293B"    # Slate dark 900
    TEXT_MUTED_HEX = "64748B"   # Slate 500

    def hex_to_rgb(h):
        return RGBColor(*(int(h[i:i+2], 16) for i in (0, 2, 4)))

    NAVY = hex_to_rgb(NAVY_HEX)
    BLUE = hex_to_rgb(BLUE_HEX)
    DARK_TEXT = hex_to_rgb(TEXT_DARK_HEX)
    MUTED_TEXT = hex_to_rgb(TEXT_MUTED_HEX)

    # Configure Normal Style font
    style_normal = doc.styles['Normal']
    font = style_normal.font
    font.name = 'Calibri'
    font.size = Pt(10.5)
    font.color.rgb = DARK_TEXT

    # XML Helper Functions
    def set_cell_background(cell, hex_color):
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
        cell._tc.get_or_add_tcPr().append(shd)

    def set_cell_margins(cell, top=120, bottom=120, left=180, right=180):
        tcPr = cell._tc.get_or_add_tcPr()
        tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}>'
                          f'<w:top w:w="{top}" w:type="dxa"/>'
                          f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
                          f'<w:left w:w="{left}" w:type="dxa"/>'
                          f'<w:right w:w="{right}" w:type="dxa"/>'
                          f'</w:tcMar>')
        tcPr.append(tcMar)

    def set_table_borders(table, border_color=BORDER_HEX, top_color=NAVY_HEX):
        tblPr = table._tbl.tblPr
        borders = parse_xml(f'<w:tblBorders {nsdecls("w")}>'
                            f'<w:top w:val="single" w:sz="6" w:space="0" w:color="{top_color}"/>'
                            f'<w:bottom w:val="single" w:sz="6" w:space="0" w:color="{top_color}"/>'
                            f'<w:left w:val="none"/>'
                            f'<w:right w:val="none"/>'
                            f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="{border_color}"/>'
                            f'<w:insideV w:val="none"/>'
                            f'</w:tblBorders>')
        tblPr.append(borders)

    # Header with Logos
    header_tbl = doc.add_table(rows=1, cols=2)
    header_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    header_tbl.autofit = False
    header_tbl.rows[0].cells[0].width = Inches(4.5)
    header_tbl.rows[0].cells[1].width = Inches(2.5)

    c0 = header_tbl.rows[0].cells[0]
    c1 = header_tbl.rows[0].cells[1]
    c0.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    c1.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    p0 = c0.paragraphs[0]
    p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
    if os.path.exists('goose_logo_new.png'):
        p0.add_run().add_picture('goose_logo_new.png', width=Inches(1.85))
    else:
        r = p0.add_run("GOOSE INDUSTRIAL SOLUTIONS")
        r.font.bold = True
        r.font.size = Pt(16)
        r.font.color.rgb = NAVY

    p1 = c1.paragraphs[0]
    p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if os.path.exists('milma_logo.png'):
        p1.add_run().add_picture('milma_logo.png', width=Inches(0.95))
    else:
        r = p1.add_run("MILMA KOTTAYAM")
        r.font.bold = True
        r.font.size = Pt(14)
        r.font.color.rgb = BLUE

    # Divider Line below header
    p_div = doc.add_paragraph()
    p_div.paragraph_format.space_before = Pt(4)
    p_div.paragraph_format.space_after = Pt(16)
    pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="14" w:space="1" w:color="{BLUE_HEX}"/></w:pBdr>')
    p_div._p.get_or_add_pPr().append(pBdr)

    # Document Header Title Block
    title_tbl = doc.add_table(rows=1, cols=1)
    title_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    title_tbl.autofit = False
    title_tbl.rows[0].cells[0].width = Inches(7.0)
    c_title = title_tbl.rows[0].cells[0]
    set_cell_background(c_title, BG_CARD_HEX)
    set_cell_margins(c_title, top=180, bottom=180, left=220, right=220)

    # Border for title box
    tcPr = c_title._tc.get_or_add_tcPr()
    tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}>'
                          f'<w:top w:val="none"/>'
                          f'<w:left w:val="single" w:sz="24" w:space="0" w:color="{BLUE_HEX}"/>'
                          f'<w:bottom w:val="none"/>'
                          f'<w:right w:val="none"/>'
                          f'</w:tcBorders>')
    tcPr.append(tcBorders)

    pt1 = c_title.paragraphs[0]
    pt1.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pt1.paragraph_format.space_after = Pt(2)
    rt1 = pt1.add_run("TECHNICAL IMPLEMENTATION PLAN & DATA REQUIREMENT SPECIFICATION")
    rt1.font.bold = True
    rt1.font.size = Pt(10)
    rt1.font.color.rgb = BLUE

    pt2 = c_title.add_paragraph()
    pt2.paragraph_format.space_after = Pt(4)
    rt2 = pt2.add_run("Automated Vision-Based Milk Pouch & Crate Counting System")
    rt2.font.bold = True
    rt2.font.size = Pt(16)
    rt2.font.color.rgb = NAVY

    pt3 = c_title.add_paragraph()
    pt3.paragraph_format.space_after = Pt(0)
    rt3 = pt3.add_run("Prepared for: Milma (E.R.C.M.P.U. Ltd.), Kottayam Dairy Plant | Prepared by: Goose Industrial Solutions (Vision AI Team)\nProject Scope: Real-time pouch detection, segregated variant counting & crate validation on conveyor line")
    rt3.font.size = Pt(9.5)
    rt3.font.color.rgb = MUTED_TEXT

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # Helper function for Section Headings
    def add_section_heading(title_text, sec_num=None):
        h = doc.add_paragraph()
        h.paragraph_format.space_before = Pt(16)
        h.paragraph_format.space_after = Pt(6)
        h.paragraph_format.keep_with_next = True
        
        full_title = f"{sec_num}. {title_text}" if sec_num else title_text
        run = h.add_run(full_title)
        run.font.bold = True
        run.font.size = Pt(13)
        run.font.color.rgb = NAVY
        
        # Subtle bottom border under section heading
        pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="6" w:space="2" w:color="{BORDER_HEX}"/></w:pBdr>')
        h._p.get_or_add_pPr().append(pBdr)
        return h

    def add_subsection_heading(title_text):
        h = doc.add_paragraph()
        h.paragraph_format.space_before = Pt(10)
        h.paragraph_format.space_after = Pt(3)
        h.paragraph_format.keep_with_next = True
        run = h.add_run(title_text)
        run.font.bold = True
        run.font.size = Pt(11)
        run.font.color.rgb = BLUE
        return h

    def add_callout(text, title="CRITICAL REQUIREMENT", bg_hex=BG_CARD_HEX, border_hex=BLUE_HEX):
        tbl = doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        tbl.rows[0].cells[0].width = Inches(7.0)
        cell = tbl.rows[0].cells[0]
        set_cell_background(cell, bg_hex)
        set_cell_margins(cell, top=100, bottom=100, left=150, right=150)
        
        tcPr = cell._tc.get_or_add_tcPr()
        tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}>'
                              f'<w:top w:val="none"/>'
                              f'<w:left w:val="single" w:sz="18" w:space="0" w:color="{border_hex}"/>'
                              f'<w:bottom w:val="none"/>'
                              f'<w:right w:val="none"/>'
                              f'</w:tcBorders>')
        tcPr.append(tcBorders)
        
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(2)
        r_title = p.add_run(f"📌 {title}: ")
        r_title.font.bold = True
        r_title.font.size = Pt(10)
        r_title.font.color.rgb = hex_to_rgb(border_hex)
        
        r_text = p.add_run(text)
        r_text.font.size = Pt(10)
        r_text.font.color.rgb = DARK_TEXT
        
        p_sp = doc.add_paragraph()
        p_sp.paragraph_format.space_after = Pt(4)

    # SECTION 1: EXECUTIVE SUMMARY
    add_section_heading("Executive Summary & Project Overview", "1")
    p = doc.add_paragraph(
        "Following the comprehensive site survey conducted at Milma (E.R.C.M.P.U. Ltd.) Kottayam Dairy, "
        "Goose Industrial Solutions is pleased to submit this detailed Implementation Plan and Technical Requirement Specification. "
        "The objective of this project is to develop and deploy an automated, non-intrusive Vision-Based Milk Pouch & Crate Counting System "
        "capable of providing real-time, segregated packet production metrics with maximum operational accuracy."
    )
    p.paragraph_format.space_after = Pt(6)

    p = doc.add_paragraph(
        "The system replaces error-prone manual tallies with high-speed industrial computer vision and deep learning instance segmentation, "
        "accurately counting 500 ml pillow pouches packed in blue plastic crates traversing the chain conveyor at line speeds of up to 24 crates per minute (~480 pouches/min). "
        "Production counts will be categorized automatically across three distinct milk variants (Orange, Violet, and Green), providing transparent, audit-ready production data."
    )
    p.paragraph_format.space_after = Pt(8)

    # Summary table
    t_sum = doc.add_table(rows=5, cols=2)
    t_sum.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_sum.autofit = False
    set_table_borders(t_sum)
    widths = [Inches(2.5), Inches(4.5)]
    for row in t_sum.rows:
        for idx, w in enumerate(widths):
            row.cells[idx].width = w
            set_cell_margins(row.cells[idx], top=70, bottom=70, left=120, right=120)

    sum_data = [
        ("Client & Installation Site", "Milma (E.R.C.M.P.U. Ltd.), Kottayam Dairy Plant"),
        ("Primary Goal", "Real-time automated packet counting per crate & shift total segregated by variant"),
        ("Throughput Capacity", "24 crates/min per line (~280–480 pouches/min), ~150,000 packets/day plant throughput"),
        ("Product Scope", "500 ml LDPE pillow pouches (Orange, Violet, Green) in standard blue moulded crates"),
        ("Core Technology", "Industrial Global Shutter Vision Camera + Polarized LED Lighting + YOLO Edge AI Segmentation")
    ]
    for idx, (label, val) in enumerate(sum_data):
        row = t_sum.rows[idx]
        set_cell_background(row.cells[0], BG_LIGHT_HEX)
        r0 = row.cells[0].paragraphs[0].add_run(label)
        r0.font.bold = True
        r0.font.size = Pt(9.5)
        r1 = row.cells[1].paragraphs[0].add_run(val)
        r1.font.size = Pt(9.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # SECTION 2: SYNTHESIS OF SITE SURVEY FINDINGS & TECHNICAL CHALLENGES
    add_section_heading("Synthesis of Site Survey Findings & Engineering Solutions", "2")
    p = doc.add_paragraph(
        "Based on the site survey report, several key mechanical, optical, and operational characteristics "
        "have been identified and factored into our system design:"
    )
    p.paragraph_format.space_after = Pt(6)

    t_obs = doc.add_table(rows=6, cols=3)
    t_obs.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_obs.autofit = False
    set_table_borders(t_obs)
    obs_widths = [Inches(1.8), Inches(2.6), Inches(2.6)]
    for row in t_obs.rows:
        for idx, w in enumerate(obs_widths):
            row.cells[idx].width = w
            set_cell_margins(row.cells[idx], top=80, bottom=80, left=100, right=100)

    # Header Row
    hdr = t_obs.rows[0]
    headers = ["Survey Parameter", "Observed Site Condition", "Goose Engineering Solution"]
    for idx, h_text in enumerate(headers):
        set_cell_background(hdr.cells[idx], NAVY_HEX)
        rh = hdr.cells[idx].paragraphs[0].add_run(h_text)
        rh.font.bold = True
        rh.font.color.rgb = RGBColor(255, 255, 255)
        rh.font.size = Pt(9.5)

    obs_data = [
        ("Lighting & Specular Glare", 
         "Dim ambient fluorescent tubes; polished stainless steel guards and wet glossy film create harsh specular glare.",
         "High-intensity polarized industrial LED bar lights with cross-polarizing lens filter to eliminate surface glare entirely."),
        ("Crate Spacing & Motion", 
         "Crates travel abutting with zero inter-crate gap at ~24 crates/min; manual lift-off causes variable dwell time.",
         "Continuous optical edge tracking + photoelectric trigger sensor to precisely delineate crate entry, boundaries, and exit."),
        ("Pouch Packing Arrangement", 
         "Packets lie flat and shingled (overlapping in 2 runs, ~20 per crate); touching runs and protruding fin seals.",
         "Deep learning instance segmentation (YOLO-based) trained to isolate overlapping boundaries and fin-seal geometries."),
        ("Dairy Environment", 
         "Wet washdown dairy processing area with humidity and daily cleaning cycles.",
         "IP65/IP67 stainless steel / anodized sealed enclosure for camera, lens, and lighting; moisture-proof industrial connectors."),
        ("Physical Clearance", 
         "Conveyor height: 900 mm; belt width: 450 mm; max overhead clearance to structure: ~950 mm.",
         "Compact custom overhead C-frame bracket with 8mm/12mm wide-angle lens optimized for short working distance (WD ~600–750 mm).")
    ]

    for idx, (p_name, p_obs, p_sol) in enumerate(obs_data):
        row = t_obs.rows[idx + 1]
        if idx % 2 == 1:
            set_cell_background(row.cells[0], BG_LIGHT_HEX)
            set_cell_background(row.cells[1], BG_LIGHT_HEX)
            set_cell_background(row.cells[2], BG_LIGHT_HEX)
        r0 = row.cells[0].paragraphs[0].add_run(p_name)
        r0.font.bold = True
        r0.font.size = Pt(9)
        r1 = row.cells[1].paragraphs[0].add_run(p_obs)
        r1.font.size = Pt(9)
        r2 = row.cells[2].paragraphs[0].add_run(p_sol)
        r2.font.size = Pt(9)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # SECTION 3: REQUIREMENTS FROM MILMA KOTTAYAM
    add_section_heading("Project Requirements & Inputs from Milma Kottayam", "3")
    p = doc.add_paragraph(
        "To ensure high counting accuracy (target ≥ 99.5%) and robust model performance under production conditions, "
        "Goose Industrial Solutions requires specific dataset assets and plant site provisions from Milma Kottayam."
    )
    p.paragraph_format.space_after = Pt(6)

    add_subsection_heading("3.1 Machine Learning Dataset & Photography Requirements")
    p = doc.add_paragraph(
        "Because milk pouches are pliable, glossy, and arranged in shingled/overlapping layers, a robust machine learning model "
        "requires photographic data captured directly from the plant floor. The table below specifies the exact photo dataset needed:"
    )
    p.paragraph_format.space_after = Pt(6)

    # Dataset table
    t_ds = doc.add_table(rows=6, cols=3)
    t_ds.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_ds.autofit = False
    set_table_borders(t_ds)
    ds_widths = [Inches(1.8), Inches(1.5), Inches(3.7)]
    for row in t_ds.rows:
        for idx, w in enumerate(ds_widths):
            row.cells[idx].width = w
            set_cell_margins(row.cells[idx], top=70, bottom=70, left=100, right=100)

    ds_hdr = t_ds.rows[0]
    ds_headers = ["Pouch Variant / Condition", "Recommended Quantity", "Specific Visual Variations Needed"]
    for idx, h_text in enumerate(ds_headers):
        set_cell_background(ds_hdr.cells[idx], NAVY_HEX)
        rh = ds_hdr.cells[idx].paragraphs[0].add_run(h_text)
        rh.font.bold = True
        rh.font.color.rgb = RGBColor(255, 255, 255)
        rh.font.size = Pt(9.5)

    ds_data = [
        ("Orange Variant (Standard)", "600 – 800 Photos", 
         "Normal shingled runs (nominal 20 pouches/crate), varying overlap depths, fin-seal orientation, dry and wet pouches."),
        ("Violet Variant (Standard)", "600 – 800 Photos", 
         "Standard packing layouts, different print alignment on film, partial overlaps, full crates on moving conveyor."),
        ("Green Variant (Standard)", "600 – 800 Photos", 
         "Standard packing runs, pouch settling variations, slight crate skewing on outer frame."),
        ("Anomalies & Edge Cases", "350 – 500 Photos", 
         "Underfilled crates (16, 17, 18, 19 packets), overfilled/tilted pouches, folded/creased pouches, empty crates, worn crates."),
        ("High-Speed Video Footages", "20 – 30 Minutes Total", 
         "Continuous top-down videos (1080p @ 30/60 fps) across morning shift (07:30 start) and mid-shift to capture natural crate flow & vibration.")
    ]

    for idx, (var_name, qty, desc) in enumerate(ds_data):
        row = t_ds.rows[idx + 1]
        if idx % 2 == 1:
            set_cell_background(row.cells[0], BG_LIGHT_HEX)
            set_cell_background(row.cells[1], BG_LIGHT_HEX)
            set_cell_background(row.cells[2], BG_LIGHT_HEX)
        r0 = row.cells[0].paragraphs[0].add_run(var_name)
        r0.font.bold = True
        r0.font.size = Pt(9)
        r1 = row.cells[1].paragraphs[0].add_run(qty)
        r1.font.bold = True
        r1.font.color.rgb = BLUE
        r1.font.size = Pt(9)
        r2 = row.cells[2].paragraphs[0].add_run(desc)
        r2.font.size = Pt(9)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    add_callout(
        "Total Target Dataset: Approximately 2,100 to 2,900 still images + 25 minutes of continuous video. "
        "Photos can be captured using a standard smartphone or DSLR following the protocol below, or by Goose engineers during a 1-day staging visit.",
        title="DATASET SUMMARY"
    )

    add_subsection_heading("3.2 Protocol for Photo & Video Capture")
    protocol_points = [
        ("Camera Perspective & Angle: ", "Capture directly from above (perpendicular 90° nadir angle), looking straight down into the crate. This simulates the fixed industrial camera position. Include slight angular shifts (5°–10°) to train robustness against slight crate tilting."),
        ("Camera Distance & Frame: ", "Position the camera approximately 700 mm to 900 mm above the crate belt so the full 565 mm × 300 mm crate plus a slight margin is clearly visible."),
        ("Image Clarity & Motion: ", "Ensure crisp focus on the pouches and fin seals. If conveyor is running, use a fast shutter speed (minimum 1/250s) to avoid motion blur."),
        ("Lighting & Glare Diversity: ", "Capture samples under existing tube lighting, with overhead lights switched on and during natural morning shift transitions."),
        ("Dataset Segregation: ", "Organize files into labeled folders: '/Orange/', '/Violet/', '/Green/', and '/Edge_Cases/' (indicating actual packet counts for validation).")
    ]
    for bold_txt, norm_txt in protocol_points:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(3)
        r_b = bp.add_run(bold_txt)
        r_b.font.bold = True
        r_b.font.size = Pt(9.5)
        r_n = bp.add_run(norm_txt)
        r_n.font.size = Pt(9.5)

    add_subsection_heading("3.3 Site Infrastructure & Mechanical Provisions Needed from Milma")
    infra_points = [
        ("Regulated Electrical Power: ", "One single-phase 230V AC (50 Hz) UPS-backed power socket (~500W load) within 3 meters of the designated conveyor inspection station."),
        ("Network Connectivity: ", "One Gigabit Ethernet (RJ45) LAN port or dedicated plant Wi-Fi access near the line for edge system dashboard access and automated data backup."),
        ("Overhead Mechanical Mount: ", "Permission and support to mount an overhead rigid C-arm bracket (stainless steel or heavy-duty aluminum) at 850–950 mm elevation above the conveyor, positioned before the wall hatch / manual lift-off area."),
        ("Line Coordinator & Access: ", "Nomination of an on-site technical point of contact (Production/Maintenance) to assist during on-site calibration, trial runs, and operator training.")
    ]
    for bold_txt, norm_txt in infra_points:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(3)
        r_b = bp.add_run(bold_txt)
        r_b.font.bold = True
        r_b.font.size = Pt(9.5)
        r_n = bp.add_run(norm_txt)
        r_n.font.size = Pt(9.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # SECTION 4: PROPOSED SYSTEM ARCHITECTURE & HARDWARE DESIGN
    add_section_heading("Proposed Vision AI System Architecture", "4")
    p = doc.add_paragraph(
        "The proposed architecture utilizes an edge-native design, executing all deep-learning inferences locally on high-performance "
        "hardware to ensure ultra-low latency (<100 ms per crate) and uninterrupted operation even in case of external network outages."
    )
    p.paragraph_format.space_after = Pt(6)

    # Architecture Table
    t_arch = doc.add_table(rows=6, cols=3)
    t_arch.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_arch.autofit = False
    set_table_borders(t_arch)
    arch_widths = [Inches(1.8), Inches(2.2), Inches(3.0)]
    for row in t_arch.rows:
        for idx, w in enumerate(arch_widths):
            row.cells[idx].width = w
            set_cell_margins(row.cells[idx], top=70, bottom=70, left=100, right=100)

    arch_hdr = t_arch.rows[0]
    arch_headers = ["Subsystem Component", "Proposed Specification", "Functional Role in Kottayam Plant"]
    for idx, h_text in enumerate(arch_headers):
        set_cell_background(arch_hdr.cells[idx], NAVY_HEX)
        rh = arch_hdr.cells[idx].paragraphs[0].add_run(h_text)
        rh.font.bold = True
        rh.font.color.rgb = RGBColor(255, 255, 255)
        rh.font.size = Pt(9.5)

    arch_data = [
        ("Industrial Vision Camera", "3.2 MP – 5.0 MP Global Shutter CMOS (Sony Pregius), GigE Vision, IP67 enclosure",
         "Captures crystal-clear frames without motion blur as crates travel at 24 crates/min."),
        ("Optical Lens & Filter", "8mm / 12mm Low-Distortion C-Mount Lens + Linear / Circular Polarizer",
         "Delivers full-crate field of view at ~750 mm WD and eliminates specular reflections from wet LDPE."),
        ("Industrial Lighting", "High-Intensity Polarized LED Diffuse Bar/Dome Light (Food-grade IP67 housing)",
         "Overpowers dim ambient fluorescent tubes, creating uniform illumination across all shifts."),
        ("Edge AI Computing Unit", "Industrial Embedded AI Box (NVIDIA Jetson Orin / Industrial PC, Fanless IP50/65)",
         "Executes real-time YOLOv8/v11 instance segmentation and crate tracking in under 80 ms per frame."),
        ("Operator Dashboard & HMI", "10.1\" / 15.6\" Touch HMI Display with Local Web Dashboard & Audio-Visual Stack Light",
         "Displays live packet counts, variant status, shift totals, and triggers immediate alarms if a crate is underfilled.")
    ]

    for idx, (comp, spec, role) in enumerate(arch_data):
        row = t_arch.rows[idx + 1]
        if idx % 2 == 1:
            set_cell_background(row.cells[0], BG_LIGHT_HEX)
            set_cell_background(row.cells[1], BG_LIGHT_HEX)
            set_cell_background(row.cells[2], BG_LIGHT_HEX)
        r0 = row.cells[0].paragraphs[0].add_run(comp)
        r0.font.bold = True
        r0.font.size = Pt(9)
        r1 = row.cells[1].paragraphs[0].add_run(spec)
        r1.font.size = Pt(9)
        r2 = row.cells[2].paragraphs[0].add_run(role)
        r2.font.size = Pt(9)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # Software Logic
    add_subsection_heading("4.1 Computer Vision & Machine Learning Pipeline")
    pipeline_steps = [
        ("Step 1: Crate Entry Detection & Spatial Triggering — ", "An optical retro-reflective sensor or continuous software edge-detector identifies the entry of a crate into the inspection zone, initializing a unique Crate ID."),
        ("Step 2: Region of Interest (ROI) Alignment & Boundary Delineation — ", "The system locks onto the crate perimeter (565 mm × 300 mm), isolating internal contents even when consecutive crates travel abutting each other."),
        ("Step 3: Deep Learning Instance Segmentation — ", "A custom YOLO-based segmentation neural network isolates each individual 500 ml pillow pouch, identifying overlapping fin seals, folded corners, and lay-flat body boundaries."),
        ("Step 4: Variant Classification — ", "A multi-spectral color classification algorithm categorizes the crate batch into Orange, Violet, or Green milk with 99.8%+ confidence."),
        ("Step 5: Counting Logic & Validation — ", "Total detected pouch instances are tallied against the nominal target (20 pouches). If count == 20, crate is marked 'PASSED'; if count < 20 or > 20, the crate is flagged with an immediate visual alert and timestamped audit snapshot."),
        ("Step 6: Shift Aggregation & Cloud / ERP Sync — ", "Counts are committed to a tamper-proof local SQLite/PostgreSQL database and forwarded to Milma's central reporting dashboard via REST API / MQTT.")
    ]
    for step_title, step_desc in pipeline_steps:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(3)
        r_b = bp.add_run(step_title)
        r_b.font.bold = True
        r_b.font.size = Pt(9.5)
        r_n = bp.add_run(step_desc)
        r_n.font.size = Pt(9.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # SECTION 5: IMPLEMENTATION PLAN & TIMELINE
    add_section_heading("Project Implementation Plan & Milestone Roadmap", "5")
    p = doc.add_paragraph(
        "Goose Industrial Solutions proposes a structured 8-week implementation timeline from dataset receipt to full production sign-off. "
        "The project is structured into five distinct phases to ensure minimal disruption to daily plant operations:"
    )
    p.paragraph_format.space_after = Pt(6)

    t_plan = doc.add_table(rows=6, cols=4)
    t_plan.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_plan.autofit = False
    set_table_borders(t_plan)
    plan_widths = [Inches(1.2), Inches(1.8), Inches(2.8), Inches(1.2)]
    for row in t_plan.rows:
        for idx, w in enumerate(plan_widths):
            row.cells[idx].width = w
            set_cell_margins(row.cells[idx], top=70, bottom=70, left=90, right=90)

    pl_hdr = t_plan.rows[0]
    pl_headers = ["Phase", "Milestone Focus", "Key Deliverables & Action Items", "Duration"]
    for idx, h_text in enumerate(pl_headers):
        set_cell_background(pl_hdr.cells[idx], NAVY_HEX)
        rh = pl_hdr.cells[idx].paragraphs[0].add_run(h_text)
        rh.font.bold = True
        rh.font.color.rgb = RGBColor(255, 255, 255)
        rh.font.size = Pt(9)

    plan_data = [
        ("Phase 1", "Data Acquisition & Ground Truth Labelling",
         "Collect 2,000+ photos and videos across Orange, Violet, and Green runs. Image augmentation, bounding annotation, and segmentation polygon tagging.",
         "Weeks 1 – 2"),
        ("Phase 2", "AI Model Training & Edge Optimization",
         "Train deep learning segmentation models. Hyperparameter tuning for overlapping pouches. Model quantization (INT8/FP16 TensorRT) for high-speed edge inference.",
         "Weeks 3 – 4"),
        ("Phase 3", "Hardware Rig Staging & Pre-Commissioning",
         "Fabrication of IP65/IP67 camera enclosure, mounting bracket assembly, polarized lighting setup, and Edge AI box bench testing in lab.",
         "Weeks 4 – 5"),
        ("Phase 4", "On-Site Installation & Calibration",
         "Physical installation at Kottayam plant line. Optical calibration, fine-tuning under live production conveyor (24 crates/min), latency benchmarking.",
         "Weeks 6 – 7"),
        ("Phase 5", "UAT, Shift Validation & Full Handover",
         "Continuous shift testing during Shift 1 (07:30–15:30). Accuracy reconciliation against physical counts. Operator training, dashboard deployment & sign-off.",
         "Weeks 8 – 9")
    ]

    for idx, (ph, foc, act, dur) in enumerate(plan_data):
        row = t_plan.rows[idx + 1]
        if idx % 2 == 1:
            set_cell_background(row.cells[0], BG_LIGHT_HEX)
            set_cell_background(row.cells[1], BG_LIGHT_HEX)
            set_cell_background(row.cells[2], BG_LIGHT_HEX)
            set_cell_background(row.cells[3], BG_LIGHT_HEX)
        r0 = row.cells[0].paragraphs[0].add_run(ph)
        r0.font.bold = True
        r0.font.size = Pt(9)
        r1 = row.cells[1].paragraphs[0].add_run(foc)
        r1.font.bold = True
        r1.font.color.rgb = NAVY
        r1.font.size = Pt(9)
        r2 = row.cells[2].paragraphs[0].add_run(act)
        r2.font.size = Pt(8.5)
        r3 = row.cells[3].paragraphs[0].add_run(dur)
        r3.font.bold = True
        r3.font.color.rgb = BLUE
        r3.font.size = Pt(9)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # SECTION 6: KEY PERFORMANCE INDICATORS & ACCEPTANCE CRITERIA
    add_section_heading("Key Performance Indicators (KPIs) & Acceptance Criteria", "6")
    p = doc.add_paragraph(
        "To satisfy the client's stated objective of 'maximum accuracy', the system will be evaluated against the following benchmark criteria:"
    )
    p.paragraph_format.space_after = Pt(6)

    t_kpi = doc.add_table(rows=5, cols=3)
    t_kpi.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_kpi.autofit = False
    set_table_borders(t_kpi)
    kpi_widths = [Inches(2.2), Inches(1.8), Inches(3.0)]
    for row in t_kpi.rows:
        for idx, w in enumerate(kpi_widths):
            row.cells[idx].width = w
            set_cell_margins(row.cells[idx], top=70, bottom=70, left=100, right=100)

    kpi_hdr = t_kpi.rows[0]
    kpi_headers = ["Performance Metric", "Target SLA / KPI", "Measurement Methodology"]
    for idx, h_text in enumerate(kpi_headers):
        set_cell_background(kpi_hdr.cells[idx], NAVY_HEX)
        rh = kpi_hdr.cells[idx].paragraphs[0].add_run(h_text)
        rh.font.bold = True
        rh.font.color.rgb = RGBColor(255, 255, 255)
        rh.font.size = Pt(9.5)

    kpi_data = [
        ("Packet Counting Accuracy", "≥ 99.5%", "Evaluated over 10,000 continuous crates compared against physical audit count."),
        ("Variant Classification Accuracy", "≥ 99.8%", "Automatic verification of Orange vs. Violet vs. Green crates."),
        ("Inference Latency", "< 100 milliseconds", "Complete processing time per crate; comfortably exceeds 2.5s crate cycle."),
        ("Underfill / Anomaly Detection", "≥ 99.0%", "Immediate trigger of visual/audio alert whenever a crate contains < 20 packets.")
    ]

    for idx, (m, tgt, met) in enumerate(kpi_data):
        row = t_kpi.rows[idx + 1]
        if idx % 2 == 1:
            set_cell_background(row.cells[0], BG_LIGHT_HEX)
            set_cell_background(row.cells[1], BG_LIGHT_HEX)
            set_cell_background(row.cells[2], BG_LIGHT_HEX)
        r0 = row.cells[0].paragraphs[0].add_run(m)
        r0.font.bold = True
        r0.font.size = Pt(9)
        r1 = row.cells[1].paragraphs[0].add_run(tgt)
        r1.font.bold = True
        r1.font.color.rgb = BLUE
        r1.font.size = Pt(9)
        r2 = row.cells[2].paragraphs[0].add_run(met)
        r2.font.size = Pt(9)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # SECTION 7: DELIVERABLES SUMMARY
    add_section_heading("Summary of Deliverables from Goose Industrial Solutions", "7")
    deliv_points = [
        ("Industrial Vision Hardware Unit: ", "Food-grade IP65/67 sealed vision camera, cross-polarized LED illuminator, custom C-mount bracket, and photoelectric trigger assembly."),
        ("Edge AI Processing Station: ", "Industrial Edge Computer with pre-installed, optimized YOLO inference engine, database storage, and automated backup routines."),
        ("Custom Operator HMI & Web Dashboard: ", "Real-time production display showing live crate count, variant status, hourly throughput, shift totals, and discrepancy alarms. Accessible via local shopfloor touch screen or network browser."),
        ("Production Reconciliation Reports: ", "Automated end-of-shift reporting with breakdown by milk variant, exportable in PDF and Excel formats, with optional ERP/SAP integration API."),
        ("Comprehensive Documentation & Training: ", "System User Manual, Hardware Maintenance SOP, Operator SOP, and on-site training sessions for plant operations staff.")
    ]
    for b_txt, n_txt in deliv_points:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(3)
        r_b = bp.add_run(b_txt)
        r_b.font.bold = True
        r_b.font.size = Pt(9.5)
        r_n = bp.add_run(n_txt)
        r_n.font.size = Pt(9.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # SECTION 8: NEXT STEPS
    add_section_heading("Next Steps & Immediate Action Items", "8")
    p = doc.add_paragraph(
        "To initiate Phase 1 of the implementation plan, the following immediate steps are recommended:"
    )
    p.paragraph_format.space_after = Pt(4)

    steps_next = [
        ("Step 1: Plan Sign-off & Alignment Meeting: ", "Review and confirm the technical approach and infrastructure checklist with Milma plant engineering."),
        ("Step 2: Dataset Collection Schedule: ", "Agree upon dates for the initial photographic dataset collection (either compiled by Milma staff as per Section 3.1 or collected during a 1-day visit by Goose engineers)."),
        ("Step 3: Staging & Bracket Fabrication: ", "Finalize bracket mounting dimensions on the conveyor frame and initiate hardware procurement.")
    ]
    for b_txt, n_txt in steps_next:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(3)
        r_b = bp.add_run(b_txt)
        r_b.font.bold = True
        r_b.font.size = Pt(9.5)
        r_n = bp.add_run(n_txt)
        r_n.font.size = Pt(9.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # Sign-off box
    sign_tbl = doc.add_table(rows=1, cols=2)
    sign_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    sign_tbl.autofit = False
    sign_tbl.rows[0].cells[0].width = Inches(3.5)
    sign_tbl.rows[0].cells[1].width = Inches(3.5)
    for c in sign_tbl.rows[0].cells:
        set_cell_background(c, BG_CARD_HEX)
        set_cell_margins(c, top=140, bottom=140, left=180, right=180)

    p_s0 = sign_tbl.rows[0].cells[0].paragraphs[0]
    p_s0.paragraph_format.space_after = Pt(2)
    r = p_s0.add_run("SUBMITTED BY:\n")
    r.font.bold = True
    r.font.size = Pt(9.5)
    r.font.color.rgb = NAVY
    r = p_s0.add_run("Goose Industrial Solutions\nVision AI & Automation Solutions\nEmail: contact@goosetech.ai | Web: www.goosetech.ai")
    r.font.size = Pt(9)
    r.font.color.rgb = DARK_TEXT

    p_s1 = sign_tbl.rows[0].cells[1].paragraphs[0]
    p_s1.paragraph_format.space_after = Pt(2)
    r = p_s1.add_run("PREPARED FOR:\n")
    r.font.bold = True
    r.font.size = Pt(9.5)
    r.font.color.rgb = BLUE
    r = p_s1.add_run("Milma (E.R.C.M.P.U. Ltd.)\nKottayam Dairy Plant\nKerala Co-operative Milk Marketing Federation")
    r.font.size = Pt(9)
    r.font.color.rgb = DARK_TEXT

    output_path = "Milma_Kottayam_Vision_Counting_Implementation_Plan.docx"
    doc.save(output_path)
    print(f"Document successfully created at {output_path}")

if __name__ == '__main__':
    create_milma_implementation_doc()

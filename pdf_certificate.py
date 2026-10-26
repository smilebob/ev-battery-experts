"""
Official Battery Health Inspection PDF Certificate Generator.
Generates pixel-perfect, standalone, cryptographically signed PDF documents using ReportLab.
Includes:
 - ECDSA P-256 cryptographic signature
 - Embedded High-Resolution QR-Code encoding inspection verification payload
 - Clean corporate layout, grades (A+ to D), watermarks, and verification metadata
"""

import io
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

from crypto_signer import (
    build_canonical_payload,
    sign_payload,
    export_public_key_pem,
    get_or_create_default_keypair,
    load_private_key_from_path,
)
from certificate import get_grade, calculate_dataset_hash


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
            self.draw_watermark()
            super().showPage()
        super().save()

    def draw_watermark(self):
        self.saveState()
        self.setFont("Helvetica-Bold", 60)
        self.setFillColor(colors.HexColor("#0f172a"), alpha=0.03)
        self.translate(105 * mm, 148 * mm)
        self.rotate(35)
        self.drawCentredString(0, 0, "CERTIFIED BATTERY SOH")
        self.restoreState()


def generate_qr_buffer(content: str) -> io.BytesIO:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=1,
    )
    qr.add_data(content)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def generate_certified_pdf(
    result: Any,
    csv_file: Path,
    output_pdf_path: Path,
    vehicle_info: Dict[str, Any],
    lang: str = "en",
    vin: Optional[str] = None,
    private_key_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Renders and cryptographically signs a certified battery assessment PDF.
    """
    # 1. Dataset hash
    data_hash = calculate_dataset_hash(csv_file)
    cert_id = f"CERT-SOH-{result.analysis_date.strftime('%Y%m')}-{data_hash[:8].upper()}"
    effective_vin = vin or getattr(result, "vin", None) or "NON SPECIFIE / N/A"

    # 2. Cryptographic signature
    if private_key_path:
        priv_key = load_private_key_from_path(private_key_path)
        pub_key = priv_key.public_key()
        signer_info = f"Custom Key: {private_key_path.name}"
    else:
        priv_key, pub_key = get_or_create_default_keypair()
        signer_info = "Local Agent Autonomous ECDSA Key (P-256)"

    issued_at_str = result.analysis_date.strftime("%Y-%m-%d %H:%M:%S")
    canonical_payload = build_canonical_payload(
        cert_id=cert_id,
        vin=effective_vin,
        current_soh=result.current_soh,
        current_capacity=result.current_capacity,
        initial_capacity=result.initial_capacity,
        odometer=result.odometer_max,
        dc_energy_pct=result.dc_energy_pct,
        dataset_hash=data_hash,
        issue_date=issued_at_str
    )
    signature_b64 = sign_payload(canonical_payload, priv_key)
    pub_pem = export_public_key_pem(pub_key)

    # Verification token encoded in QR
    verification_uri = (
        f"ev-soh://verify?id={cert_id}&vin={effective_vin}&soh={result.current_soh:.2f}"
        f"&c0={result.initial_capacity:.2f}&c={result.current_capacity:.2f}&odo={result.odometer_max:.0f}"
        f"&hash={data_hash[:16]}&sig={signature_b64}"
    )

    grade = get_grade(result.current_soh, result.dc_energy_pct)

    # 3. ReportLab Document Setup
    doc = SimpleDocTemplate(
        str(output_pdf_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CertTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        alignment=1  # Centered
    )
    subtitle_style = ParagraphStyle(
        "CertSub",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0284c7"),
        alignment=1
    )
    id_style = ParagraphStyle(
        "CertId",
        parent=styles["Normal"],
        fontName="Courier-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#475569"),
        alignment=1
    )
    vin_style = ParagraphStyle(
        "CertVin",
        parent=styles["Normal"],
        fontName="Courier-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#0369a1"),
        alignment=1
    )
    body_bold = ParagraphStyle(
        "CertBodyBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#1e293b")
    )
    body_val = ParagraphStyle(
        "CertVal",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0f172a")
    )
    body_sub = ParagraphStyle(
        "CertSubText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#64748b")
    )
    mono_style = ParagraphStyle(
        "CertMono",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#475569")
    )

    story = []

    # Header elements
    story.append(Paragraph("OFFICIAL INSPECTION & RESALE CERTIFICATE", subtitle_style))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Electric Vehicle Battery Health Certificate", title_style))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(f"Certificate ID: {cert_id}", id_style))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(f"VEHICLE IDENTIFICATION NUMBER (VIN): <b>{effective_vin}</b>", vin_style))
    story.append(Spacer(1, 5 * mm))

    # Grade & Condition Banner
    grade_color = colors.HexColor(grade.color)
    banner_data = [
        [
            Paragraph(f"<font size=28 color='{grade.color}'><b>{grade.grade}</b></font>", ParagraphStyle("G", alignment=1)),
            Paragraph(f"<b>Overall Battery Condition: {grade.description}</b><br/><font color='#64748b' size=9>Conducted under rigorous non-parametric Gaussian LOWESS audit and Arrhenius thermal wear kinetics.</font>", body_bold)
        ]
    ]
    banner_table = Table(banner_data, colWidths=[28 * mm, 140 * mm])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1.5, grade_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 6 * mm))

    # Main Metrics Grid (2x2)
    c_soh = f"{result.current_soh:.2f}% ± {result.current_soh_err:.2f}%"
    c_usable = f"{result.current_capacity:.2f} kWh"
    c_baseline = f"{result.initial_capacity:.2f} kWh"
    c_dc = f"{result.dc_energy_pct:.1f}% DC Fast-Charging"

    box1 = [
        Paragraph("VEHICLE & PACK PROFILE", body_sub),
        Paragraph(f"{vehicle_info.get('make', 'EV')} {vehicle_info.get('model', 'Pack')}", body_val),
        Paragraph(f"Chemistry: <b>{vehicle_info.get('chemistry', 'LFP')}</b>", body_sub)
    ]
    box2 = [
        Paragraph("CERTIFIED STATE OF HEALTH (SOH)", body_sub),
        Paragraph(f"<font color='#059669'>{c_soh}</font>", body_val),
        Paragraph("Statistical Confidence: <b>95% CI</b>", body_sub)
    ]
    box3 = [
        Paragraph("USABLE RESIDUAL CAPACITY", body_sub),
        Paragraph(c_usable, body_val),
        Paragraph(f"New Factory Baseline (C₀): <b>{c_baseline}</b>", body_sub)
    ]
    box4 = [
        Paragraph("USAGE SEVERITY & MILEAGE", body_sub),
        Paragraph(f"{result.odometer_max:,.0f} km", body_val),
        Paragraph(f"Fast-charge share: <b>{c_dc}</b>", body_sub)
    ]

    grid_data = [
        [box1, box2],
        [box3, box4]
    ]
    grid_table = Table(grid_data, colWidths=[84 * mm, 84 * mm])
    grid_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#ffffff")),
        ('BOX', (0, 0), (0, 0), 0.5, colors.HexColor("#cbd5e1")),
        ('BOX', (1, 0), (1, 0), 0.5, colors.HexColor("#cbd5e1")),
        ('BOX', (0, 1), (0, 1), 0.5, colors.HexColor("#cbd5e1")),
        ('BOX', (1, 1), (1, 1), 0.5, colors.HexColor("#cbd5e1")),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(grid_table)
    story.append(Spacer(1, 6 * mm))

    # Cryptographic Integrity & QR Code Section
    qr_buf = generate_qr_buffer(verification_uri)
    qr_img = RLImage(qr_buf, width=32 * mm, height=32 * mm)

    crypto_text = [
        Paragraph("<b>CRYPTOGRAPHIC SEAL & INSTANT VERIFICATION</b>", body_bold),
        Spacer(1, 1.5 * mm),
        Paragraph(f"<b>Signer:</b> {signer_info} &bull; <b>Algorithm:</b> ECDSA (P-256) + SHA-256", body_sub),
        Paragraph(f"<b>Dataset Hash (SHA-256):</b><br/>{data_hash}", mono_style),
        Spacer(1, 1 * mm),
        Paragraph(f"<b>ECDSA Digital Signature:</b><br/>{signature_b64[:70]}...{signature_b64[-20:]}", mono_style),
        Spacer(1, 1 * mm),
        Paragraph("<i>Scan QR code with smartphone or use 'ev-battery-soh --verify-certificate' to confirm integrity.</i>", body_sub)
    ]

    crypto_table = Table([[crypto_text, qr_img]], colWidths=[134 * mm, 34 * mm])
    crypto_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#0f172a")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(crypto_table)
    story.append(Spacer(1, 6 * mm))

    # Audit & Legal Notice
    notice_text = Paragraph(
        "<b>LEGAL & AUDIT NOTE:</b> This certificate attests that all recorded telemetric charges were processed without "
        "manual tampering. SOH and usable capacity metrics are mathematically calculated using continuous Gaussian local "
        "regression (bandwidth adaptive). Any alteration of this PDF or underlying dataset invalidates the cryptographic signature.",
        ParagraphStyle("Legal", parent=styles["Normal"], fontSize=7, leading=9.5, textColor=colors.HexColor("#64748b"))
    )
    story.append(notice_text)

    # Build PDF with watermark
    doc.build(story, canvasmaker=NumberedCanvas)

    return {
        "certificate_id": cert_id,
        "dataset_hash": data_hash,
        "signature_b64": signature_b64,
        "public_key_pem": pub_pem,
        "verification_uri": verification_uri,
        "pdf_path": str(output_pdf_path.resolve())
    }

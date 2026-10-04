import os
import logging
from app.config import settings
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import docx
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

def generate_demo_files() -> list:
    """
    Generates realistic sample files across multiple formats (PDF, DOCX, TXT, PNG)
    containing intentional policy conflicts to test conflict detection and uncertainty handling.
    """
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    generated = []

    # 1. Company_Policy.pdf (PDF with 3 pages)
    pdf_path_1 = os.path.join(settings.UPLOAD_DIR, "Company_Policy.pdf")
    c1 = canvas.Canvas(pdf_path_1, pagesize=letter)
    
    # Page 1
    c1.setFont("Helvetica-Bold", 18)
    c1.drawString(72, 720, "Global Enterprises Corp — Corporate Policy")
    c1.setFont("Helvetica", 12)
    c1.drawString(72, 690, "Document ID: POL-2025-01 | Classification: Internal")
    c1.drawString(72, 660, "1. Code of Conduct and General Working Hours")
    c1.drawString(72, 640, "Core business hours are from 9:00 AM to 5:00 PM Monday through Friday.")
    c1.drawString(72, 620, "Employees must log attendance daily using the internal portal.")
    c1.showPage()

    # Page 2 (Canonical 20-day paid leave statement)
    c1.setFont("Helvetica-Bold", 16)
    c1.drawString(72, 720, "2. Leave and Vacation Allowance Policy")
    c1.setFont("Helvetica", 12)
    c1.drawString(72, 690, "Annual paid leave allowance is 20 days.")
    c1.drawString(72, 670, "Unused paid leaves up to 5 days may be carried over to the following year.")
    c1.drawString(72, 650, "Sick leave is granted separately up to 10 days upon medical certificate submission.")
    c1.drawString(72, 630, "Maternity leave is provided for 26 weeks as per statutory regulations.")
    c1.showPage()

    # Page 3
    c1.setFont("Helvetica-Bold", 16)
    c1.drawString(72, 720, "3. Health and Medical Insurance Benefits")
    c1.setFont("Helvetica", 12)
    c1.drawString(72, 690, "Comprehensive medical insurance coverage is provided for all full-time staff.")
    c1.drawString(72, 670, "Health insurance covers 80% of dental procedures up to an annual limit of $1,500.")
    c1.drawString(72, 650, "Vision care includes an annual checkup and up to $300 eyewear allowance.")
    c1.save()
    generated.append((pdf_path_1, "Company_Policy.pdf", "pdf"))

    # 2. Employee_Handbook.pdf (PDF with 2 pages, contains the 18-day conflict)
    pdf_path_2 = os.path.join(settings.UPLOAD_DIR, "Employee_Handbook.pdf")
    c2 = canvas.Canvas(pdf_path_2, pagesize=letter)
    
    # Page 1
    c2.setFont("Helvetica-Bold", 18)
    c2.drawString(72, 720, "Employee Handbook & Team Guidelines")
    c2.setFont("Helvetica", 12)
    c2.drawString(72, 690, "Revision Date: Q3 2024 | Version 2.4")
    c2.drawString(72, 660, "Welcome to the organization. This handbook outlines your rights and responsibilities.")
    c2.drawString(72, 640, "Probation Period: The standard probation period for newly joined employees is 3 months.")
    c2.drawString(72, 620, "A performance appraisal will be conducted at the end of the 90-day period.")
    c2.showPage()

    # Page 2 (Contains the conflicting 18 days paid leave statement!)
    c2.setFont("Helvetica-Bold", 16)
    c2.drawString(72, 720, "Section 4: Time Off and Annual Leave")
    c2.setFont("Helvetica", 12)
    c2.drawString(72, 690, "Annual paid leave allowance is 18 days.")
    c2.drawString(72, 670, "All leave requests must be approved by the immediate team supervisor at least")
    c2.drawString(72, 650, "two weeks prior to the intended start date.")
    c2.drawString(72, 630, "Bereavement leave is provided up to 5 consecutive business days.")
    c2.save()
    generated.append((pdf_path_2, "Employee_Handbook.pdf", "pdf"))

    # 3. Remote_Work_Guidelines.docx
    docx_path = os.path.join(settings.UPLOAD_DIR, "Remote_Work_Guidelines.docx")
    doc = docx.Document()
    doc.add_heading("Remote and Hybrid Work Policy Guidelines", level=1)
    doc.add_paragraph("Purpose and Scope: This document establishes criteria for flexible and hybrid work arrangements.")
    doc.add_heading("Eligibility & Schedule", level=2)
    doc.add_paragraph("Eligible employees may work remotely up to 2 days per week upon manager approval.")
    doc.add_paragraph("Core collaboration days in office are Tuesday and Thursday for all engineering teams.")
    doc.add_heading("Equipment and Home Office Stipend", level=2)
    doc.add_paragraph("The company provides a one-time home office setup stipend of $500 for ergonomic monitors and furniture.")
    doc.save(docx_path)
    generated.append((docx_path, "Remote_Work_Guidelines.docx", "docx"))

    # 4. Security_Compliance.txt
    txt_path = os.path.join(settings.UPLOAD_DIR, "Security_Compliance.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(
            "INFORMATION SECURITY AND COMPLIANCE STANDARDS\n\n"
            "1. Password Requirements:\n"
            "All employee passwords must be at least 12 characters in length and include uppercase,\n"
            "lowercase, numbers, and special symbols. Passwords must be rotated every 90 days.\n\n"
            "2. Multi-Factor Authentication:\n"
            "MFA is strictly mandatory for accessing corporate email, GitHub, AWS, and internal VPNs.\n\n"
            "3. Data Confidentiality:\n"
            "Customer data may never be exported to unencrypted personal storage devices."
        )
    generated.append((txt_path, "Security_Compliance.txt", "txt"))

    # 5. Office_Notice_Receipt.png (Image for OCR verification)
    img_path = os.path.join(settings.UPLOAD_DIR, "Office_Notice.png")
    img = Image.new("RGB", (700, 300), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Draw simple clean text onto image
    draw.rectangle([(20, 20), (680, 280)], outline=(12, 135, 235), width=3)
    draw.text((40, 50), "OFFICE NOTICE: CAFETERIA AND VISITOR ACCESS", fill=(10, 10, 10))
    draw.text((40, 100), "Subsidized cafeteria lunch service operates daily from 12:30 PM to 2:30 PM.", fill=(40, 40, 40))
    draw.text((40, 140), "Coffee and snack stations on the 4th floor remain open 24/7.", fill=(40, 40, 40))
    draw.text((40, 180), "Visitor badges must be returned to the security reception desk by 6:00 PM.", fill=(40, 40, 40))
    draw.text((40, 230), "DocIntel AI OCR Test Verification Document - Facility Admin", fill=(80, 80, 80))
    img.save(img_path)
    generated.append((img_path, "Office_Notice.png", "png"))

    return generated

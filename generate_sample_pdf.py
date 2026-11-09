from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def create_sample_pdf(filename="Sample_API_Deviation_ATV261004.pdf"):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 50, "AIVOA PHARMA SCIENCES LTD. - API MANUFACTURING DIVISION")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 70, "GMP DEVIATION & PRELIMINARY INVESTIGATION REPORT (ICH Q7)")
    c.line(50, height - 78, width - 50, height - 78)

    lines = [
        "Deviation Reference ID: DEV-API-2026-089",
        "Date of Incident: 2026-10-24 14:20 HRS",
        "API Product Name: Atorvastatin Calcium API (USP/EP Grade)",
        "Manufacturing Stage: Stage-III Final Crystallization & Isolation",
        "Batch Number: ATV-261004 (Batch Size: 450.0 kg)",
        "Equipment ID: Glass-Lined Reactor GLR-204 & Chilled Brine Loop CBL-02",
        "Manufacturing Site / Block: API Synthesis Block-B, Cleanroom Suite 4",
        "Preliminary Classification: CRITICAL DEVIATION",
        "",
        "1. INCIDENT DESCRIPTION & PROCESS EXCURSION:",
        "During Stage-III crystallization of Atorvastatin Calcium Batch ATV-261004 in Glass-Lined Reactor",
        "GLR-204, the BMR step requires linear cooling of the reaction mass from 65.0 C to 15.0 C over",
        "300 minutes (target cooling rate: 0.16 C/min) to ensure selective crystallization of Polymorph Form I.",
        "At 14:20 HRS, SCADA alarm ALM-204-T triggered. The reactor jacket cooling stalled at 43.5 C for",
        "95 minutes before operator intervention opened the manual bypass valve.",
        "",
        "2. CRITICAL QUALITY ATTRIBUTES (CQA) & QC LAB OOS RESULTS:",
        "- In-Process HPLC Purity Check (Sample ID: QC-ATV-882):",
        "  * Desfluoro Impurity: 0.08% (Spec: NMT 0.15%) - PASS",
        "  * Diastereomer Impurity (Impurity-D): 0.27% (Spec: NMT 0.15%) - FAIL (OOS)",
        "- Powder X-Ray Diffraction (PXRD): Detected ~18% unwanted amorphous/Form-III phase.",
        "",
        "3. IMMEDIATE CONTAINMENT ACTIONS TAKEN:",
        "- Batch ATV-261004 (wet cake, 462 kg) immediately placed under QA QUARANTINE hold tag #QH-904.",
        "- Reactor GLR-204 tagged 'OUT OF SERVICE - ENGINEERING HOLD' pending valve inspection.",
        "- Notification sent to Head of Quality Assurance and Qualified Person (QP).",
        "",
        "4. INITIAL OBSERVATIONS & AVAILABLE EVIDENCE:",
        "- SCADA trend log confirms PLC sent 100% open command signal (20 mA) to chilled brine proportional",
        "  control valve CV-204B, but flow meter FM-204 showed brine flow dropped to 1.2 m3/hr (normal: 14 m3/hr).",
        "- Operator shift handover log noted slight air hissing near CV-204B pneumatic actuator 2 days prior,",
        "  but no maintenance work order was raised.",
        "- Last Preventive Maintenance (PM) on control valve CV-204B was performed 14 months ago (SOP requires",
        "  annual diaphragm and positioner PM every 6 months for critical crystallization reactors).",
        "",
        "5. OPEN EVIDENCE GAPS TO VERIFY ROOT CAUSE:",
        "- Physical dismantling and bench pressure test report of pneumatic actuator diaphragm on CV-204B.",
        "- Calibration verification certificate of reactor RTD temperature probe TT-204A.",
        "- Purity & water content CoA verification of incoming Methanol solvent Lot #METH-9921.",
    ]

    y = height - 105
    for line in lines:
        if line.startswith(("1.", "2.", "3.", "4.", "5.")):
            c.setFont("Helvetica-Bold", 10)
        else:
            c.setFont("Helvetica", 10)
        c.drawString(50, y, line)
        y -= 16

    c.save()
    print(f"Created sample PDF: {filename}")


if __name__ == "__main__":
    create_sample_pdf()
"""Generate fictional sample documents (PDF, DOCX, XLSX) for the demo."""
from pathlib import Path

import docx
import openpyxl
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate

OUT = Path(__file__).parent
S = getSampleStyleSheet()

# PDF: employee handbook, two pages so page citations are visible.
pages = [
    ("Northwind Labs Employee Handbook", [
        "Northwind Labs is a fictional software company used for this demo.",
        "Working hours are 10:00 to 18:30, Monday to Friday. Core collaboration hours are 11:00 to 16:00.",
        "Employees may work remotely up to 3 days per week with manager approval.",
    ]),
    ("Leave Policy", [
        "Full-time employees receive 24 days of paid annual leave per calendar year, accrued monthly at 2 days per month.",
        "Up to 8 unused leave days may be carried over to the next year. Carried-over days expire on 31 March.",
        "Sick leave is 12 days per year. A medical certificate is required for sick leave longer than 2 consecutive days.",
        "Parental leave is 26 weeks for the primary caregiver and 4 weeks for the secondary caregiver.",
    ]),
]
doc = SimpleDocTemplate(str(OUT / "employee_handbook.pdf"), pagesize=A4)
story = []
for i, (title, paras) in enumerate(pages):
    story.append(Paragraph(title, S["Title"] if i == 0 else S["Heading1"]))
    story += [Paragraph(p, S["BodyText"]) for p in paras]
    if i < len(pages) - 1:
        story.append(PageBreak())
doc.build(story)

# DOCX: vendor contract with headings.
d = docx.Document()
d.add_heading("Master Services Agreement: Northwind Labs and Contoso Cloud", 0)
d.add_heading("Term", 1)
d.add_paragraph("This agreement starts on 1 January 2026 and runs for 24 months. It renews automatically for 12-month periods unless either party gives 60 days' written notice.")
d.add_heading("Fees", 1)
d.add_paragraph("Northwind Labs pays a monthly platform fee of USD 4,200, invoiced on the 1st and due within 30 days. Late payments incur interest of 1.5% per month.")
d.add_heading("Service Levels", 1)
d.add_paragraph("Contoso Cloud guarantees 99.9% monthly uptime. For each 0.1% below that, Northwind receives a 5% service credit, capped at 30% of the monthly fee.")
d.add_heading("Termination", 1)
d.add_paragraph("Either party may terminate for material breach not cured within 30 days of notice. Customer data is returned within 15 days of termination.")
d.save(OUT / "vendor_contract.docx")

# XLSX: quarterly sales by region.
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Q3 2026 Sales"
ws.append(["Region", "Revenue (USD)", "Deals Closed", "Top Product"])
for row in [
    ("North", 182000, 41, "Analytics Suite"),
    ("South", 96500, 22, "Data Connector"),
    ("East", 241300, 55, "Analytics Suite"),
    ("West", 134800, 30, "Workflow Builder"),
]:
    ws.append(row)
wb.save(OUT / "q3_sales.xlsx")
print("wrote samples to", OUT)

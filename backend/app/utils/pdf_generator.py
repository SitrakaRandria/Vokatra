from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO

def generate_invoice_pdf(order_data: dict, company_info: dict) -> BytesIO:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(30, height - 30, "FACTURE")
    c.setFont("Helvetica", 12)
    c.drawString(30, height - 50, f"N° {order_data['id']}")

    c.drawString(30, height - 80, f"Vendeur: {company_info['name']}")
    c.drawString(30, height - 100, f"NIF: {company_info.get('nif', '')}")
    c.drawString(30, height - 120, f"Adresse: {company_info.get('address', '')}")

    buyer = order_data['buyer']
    c.drawString(300, height - 80, f"Acheteur: {buyer['name']}")
    c.drawString(300, height - 100, f"Tél: {buyer['phone']}")

    c.line(30, height - 140, width - 30, height - 140)

    y = height - 170
    c.setFont("Helvetica-Bold", 10)
    c.drawString(30, y, "Produit")
    c.drawString(150, y, "Quantité")
    c.drawString(250, y, "Prix unitaire")
    c.drawString(380, y, "Total")
    c.line(30, y - 5, width - 30, y - 5)

    c.setFont("Helvetica", 10)
    y -= 20
    for item in order_data['items']:
        c.drawString(30, y, item['product'])
        c.drawString(150, y, f"{item['quantity']} {item['unit']}")
        c.drawString(250, y, f"{item['unit_price']} Ar")
        c.drawString(380, y, f"{item['total']} Ar")
        y -= 20

    c.line(30, y - 5, width - 30, y - 5)
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(300, y, "Total TTC:")
    c.drawString(400, y, f"{order_data['total_amount']} Ar")

    c.setFont("Helvetica", 8)
    c.drawString(30, 30, "Facture générée automatiquement par Vokatra")

    c.save()
    buffer.seek(0)
    return buffer

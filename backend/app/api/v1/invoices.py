from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session
from app.core.auth import get_current_user
from app.models.user import User
from app.models.order import Order
from app.models.invoice import Invoice
from app.utils.pdf_generator import generate_invoice_pdf

router = APIRouter(prefix="/invoices", tags=["invoices"])

@router.get("/{order_id}/pdf")
async def generate_invoice(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    if not current_user.can_issue_invoices():
        raise HTTPException(403, "Seuls les comptes professionnels vérifiés peuvent générer des factures")
    order = await session.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Commande non trouvée")
    if order.seller_id != current_user.id:
        raise HTTPException(403, "Vous n'êtes pas le vendeur de cette commande")

    order_data = {
        "id": order.id,
        "buyer": {"name": order.buyer.full_name, "phone": order.buyer.phone},
        "items": [{
            "product": order.listing.product,
            "quantity": order.quantity,
            "unit": order.listing.unit,
            "unit_price": order.price_final,
            "total": order.quantity * order.price_final
        }],
        "total_amount": order.quantity * order.price_final
    }
    company_info = {
        "name": current_user.company_name or current_user.full_name,
        "nif": current_user.verification_documents.get("nif") if current_user.verification_documents else None,
        "address": current_user.address
    }

    pdf_buffer = generate_invoice_pdf(order_data, company_info)

    invoice = Invoice(
        order_id=order.id,
        issuer_id=current_user.id,
        recipient_id=order.buyer_id,
        amount=order_data["total_amount"],
        status="generated",
        pdf_url=f"/invoices/{order_id}/pdf"
    )
    session.add(invoice)
    await session.commit()

    return Response(content=pdf_buffer.getvalue(), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=facture_{order_id}.pdf"})

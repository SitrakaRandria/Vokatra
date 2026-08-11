from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import List, Optional
from app.core.database import get_db_session
from app.models.price_history import PriceHistory
from app.schemas.price_history import PriceHistoryResponse

router = APIRouter(prefix="/prices", tags=["prices"])

@router.get("/history", response_model=List[PriceHistoryResponse])
async def get_price_history(
    product: Optional[str] = None,
    region: Optional[str] = None,
    months: int = Query(12, ge=1, le=24),
    session: AsyncSession = Depends(get_db_session)
):
    query = select(PriceHistory)
    if product:
        query = query.where(PriceHistory.product == product)
    if region:
        query = query.where(PriceHistory.region == region)
    cutoff = datetime.utcnow().replace(day=1)
    from dateutil.relativedelta import relativedelta
    cutoff = cutoff - relativedelta(months=months)
    query = query.where(PriceHistory.month_year >= cutoff)
    query = query.order_by(PriceHistory.month_year.desc())
    result = await session.execute(query)
    histories = result.scalars().all()
    return [PriceHistoryResponse.model_validate(h) for h in histories]

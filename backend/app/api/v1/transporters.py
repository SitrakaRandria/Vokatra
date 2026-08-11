from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from app.core.database import get_db_session
from app.core.auth import get_current_user
from app.models.user import User
from app.models.transporter import TransporterProfile
from app.schemas.transporter import TransporterProfileCreate, TransporterProfileUpdate, TransporterProfileResponse

router = APIRouter(prefix="/transporters", tags=["transporters"])

@router.get("/", response_model=List[TransporterProfileResponse])
async def get_transporters(
    region: Optional[str] = None,
    vehicle_type: Optional[str] = None,
    is_available: Optional[bool] = True,
    session: AsyncSession = Depends(get_db_session)
):
    query = select(TransporterProfile).join(User).where(User.role == "transporteur")
    if region:
        query = query.where(TransporterProfile.coverage_region.contains([region]))
    if vehicle_type:
        query = query.where(TransporterProfile.vehicle_type == vehicle_type)
    if is_available is not None:
        query = query.where(TransporterProfile.is_available == is_available)
    result = await session.execute(query)
    profiles = result.scalars().all()
    for p in profiles:
        await session.refresh(p, attribute_names=['user'])
    return [TransporterProfileResponse.model_validate(p) for p in profiles]

@router.post("/", response_model=TransporterProfileResponse, status_code=201)
async def create_transporter_profile(
    profile_data: TransporterProfileCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    if current_user.role != "transporteur":
        raise HTTPException(403, "Seul un transporteur peut créer un profil")
    stmt = select(TransporterProfile).where(TransporterProfile.user_id == current_user.id)
    result = await session.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(409, "Profil transporteur déjà existant")
    new_profile = TransporterProfile(
        user_id=current_user.id,
        coverage_region=profile_data.coverage_region,
        vehicle_type=profile_data.vehicle_type,
        capacity_kg=profile_data.capacity_kg,
        base_rate=profile_data.base_rate,
        rate_unit=profile_data.rate_unit,
        is_available=profile_data.is_available,
        description=profile_data.description
    )
    session.add(new_profile)
    await session.commit()
    await session.refresh(new_profile)
    return TransporterProfileResponse.model_validate(new_profile)

@router.put("/{profile_id}", response_model=TransporterProfileResponse)
async def update_transporter_profile(
    profile_id: int,
    update_data: TransporterProfileUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    stmt = select(TransporterProfile).where(TransporterProfile.id == profile_id)
    result = await session.execute(stmt)
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Profil non trouvé")
    if profile.user_id != current_user.id:
        raise HTTPException(403, "Vous n'êtes pas autorisé")
    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
    await session.commit()
    await session.refresh(profile)
    return TransporterProfileResponse.model_validate(profile)

@router.delete("/{profile_id}", status_code=204)
async def delete_transporter_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    stmt = select(TransporterProfile).where(TransporterProfile.id == profile_id)
    result = await session.execute(stmt)
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Profil non trouvé")
    if profile.user_id != current_user.id:
        raise HTTPException(403, "Vous n'êtes pas autorisé")
    await session.delete(profile)
    await session.commit()

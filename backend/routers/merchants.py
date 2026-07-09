from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import auth, schemas
from ..database import get_db
from ..models_db import AuditLog, Merchant, User

router = APIRouter(prefix="/merchants", tags=["merchants"])


@router.post("", response_model=schemas.MerchantOut, status_code=status.HTTP_201_CREATED)
def create_merchant(
    payload: schemas.MerchantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
):
    if db.query(Merchant).filter(Merchant.merchant_id == payload.merchant_id).first():
        raise HTTPException(status_code=400, detail=f"Merchant '{payload.merchant_id}' already exists")

    merchant = Merchant(**payload.model_dump(), created_by=current_user.id)
    db.add(merchant)
    db.commit()
    db.refresh(merchant)

    db.add(AuditLog(user_id=current_user.id, action="CREATE_MERCHANT", target=merchant.merchant_id))
    db.commit()
    return merchant


@router.get("/{merchant_id}", response_model=schemas.MerchantOut)
def get_merchant(
    merchant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth.get_current_user),
):
    merchant = db.query(Merchant).filter(Merchant.merchant_id == merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return merchant

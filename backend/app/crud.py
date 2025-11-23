from sqlalchemy.orm import Session
from . import models, schemas, auth
from datetime import datetime

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        name=user.name,
        password_hash=hashed_password,
        role=user.role,
        phone=user.phone,
        condominium_id=user.condominium_id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_inspection(db: Session, inspection: schemas.InspectionCreate, user_id: int):
    # Cria a vistoria
    db_inspection = models.Inspection(
        surveyor_id=user_id,
        condominium_id=inspection.condominium_id,
        is_custom=inspection.is_custom,
        ia_analysis=inspection.ia_analysis
    )
    db.add(db_inspection)
    db.commit()
    db.refresh(db_inspection)
    
    # Adiciona os itens da vistoria
    for item in inspection.items:
        db_item = models.InspectionItem(
            inspection_id=db_inspection.id,
            name=item.name,
            status=item.status,
            observation=item.observation
            # photo_url deve ser atualizado separadamente ou logica complexa de upload aqui
        )
        db.add(db_item)
    
    db.commit()
    return db_inspection

def create_work_order(db: Session, work_order: schemas.WorkOrderCreate):
    db_wo = models.WorkOrder(
        title=work_order.title,
        description=work_order.description,
        item_id=work_order.item_id,
        provider_id=work_order.provider_id
    )
    db.add(db_wo)
    db.commit()
    db.refresh(db_wo)
    return db_wo
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, case, text, or_
from sqlalchemy.orm import joinedload, outerjoin
# Importa componentes internos
from .. import database, models, auth, schemas 

router = APIRouter(prefix="/work-orders", tags=["Work Orders"])

# Schema simples para atualizar status (recebe a nova situação)
class StatusUpdateSchema(BaseModel):
    status: str 
    
class WorkOrderPhotoUpdateSchema(BaseModel):
    photo_after_url: Optional[str] = None
    status: str = "Concluído"
    model_config = ConfigDict(from_attributes=True)

# Dependência para o banco de dados
get_db = database.get_db

### ROTAS DE BUSCA E GESTÃO ###

@router.get("/", response_model=List[schemas.WorkOrderResponse], summary="Listar Ordens de Serviço (Diagnóstico Bruto)")
def list_work_orders(
    condominium_id: Optional[int] = None,
    sort_by: str = "status",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Retorna dados brutos para confirmar a leitura do DB, ignorando o ORM."""
    
    try:
        # 🚨 DIAGNÓSTICO FINAL: SQL BRUTO
        # Busca apenas os campos essenciais que sabemos que existem
        raw_data = db.execute(
            text(
                "SELECT id, title, description, status, created_at, closed_at, item_id, provider_id FROM work_orders ORDER BY created_at DESC"
            )
        ).fetchall()
        
        # Converte a lista de tuplas para uma lista de WorkOrderResponse (Pydantic)
        # ⚠️ Nota: Esta conversão é mais complexa do que o Pydantic lida automaticamente
        
        # Vamos usar o método mais simples: criar um objeto serializável
        orders_serializable = []
        for row in raw_data:
            # Assumimos que a ordem dos campos está correta para mapear no WorkOrderResponse
            orders_serializable.append({
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'status': row[3],
                'created_at': row[4].isoformat() if row[4] else None,
                'closed_at': row[5].isoformat() if row[5] else None,
                'photo_before_url': None,
                'photo_after_url': None,
                'provider_id': row[7],
                'item_id': row[6],
                'condominium': None, # Não carregamos o condomínio para este teste
            })

        return orders_serializable

    except Exception as e:
        print(f"❌ ERRO FATAL NA LEITURA BRUTA: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Falha crítica ao ler dados do banco. Trace: {e}"
        )
    
@router.post("/{order_id}/status", response_model=schemas.WorkOrderResponse, summary="Atualizar Status da OS")
async def update_wo_status(
    order_id: int,
    data: StatusUpdateSchema,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Atualiza o status para Pendente, Em Andamento ou Concluído (sem foto)."""
    db_wo = db.query(models.WorkOrder).filter(models.WorkOrder.id == order_id).first()
    if not db_wo:
        raise HTTPException(status_code=404, detail="Ordem de Serviço não encontrada")

    db_wo.status = data.status.capitalize() # ⬅️ Otimização: Padroniza o status
    
    if data.status.lower() == "concluído" and not db_wo.closed_at:
        db_wo.closed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_wo)
    return db_wo

@router.post("/{order_id}/close", response_model=schemas.WorkOrderResponse, summary="Concluir OS com Foto")
async def close_wo_with_photo(
    order_id: int,
    data: WorkOrderPhotoUpdateSchema,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Finaliza a OS, registrando a foto do serviço pronto."""
    db_wo = db.query(models.WorkOrder).filter(models.WorkOrder.id == order_id).first()
    if not db_wo:
        raise HTTPException(status_code=404, detail="Ordem de Serviço não encontrada")

    db_wo.status = "Concluído"
    db_wo.photo_after_url = data.photo_after_url
    
    if not db_wo.closed_at:
        db_wo.closed_at = datetime.utcnow()
        
    db.commit()
    db.refresh(db_wo)
    return db_wo

@router.post("/", response_model=schemas.WorkOrderResponse, status_code=201, summary="Criar Ordem de Serviço Manualmente")
async def create_work_order(
    work_order: schemas.WorkOrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Cria uma nova OS a partir de uma demanda administrativa."""
    
    db_wo = models.WorkOrder(**work_order.model_dump())
    
    try:
        db.add(db_wo)
        db.commit()
        db.refresh(db_wo)
    except IntegrityError as e:
        db.rollback()
        print(f"ERRO SQL INTEGRITY FAILED (ROLLBACK): {e.orig}") 
        raise HTTPException(
            status_code=400, 
            detail="Falha ao criar a OS: Verifique se todos os IDs (Condomínio/Item/Provider) existem."
        )

    return db_wo

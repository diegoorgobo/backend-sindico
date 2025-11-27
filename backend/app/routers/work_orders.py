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

@router.get("/", response_model=List[schemas.WorkOrderResponse], summary="Listar Ordens de Serviço (SQL BRUTO FINAL)")
def list_work_orders(
    condominium_id: Optional[int] = None,
    sort_by: str = "status",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Executa consulta SQL bruta para garantir a listagem e os filtros."""
    
    from sqlalchemy import text 
    
    # Define a consulta SQL base com LEFT JOINs explícitos para carregar o nome do Condomínio
    sql_base = """
        SELECT 
            wo.id, wo.title, wo.description, wo.status, wo.created_at, wo.closed_at, 
            wo.photo_before_url, wo.photo_after_url, wo.item_id, wo.provider_id,
            c.name AS condominium_name, c.id AS condominium_id -- ⬅️ COLUNAS FALTANTES
        FROM work_orders wo
        LEFT JOIN inspection_items ii ON wo.item_id = ii.id
        LEFT JOIN condominiums c ON ii.condominium_id = c.id -- ⬅️ JOIN PARA CONDOMÍNIO
    """
    
    where_clauses = ["1=1"] 
    
    # 1. FILTRO DE SEGURANÇA (Se o bloco estiver comentado, o código segue sem filtro)
    if current_user.role != 'Programador' and current_user.condominium_id is not None:
        user_condo_id = current_user.condominium_id
        
        where_clauses.append(f"""
            (ii.condominium_id = {user_condo_id} OR wo.item_id IS NULL)
        """)
        
    # 2. FILTRO POR DROPDOWN
    if condominium_id is not None:
        where_clauses.append(f"ii.condominium_id = {condominium_id}")

    # 3. ORDENAÇÃO
    order_clause = "wo.created_at DESC"
    if sort_by == 'status':
        # Nota: Não podemos usar CASE com SQL Bruto aqui para este teste. A ordenação será simplificada:
        order_clause = "wo.status, wo.created_at DESC" 
    
    # 4. EXECUÇÃO DO SQL BRUTO FINAL
    sql_query = text(f"""
        {sql_base}
        WHERE {' AND '.join(where_clauses)}
        ORDER BY {order_clause} 
    """)

    raw_results = db.execute(sql_query).fetchall()

    # 5. MAPEAMENTO MANUAL PARA PYDANTIC/JSON
    orders_serializable = []
    for row in raw_results:
        orders_serializable.append(schemas.WorkOrderResponse(
            id=row[0],
            title=row[1],
            description=row[2],
            status=row[3],
            created_at=row[4].isoformat() if row[4] else None,
            closed_at=row[5].isoformat() if row[5] else None,
            photo_before_url=row[6],
            photo_after_url=row[7],
            item_id=row[8],
            provider_id=row[9],
            # 🚨 Mapeamento do objeto Condomínio (ID está no índice 11, Nome está no 10)
            condominium=schemas.SimpleCondo(id=row[11], name=row[10]) 
                        if row[11] is not None else None,
        ).model_dump())
        
    return orders_serializable
    
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

    db_wo.status = data.status.capitalize()
    
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

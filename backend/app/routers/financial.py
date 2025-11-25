# Adicione em backend/app/routers/financial.py ou no main.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List
from datetime import datetime, timedelta
from .. import database, models, auth, schemas

router = APIRouter(prefix="/financial", tags=["Financial"])

@router.get("/dashboard-stats")
def get_financial_stats(condominium_id: int, db: Session = Depends(database.get_db)):
    # 1. Totais do Mês Atual
    today = datetime.now()
    month_start = today.replace(day=1, hour=0, minute=0, second=0)
    
    # Query base para o condomínio e mês atual
    base_query = db.query(
        models.FinancialRecord.type,
        func.sum(models.FinancialRecord.amount).label("total")
    ).filter(
        models.FinancialRecord.condominium_id == condominium_id,
        models.FinancialRecord.date >= month_start
    ).group_by(models.FinancialRecord.type).all()

    income = next((x.total for x in base_query if x.type == 'Receita'), 0.0)
    expense = next((x.total for x in base_query if x.type == 'Despesa'), 0.0)
    
    # 2. Dados para o Gráfico (Últimos 6 meses)
    # Lógica simplificada: Agrupar por mês
    six_months_ago = today - timedelta(days=180)
    chart_data_query = db.query(
        func.to_char(models.FinancialRecord.date, 'YYYY-MM').label("month"),
        models.FinancialRecord.type,
        func.sum(models.FinancialRecord.amount)
    ).filter(
        models.FinancialRecord.condominium_id == condominium_id,
        models.FinancialRecord.date >= six_months_ago
    ).group_by("month", models.FinancialRecord.type).order_by("month").all()
    
    # Processar chart_data para formato JSON amigável ao Flutter
    # ... (Lógica de transformação de dados omitida para brevidade)
    
    return {
        "current_month": {
            "income": income,
            "expense": expense,
            "balance": income - expense
        },
        "chart_data": chart_data_query # O frontend irá tratar
    }

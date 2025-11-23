from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from . import models, schemas, crud, database, auth

# Cria tabelas no banco (apenas para dev, em prod usar Alembic)
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="CondoManager API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permitir tudo conforme solicitado
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Auth Routes ---
@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = crud.get_user_by_email(db, form_data.username)
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

# --- Inspection Routes ---
# Endpoint complexo para upload de vistoria com fotos e dados JSON
@app.post("/inspections/upload")
async def create_inspection_with_files(
    condominium_id: int = Form(...),
    is_custom: bool = Form(...),
    ia_analysis: str = Form(""),
    items_json: str = Form(...), # JSON string dos itens
    files: List[UploadFile] = File(None), # Lista de fotos
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db)
):
    # 1. Parse do JSON dos itens
    try:
        items_data = json.loads(items_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for items")

    # 2. Criação da Vistoria base
    db_inspection = models.Inspection(
        surveyor_id=current_user.id,
        condominium_id=condominium_id,
        is_custom=is_custom,
        ia_analysis=ia_analysis
    )
    db.add(db_inspection)
    db.commit()
    db.refresh(db_inspection)

    # 3. Processamento dos itens e upload (Simulado)
    # Na prática, você deve fazer upload para S3/Supabase Storage aqui e pegar a URL
    # Mapear qual arquivo pertence a qual item é complexo via Form Data puro
    # Sugestão: Nomear o arquivo com o ID temporário do item ou índice
    
    for item in items_data:
        db_item = models.InspectionItem(
            inspection_id=db_inspection.id,
            name=item.get('name'),
            status=item.get('status'),
            observation=item.get('observation'),
            photo_url="url_simulada_storage" # Lógica de storage aqui
        )
        db.add(db_item)
    
    db.commit()
    return {"status": "success", "inspection_id": db_inspection.id}

@app.get("/condominiums/{condo_id}/pdf-report")
def generate_pdf_report(condo_id: int, db: Session = Depends(database.get_db)):
    # Placeholder para geração de PDF com ReportLab
    # Deve buscar logo da empresa, cores do tema e dados
    return {"msg": "PDF generation logic here"}
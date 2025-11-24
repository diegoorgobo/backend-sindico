from pydantic import BaseModel, ConfigDict, EmailStr
from typing import List, Optional
from datetime import datetime, date

# --- Configuração Base ---
class BaseConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# --- User ---
class UserBase(BaseConfig):
    email: EmailStr
    name: str
    phone: Optional[str] = None
    role: str
    condominium_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    photo_url: Optional[str] = None

# --- Token ---
class Token(BaseModel):
    access_token: str
    token_type: str

# --- Condominium ---
class CondominiumBase(BaseConfig):
    name: str
    cnpj: str
    primary_color: Optional[str] = "0xFF000000"
    logo_url: Optional[str] = None

class CondominiumCreate(CondominiumBase):
    pass

class CondominiumResponse(CondominiumBase):
    id: int
    # Incluir outros campos conforme necessidade

# --- Inspection Item ---
class InspectionItemCreate(BaseConfig):
    name: str
    status: str # Bom, Regular, Ruim
    observation: Optional[str] = None
    # photo_url será tratado no upload

class InspectionItemResponse(InspectionItemCreate):
    id: int
    photo_url: Optional[str] = None

# --- Inspection ---
class InspectionCreate(BaseConfig):
    condominium_id: int
    is_custom: bool = False
    ia_analysis: Optional[str] = None
    items: List[InspectionItemCreate]

class InspectionResponse(BaseConfig):
    id: int
    date: datetime
    status: str
    surveyor_id: int
    items: List[InspectionItemResponse]
    
# --- Work Order ---
class WorkOrderCreate(BaseConfig):
    title: str
    description: str
    item_id: Optional[int] = None
    provider_id: Optional[int] = None

id: int
    title: str
    description: str
    status: str
    created_at: datetime
    closed_at: Optional[datetime] = None
    photo_before_url: Optional[str] = None
    photo_after_url: Optional[str] = None
    provider_id: Optional[int] = None
    item_id: Optional[int] = None # Se o relacionamento for carregado
    model_config = ConfigDict(from_attributes=True)

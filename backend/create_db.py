# backend/create_db.py

from app.database import engine, Base
from app import models # Importa os modelos para garantir que eles sejam conhecidos pelo Base

print("Tentando criar todas as tabelas (incluindo 'messages')...")
Base.metadata.create_all(bind=engine)
print("Sucesso! O banco de dados foi atualizado.")

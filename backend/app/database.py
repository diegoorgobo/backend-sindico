from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Em produção, use variáveis de ambiente. Ex: os.getenv("DATABASE_URL") 
# String de conexão de exemplo (substitua pela sua do Supabase) ------------ senha: JRhKVTLayVK1cySk
SQLALCHEMY_DATABASE_URL = "postgresql://postgres.jqlygddtjkvtuckwpucp:JRhKVTLayVK1cySk@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:

        db.close()

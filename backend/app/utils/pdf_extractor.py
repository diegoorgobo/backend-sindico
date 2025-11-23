from pypdf import PdfReader
from fastapi import UploadFile
import io

async def extract_text_from_pdf(file: UploadFile) -> str:
    content = await file.read()
    pdf_file = io.BytesIO(content)
    reader = PdfReader(pdf_file)
    
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
            
    # Retorna o cursor do arquivo para o início caso precise salvar no disco depois
    await file.seek(0) 
    return text
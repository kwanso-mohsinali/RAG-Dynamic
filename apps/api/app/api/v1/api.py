from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi import HTTPException
from app.api.v1.endpoints import chat, documents
from app.s3_utils import download_file_from_s3

api_router = APIRouter()

@api_router.get("/download/{file_key}")
async def download_file(file_key: str):
    """Download file from S3"""
    try:
        local_file = download_file_from_s3(file_key)
        return FileResponse(local_file, filename=file_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])

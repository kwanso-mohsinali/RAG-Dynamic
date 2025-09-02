from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi import HTTPException
from app.s3_utils import download_file_from_s3

api_router = APIRouter()

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "API is running"}

@api_router.get("/download/{file_key}")
async def download_file(file_key: str):
    """Download file from S3"""
    try:
        local_file = download_file_from_s3(file_key)
        return FileResponse(local_file, filename=file_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

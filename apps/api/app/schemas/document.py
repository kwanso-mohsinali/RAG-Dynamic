from pydantic import BaseModel

class UploadFileRequest(BaseModel):
    resource_id: str
    file_key: str
    secret_key: str

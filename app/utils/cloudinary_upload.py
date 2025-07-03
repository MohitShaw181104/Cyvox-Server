import os
import cloudinary
from io import BytesIO
import cloudinary.uploader
from fastapi import UploadFile
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

# Configuration       
cloudinary.config( 
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

async def upload_audio_to_cloudinary(
    file: UploadFile, 
    filename: str, 
    suffix: Optional[str] = None
) -> str:
    contents = await file.read()

    # Create a file-like object from bytes
    file_stream = BytesIO(contents)
    
    file_name = f"{filename}_{suffix}" if suffix else filename
    
    result = cloudinary.uploader.upload_large(
        file_stream,
        resource_type="video",
        public_id=file_name,
        format="mp3",
        overwrite=True
    )

    return result["secure_url"]

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import JSONResponse
from ..utils.cloudinary_upload import upload_audio_to_cloudinary
from typing import Optional
from bson import ObjectId
from datetime import datetime, timezone

router = APIRouter()

@router.put("/upload-audio")
async def upload_audio(
    request: Request, 
    user_id: str = Form(...), 
    audio: UploadFile = File(...), 
    suffix: Optional[str] = Form(None)
):
    test_user_collection = request.app.state.db["users"]
    user = test_user_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    audio_url = await upload_audio_to_cloudinary(audio, user_id, suffix=suffix)
    
    test_user_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"audioUrl": audio_url, "updatedAt": datetime.now(timezone.utc)}}
    )
    return {"audioUrl": audio_url, "message": "Audio uploaded successfully."}
    
upload_audio_router = router
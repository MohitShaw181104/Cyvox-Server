from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException, status
from typing import Optional, List
from app.schemas.user_schema import user_serializer, user_list_serializer
from bson import ObjectId
from datetime import datetime, timezone
from ..utils.cloudinary_upload import upload_audio_to_cloudinary

router = APIRouter()
    
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    phoneNumber: str = Form(...),
    clerkUserId: str = Form(...),
    audio: Optional[UploadFile] = File(None),
):
    test_user_collection = request.app.state.db["users"]

    if test_user_collection.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already exists")

    if test_user_collection.find_one({"phoneNumber": phoneNumber}):
        raise HTTPException(status_code=400, detail="Phone number already exists")
    
    if test_user_collection.find_one({"clerkUserId": clerkUserId}):
        raise HTTPException(status_code=400, detail="clerkUserId already exists")

    user_dict = {
        "username": username,
        "email": email,
        "phoneNumber": phoneNumber,
        "clerkUserId": clerkUserId,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
        "audioUrl": None
    }
    
    result = test_user_collection.insert_one(user_dict)
    user_id = result.inserted_id
    
    if audio:
        audio_url = await upload_audio_to_cloudinary(audio, str(user_id))
        test_user_collection.update_one(
            {"_id": user_id},
            {"$set": {"audioUrl": audio_url, "updatedAt": datetime.now(timezone.utc),}}
        )
        user_dict["audioUrl"] = audio_url

    user_dict["_id"] = str(user_id)
    
    return user_dict

auth_router = router
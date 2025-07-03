from fastapi import APIRouter, status, HTTPException, Request, Form, UploadFile, File
from app.schemas.user_schema import user_serializer, user_list_serializer
from bson import ObjectId, errors
from datetime import datetime, timezone
from typing import Optional
from pydantic import EmailStr
from ..utils.cloudinary_upload import upload_audio_to_cloudinary
from app.voice_pipeline.pipeline import process_complaint_audio
from ..schemas.complaint_schema import complaint_list_serializer, complaint_serializer

router = APIRouter()

@router.post("/register", status_code=status.HTTP_200_OK)
async def register_complain(
    request: Request,
    username: str = Form(..., min_length=3, max_length=50),
    userId: str = Form(...),
    clerkUserId: str = Form(...),
    email: EmailStr = Form(...),
    userPhoneNumber: str = Form(..., min_length=10, max_length=15),
    scammerPhoneNumber: str = Form(..., min_length=10, max_length=15),
    callFrequency: int = Form(default=1),
    userSampleAudio: Optional[UploadFile] = File(None),  # not in the scammer db
    userConversationAudio: UploadFile = File(...),  # in scammer db
    city: str = Form(...),
    district: str = Form(...),
    state: str = Form(...),
    pincode: str = Form(..., min_length=6, max_length=6),
    streetAddress: str = Form(...),
    complainSubject: str = Form(...),
    incidentDescription: str = Form(...),
    moneyScammed: int = Form(...), 
    dateOfIncident: str = Form(...),
):
    try:
        user_obj_id = ObjectId(userId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid userId")
    
    scammer_complain_collection = request.app.state.db["scammer_complaints"]
    test_user_collection = request.app.state.db["users"]

    # dictionary of recieved req.
    complain_dict = {
        "username": username,
        "userId": user_obj_id,
        "clerkUserId": clerkUserId,
        "email": email,
        "userPhoneNumber": userPhoneNumber,
        "scammerPhoneNumber": scammerPhoneNumber,
        "callFrequency": callFrequency,
        "userConversationAudioUrl": None,
        "city": city,
        "district": district,
        "state": state,
        "pincode": pincode,
        "streetAddress": streetAddress,
        "complainSubject": complainSubject,
        "incidentDescription": incidentDescription,
        "moneyScammed": moneyScammed,
        "dateOfIncident":dateOfIncident,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    }

    # dictionary insert to mongoDB
    complaint_result = scammer_complain_collection.insert_one(complain_dict)
    complaint_id = complaint_result.inserted_id
    
    # add the complaintId in the user's collection
    test_user_collection.update_one(
    {"_id": user_obj_id},
        {
            "$push": {
                "previousComplaints": {
                    "complaint_id": ObjectId(complaint_id),
                    "complaint_date": datetime.now(timezone.utc)
                }
            }
        }
    )
    
    # add the userSampleAudio to the userCollection
    user_sample_audio_url = None
    if userSampleAudio:
        user_sample_audio_url = await upload_audio_to_cloudinary(userSampleAudio, str(userId))
        print("audio uploaded: ", user_sample_audio_url)
        test_user_collection.update_one(
            {"_id": user_obj_id},
            {"$set": {"audioUrl": user_sample_audio_url, "updatedAt": datetime.now(timezone.utc),}}
        )
    
    # userConversation audio to cloudinary with name <userId>_<complaintId>_conversation.mp3
    user_conversation_audio_url = None
    if userConversationAudio:
        user_conversation_audio_url = await upload_audio_to_cloudinary(userConversationAudio, str(userId), suffix=f"{complaint_id}_conversation")
        print("conversation uploaded: ", user_conversation_audio_url)
        scammer_complain_collection.update_one(
            {"_id": ObjectId(complaint_id)},
            {"$set": {"userConversationAudioUrl": user_conversation_audio_url, "updatedAt": datetime.now(timezone.utc),}}
        )
        complain_dict["userConversationAudioUrl"] = user_conversation_audio_url
    else:
        raise HTTPException(status_code=400, detail="User conversation audio is required.")

    print("entering model")
    try:
        results, scammer_audio_url = await process_complaint_audio(userId, complaint_id, user_sample_audio_url, user_conversation_audio_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice analysis error: {str(e)}")
    
    if results is None:
        raise HTTPException(status_code=500, detail="Voice analysis failed. Please try again later.")
    else:
        print("result recived in register_complain:", results)

    complain_dict["_id"] = str(complaint_id)
    complain_dict["userId"] = str(userId)
    complain_dict["scammerAudioUrl"] = scammer_audio_url
    complain_dict["matchedScammerComplaints"] = results
    
    scammer_complain_collection.update_one(
        {"_id": ObjectId(complaint_id)},
        {"$set": {
            "matchedScammerComplaints": results,
            "updatedAt": datetime.now(timezone.utc)
        }}
    )
    
    for result in results:
        scammer_complain_collection.update_one(
            {"_id": ObjectId(result["complaintId"])},
            {
                "$push": {
                    "matchedScammerComplaints": {
                        "complaintId": complaint_id,
                        "similarity": result["similarity"]
                    }
                }
            }
        )

    return {
        "message" : "Complaint registered successfully",
        "email": email,
        "complaint details": complain_dict
    }

@router.get("/get-all", status_code=status.HTTP_200_OK)
async def get_all_complaints(request: Request):
    scammer_complain_collection = request.app.state.db["scammer_complaints"]
    complaints = complaint_list_serializer(scammer_complain_collection.find())
    
    if not complaints:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "No complaints in the DB"}
        )
    return {"All complaints": complaints}

@router.get("/{complaintId}", status_code=status.HTTP_200_OK, summary="Get Complaints By complaintID")
async def get_complaint_by_complaintId(complaintId: str, request: Request):
    scammer_complain_collection = request.app.state.db["scammer_complaints"]

    try:
        complaint_obj_id = ObjectId(complaintId)
    except errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid complaintId format")
    
    raw_complaint = scammer_complain_collection.find_one({"_id": complaint_obj_id})

    if not raw_complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "No complaint in the DB for the given complaintId"}
        )

    complaint = complaint_serializer(raw_complaint)
    return {"complaint_detail": complaint}

@router.get("/user/{userId}", status_code=status.HTTP_200_OK, summary="Get Complaints By UserID")
async def get_complaint_by_userId(userId: str, request: Request):
    scammer_complain_collection = request.app.state.db["scammer_complaints"]
    
    try:
        user_id_obj = ObjectId(userId)
    except errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid userId format")
    
    complaints = complaint_list_serializer(scammer_complain_collection.find({"userId": user_id_obj}))

    if not complaints:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "No complaints in the DB for the userId"}
        )

    return {"complaints": complaints}

# @router.get("/clerkId/{clerkId}", status_code=status.HTTP_200_OK, summary="Get Complaints By ClerkID")
# async def get_complaint_by_clerkId(clerkId: str, request: Request):
#     scammer_complain_collection = request.app.state.db["scammer_complaints"]
#     complaints = complaint_list_serializer(scammer_complain_collection.find({"clerkUserId": clerkId}))
    
#     # complaints = complaint_list_serializer(scammer_complain_collection.find())
    
#     if not complaints:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail={"error": "No complaints in the DB with the given clerkId"}
#         )
#     return {"complaints": complaints}

complain_router = router

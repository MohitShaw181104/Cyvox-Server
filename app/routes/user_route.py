from fastapi import APIRouter, status, HTTPException, Request
from app.schemas.user_schema import user_serializer, user_list_serializer
from bson import ObjectId
from datetime import datetime, timezone

router = APIRouter()

@router.get("/all", status_code=status.HTTP_200_OK)
async def get_users(request: Request):
    test_user_collection = request.app.state.db["users"]
    users = user_list_serializer(test_user_collection.find())
    
    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "No user in the DB"}
        )
    return {"All users": users}

@router.get("/{userId}", status_code=status.HTTP_200_OK)
async def get_user_by_ID(userId: str, request: Request):
    test_user_collection = request.app.state.db["users"]
    
    try:
        user = test_user_collection.find_one({"_id": ObjectId(userId)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid userId format"}
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "User not found"}
        )
        
    return {"User Found": user_serializer(user)}

@router.get("/clerkId/{clerkUserId}", status_code=status.HTTP_200_OK)
async def get_user_by_clerk_ID(clerkUserId: str, request: Request):
    test_user_collection = request.app.state.db["users"]
    
    try:
        user = test_user_collection.find_one({"clerkUserId": clerkUserId})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid userId format"}
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "User not found"}
        )
        
    return {"User Found": user_serializer(user)}

user_router = router
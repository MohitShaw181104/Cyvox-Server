from bson import ObjectId
from datetime import datetime

def user_serializer(user) -> dict:
    previous_complaints = []
    for complaint in user.get("previousComplaints", []):
        previous_complaints.append({
            "complaint_id": str(complaint["complaint_id"]),
            "complaint_date": complaint["complaint_date"].isoformat() if isinstance(complaint["complaint_date"], datetime) else complaint["complaint_date"]
        })
        
    return {
        "_id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
        "phoneNumber": user["phoneNumber"],
        "clerkUserId": user["clerkUserId"],
        "createdAt": user["createdAt"].isoformat() if isinstance(user["createdAt"], datetime) else user["createdAt"],
        "updatedAt": user["updatedAt"].isoformat() if isinstance(user["updatedAt"], datetime) else user["updatedAt"],
        "audioUrl": user.get("audioUrl", None),
        "previousComplaints": previous_complaints
    }
    
    
def user_list_serializer(users) -> list:
    return [user_serializer(user) for user in users]
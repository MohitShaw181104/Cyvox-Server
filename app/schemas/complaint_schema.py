from datetime import datetime

def complaint_serializer(complaint) -> dict:
    matched_scammer_complaints = []
    for result in complaint.get("matchedScammerComplaints", []):
        matched_scammer_complaints.append({
            "matchedId": str(result.get("complaintId")),
            "matchedScore": result.get("similarity")
        })

    return {
        "_id": str(complaint["_id"]),
        "username": complaint.get("username"),
        "userId": str(complaint.get("userId")),
        "clerkUserId": complaint.get("clerkUserId"),
        "email": complaint.get("email"),
        "userPhoneNumber": complaint.get("userPhoneNumber"),
        "scammerPhoneNumber": complaint.get("scammerPhoneNumber"),
        "callFrequency": complaint.get("callFrequency"),
        "userConversationAudioUrl": complaint.get("userConversationAudioUrl"),
        "city": complaint.get("city"),
        "district": complaint.get("district"),
        "state": complaint.get("state"),
        "pincode": complaint.get("pincode"),
        "streetAddress": complaint.get("streetAddress"),
        "complainSubject": complaint.get("complainSubject"),
        "incidentDescription": complaint.get("incidentDescription"),
        "moneyScammed": complaint.get("moneyScammed"),
        "dateOfIncident": complaint.get("dateOfIncident").isoformat() if isinstance(complaint.get("dateOfIncident"), datetime) else complaint.get("dateOfIncident"),
        "createdAt": complaint.get("createdAt").isoformat() if isinstance(complaint.get("createdAt"), datetime) else complaint.get("createdAt"),
        "updatedAt": complaint.get("updatedAt").isoformat() if isinstance(complaint.get("updatedAt"), datetime) else complaint.get("updatedAt"),
        "scammerAudioUrl": complaint.get("userScammerAudioUrl"),
        "matchedScammerComplaints": matched_scammer_complaints
    }
    

def complaint_list_serializer(complaints) -> list:
    return [complaint_serializer(c) for c in complaints]

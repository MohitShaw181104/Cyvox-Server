from scipy.spatial.distance import cosine
from bson import ObjectId

def compare_with_existing_scammer_embeddings(current_embedding, db, complaint_id, threshold=0.5):
    matches = []
    cursor = db["scammer_complaints"].find({
        "_id": {"$ne": ObjectId(complaint_id)},
        "scammerEmbedding": {"$exists": True}
        
    })

    for record in cursor:
        db_embedding = record["scammerEmbedding"]
        similarity = 1 - cosine(current_embedding, db_embedding)
        print(f"Comparing with complaint {record['_id']}: similarity = {similarity:.4f}")
        if similarity > threshold:
            matches.append({
                "complaintId": str(record["_id"]),
                "similarity": round(similarity, 4)
            })

    return matches

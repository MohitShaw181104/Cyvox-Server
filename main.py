from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.utils.connect_mongo_db import connectToMongoDB
from app.routes.user_route import user_router
from app.routes.auth_route import auth_router
from app.routes.complain_route import complain_router
from app.routes.upload_audio_route import upload_audio_router
from app.routes.mail_route import mail_router
from app.voice_pipeline.init_model import init_voice_models

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173"
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to MongoDB
    client = connectToMongoDB()
    db = client["cyvox_db"]
    app.state.db = db
    print("✅ MongoDB client initialized in lifespan.")
    
    # Ensure unique indexes
    user_collection = db["users"]
    user_collection.create_index("email", unique=True)
    user_collection.create_index("phoneNumber", unique=True)
    user_collection.create_index("clerkUserId", unique=True)
    print("✅ Unique indexes ensured on clerkUserId, email and phoneNumber.")
    
    print("🚀 Initializing voice models...")
    recognizer, diarization_pipeline = init_voice_models()
    app.state.recognizer = recognizer
    app.state.diarization_pipeline = diarization_pipeline
    print("✅ Models loaded and ready.")
    
    yield  # control passes to FastAPI here
    
    # CleanUp
    client.close()
    print("🧹 MongoDB client closed.")
    

app = FastAPI(title="CyVox Server", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Health-Check"])
def heath_chcek():
    return {"ok": True, "message": "CyVox Server is running!"}


app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(user_router, prefix="/user", tags=["Users"])
app.include_router(complain_router, prefix="/complaint", tags=["Complaint"])
app.include_router(upload_audio_router, tags=["Upload"])
app.include_router(mail_router, tags=["Mail"])

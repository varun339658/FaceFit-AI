"""
utils/db.py — FaceFit Database Connection
══════════════════════════════════════════
Unified MongoDB connection. All collections use the "facefit_ai" database.
"""
from pymongo import MongoClient
import os

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://mandadivarunreddy339658_db_user:varun2004@cluster0.uevkhk7.mongodb.net/?retryWrites=true&w=majority"
)

client = MongoClient(MONGO_URI)
db = client["facefit_ai"]  # ← Unified DB name for ALL collections

# Collections
face_collection    = db["face_analysis"]
wardrobe_collection = db["wardrobe"]
users_collection   = db["users"]
reminders_collection = db["outfit_reminders"]
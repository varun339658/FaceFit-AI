from pymongo import MongoClient
import os

# MongoDB Atlas connection
MONGO_URI = "mongodb+srv://mandadivarunreddy339658_db_user:varun2004@cluster0.uevkhk7.mongodb.net/?retryWrites=true&w=majority"

client = MongoClient(MONGO_URI)

db = client["facefit_ai"]

face_collection = db["face_analysis"]
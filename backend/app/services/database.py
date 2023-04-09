from pymongo import MongoClient
import os

client = MongoClient(os.environ['MONGO_URI'])
db = client["orders_db"]
orders_collection = db["orders"]
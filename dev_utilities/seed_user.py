import argparse
import pymongo
from getpass import getpass
from passlib.context import CryptContext

# Configure password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Seed user into MongoDB container')
parser.add_argument('username', help='Username of the new user')
parser.add_argument('--password', help='Password of the new user')
args = parser.parse_args()

# If the password is not provided via command-line, prompt the user for it
if args.password is None:
    password = getpass("Password: ")
else:
    password = args.password

# Hash the password
hashed_password = pwd_context.hash(password)

# Insert the user into MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["your_database_name"]
users_collection = db["users"]

new_user = {
    "username": args.username,
    "hashed_password": hashed_password
}

users_collection.insert_one(new_user)
print(f"User '{args.username}' has been seeded successfully.")

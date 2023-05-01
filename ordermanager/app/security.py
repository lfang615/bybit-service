from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import os
from pymongo import MongoClient
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

class User(BaseModel):
    username: str

class UserInDB(User):
    hashed_password: str

MONGO_URI = os.environ["MONGO_URI"]
client = MongoClient(MONGO_URI)

db = client["ordermanager"]
users_collection = db["users"]

class Security:
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    SECRET_KEY = os.environ['SECRET_KEY'] # Generate a strong secret key
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 43200 # 30 days

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def get_user_in_db(self, username: str):
        user = users_collection.find_one({"username": username})
        if user:
            return UserInDB(**user)

    def verify_password(self, plain_password, hashed_password):
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password):
        return self.pwd_context.hash(password)

    def create_access_token(self, data: dict, expires_delta: timedelta = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, os.environ['SECRET_KEY'], algorithm=os.environ['ALGORITHM'])
        return encoded_jwt

    def authenticate_user(self, username: str, password: str):
        user = users_collection.find_one({"username": username, "hashed_password": self.get_password_hash(password)})
        if not user:
            return False
        if not self.verify_password(password, user.hashed_password):
            return False
        user = UserInDB(**user)
        return user
    
    def decode_payload(self, token: str):
        payload = jwt.decode(token, os.environ['SECRET_KEY'], algorithms=[os.environ['ALGORITHM']])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        token_data = TokenData(username=username)
        return token_data
    
    async def get_current_user(self, token: str = Depends(oauth2_scheme)):
        credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
        try:
            payload = jwt.decode(token, os.environ['SECRET_KEY'], algorithms=[os.environ['ALGORITHM']])
            username: str = payload.get("sub")
            if username is None:
                raise 
            token_data = TokenData(username=username)
        except JWTError:
            raise credentials_exception
        user_db = self.get_user_in_db(token_data.username)
        if user_db is None:
            raise credentials_exception
        return User(**user_db)
    

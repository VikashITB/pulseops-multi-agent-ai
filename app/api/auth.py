from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

router = APIRouter()

# In-memory user storage for demo
_users_db = {}

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    email: str
    full_name: str
    is_active: bool = True

@router.post("/register")
async def register(user_data: UserCreate):
    email = user_data.email.lower()
    if email in _users_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # In a real app, hash the password here
    _users_db[email] = {
        "email": email,
        "full_name": user_data.full_name,
        "password": user_data.password,  # Should be hashed in production
        "is_active": True,
    }
    
    return {"message": "User registered successfully"}

@router.post("/login")
async def login(user_data: UserLogin):
    email = user_data.email.lower()
    user = _users_db.get(email)
    
    if not user or user["password"] != user_data.password:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    # In a real app, generate a JWT token here
    access_token = f"demo_token_{email}"
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def get_me():
    # In a real app, this would extract user from JWT token
    return {
        "message": "This endpoint requires JWT authentication",
        "note": "Implement JWT token validation in production"
    }

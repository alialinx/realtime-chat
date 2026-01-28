from typing import List, Optional, Literal

from pydantic import BaseModel, Field, EmailStr


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["test"])
    email: EmailStr = Field(..., examples=["test@example.com"])
    password: str = Field(..., min_length=6, max_length=128, examples=["strongpassword123"])


class MessageCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)



class CreateGroup(BaseModel):
    name:str
    description: Optional[str] = None

class UpdateGroup(BaseModel):
    name:str
    description: Optional[str] = None

class ChangeVisibility(BaseModel):
    is_private: bool

class AddMember(BaseModel):
    member_id: int
    role: Literal["member", "admin"]

class ChangeRole(BaseModel):
    role: Literal["admin","member"]

class UpdateMessageContent(BaseModel):
    content: str
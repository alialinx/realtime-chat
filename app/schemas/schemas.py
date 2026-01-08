from pydantic import BaseModel, Field

class UserRegister(BaseModel):
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        examples=["ali"]
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        examples=["strongpassword123"]
    )
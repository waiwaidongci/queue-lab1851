from typing import Literal
from pydantic import BaseModel,Field
class NoteInput(BaseModel):
    run_id:int
    title:str=Field(min_length=2,max_length=120)
    interpretation:str=Field(min_length=8,max_length=2000)
    proposal:str=Field(min_length=8,max_length=2000)
class ReviewInput(BaseModel):
    status:Literal["approved","rejected"]
    review_note:str=Field(min_length=8,max_length=1500)

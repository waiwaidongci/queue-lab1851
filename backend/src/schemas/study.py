from pydantic import BaseModel,Field
class StudyOutput(BaseModel):
    id:int
    code:str
    name:str
    description:str
    source:str
class StudyAnnotation(BaseModel):
    description:str=Field(min_length=8,max_length=1500)

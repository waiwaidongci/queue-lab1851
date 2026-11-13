from pydantic import BaseModel
class ArrivalOutput(BaseModel):
    id:int
    code:str
    study_id:int
    name:str
    arrival_rate:float
    description:str

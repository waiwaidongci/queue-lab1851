from pydantic import BaseModel,Field
class ScenarioInput(BaseModel):
    name:str=Field(min_length=2,max_length=120)
    profile_id:int
    servers:int=Field(ge=1,le=20)
    mean_service_minutes:float=Field(ge=.001,le=120,allow_inf_nan=False)

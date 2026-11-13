from pydantic import BaseModel,Field
class RunInput(BaseModel):
    name:str=Field(min_length=2,max_length=120)
    scenario_id:int
    customers:int=Field(default=3000,ge=500,le=10000)
    warmup:int=Field(default=500,ge=0,le=5000)
    replications:int=Field(default=20,ge=5,le=40)
    seed:int=Field(default=2026,ge=0,le=2147483647)
    confidence:float=Field(default=.95,ge=.8,le=.99,allow_inf_nan=False)

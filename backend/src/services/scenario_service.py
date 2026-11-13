import uuid
from fastapi import HTTPException
from ..models import ServiceScenario,ArrivalProfile
from ..utils.serialize import record
from .audit_service import log

def serialize_scenario(db,s):
    p=db.get(ArrivalProfile,s.profile_id);mu=1/s.mean_service_minutes;rho=p.arrival_rate/(s.servers*mu)
    return dict(record(s),arrival_rate=p.arrival_rate,service_rate=mu,utilization=rho,stable=rho<1,profile_name=p.name)
def list_scenarios(db):return [serialize_scenario(db,s) for s in db.query(ServiceScenario).order_by(ServiceScenario.id.desc())]
def create_scenario(db,data,user):
    if not db.get(ArrivalProfile,data.profile_id):raise HTTPException(404,"到达配置不存在")
    if db.query(ServiceScenario).filter_by(name=data.name).first():raise HTTPException(409,"情景名称已存在")
    row=ServiceScenario(**data.model_dump(),code='SC-'+uuid.uuid4().hex[:10],owner=user.name)
    db.add(row);db.flush();log(db,user.email,"scenario.create",row.code);db.commit();return serialize_scenario(db,row)

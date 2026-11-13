from fastapi import HTTPException
from ..models import CapacityNote,SimulationRun
from ..utils.serialize import record
from .audit_service import log

def list_notes(db):return [record(n) for n in db.query(CapacityNote).order_by(CapacityNote.id.desc())]
def create_note(db,data,user):
    run=db.get(SimulationRun,data.run_id)
    if not run or run.status!="completed":raise HTTPException(409,"只能对已完成运行提出容量建议")
    row=CapacityNote(**data.model_dump(),owner=user.name,status="submitted")
    db.add(row);db.flush();log(db,user.email,"capacity.submit",row.id);db.commit();return record(row)
def review_note(db,nid,data,user):
    row=db.get(CapacityNote,nid)
    if not row:raise HTTPException(404,"建议不存在")
    if row.status!="submitted":raise HTTPException(409,"已复核建议不可重复审批")
    row.status=data.status;row.reviewer=user.name;row.review_note=data.review_note
    log(db,user.email,"capacity."+data.status,row.id);db.commit();return record(row)

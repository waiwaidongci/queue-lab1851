from fastapi import HTTPException
from ..models import QueueStudy
from ..utils.serialize import record
from .audit_service import log

def list_studies(db):return [record(s) for s in db.query(QueueStudy).order_by(QueueStudy.id)]
def annotate_study(db,sid,data,user):
    row=db.get(QueueStudy,sid)
    if not row:raise HTTPException(404,"研究不存在")
    row.description=data.description;log(db,user.email,"study.annotate",row.code);db.commit();return record(row)

import uuid

from fastapi import HTTPException

from ..models import ArrivalProfile, QueueStudy
from ..utils.serialize import record
from .arrival_schedule import normalize_segments, expected_arrivals, segment_horizon
from .audit_service import log


def serialize_profile(row):
    data = record(row)
    segments = data.get("segments")
    if segments:
        data["segments"] = normalize_segments(segments)
        data["arrival_mode"] = "time_varying"
    else:
        data["segments"] = None
        data["arrival_mode"] = "constant"
    return data


def list_profiles(db):
    return [serialize_profile(p) for p in db.query(ArrivalProfile).order_by(ArrivalProfile.code)]


def create_profile(db, data, user):
    if not db.get(QueueStudy, data.study_id):
        raise HTTPException(404, "研究不存在")
    if db.query(ArrivalProfile).filter_by(name=data.name).first():
        raise HTTPException(409, "到达配置名称已存在")
    payload = data.model_dump()
    if payload.get("segments"):
        segments = normalize_segments(payload["segments"])
        horizon = segment_horizon(segments)[2]
        weighted = expected_arrivals(segments) / horizon
        profile = ArrivalProfile(code="AP-" + uuid.uuid4().hex[:10], name=payload["name"],
                                 study_id=payload["study_id"], arrival_rate=weighted,
                                 description=payload["description"], segments=segments,
                                 )
    else:
        if payload.get("arrival_rate") is None:
            raise HTTPException(422, "恒定到达配置必须提供arrival_rate，分时段配置必须提供segments")
        profile = ArrivalProfile(code="AP-" + uuid.uuid4().hex[:10], name=payload["name"],
                                 study_id=payload["study_id"],
                                 arrival_rate=float(payload["arrival_rate"]),
                                 description=payload["description"], segments=None)
    db.add(profile)
    db.flush()
    log(db, user.email, "profile.create", profile.code)
    db.commit()
    return serialize_profile(profile)

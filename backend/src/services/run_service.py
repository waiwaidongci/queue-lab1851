import csv
import io

from fastapi import HTTPException
from redis import Redis

from ..config.settings import REDIS_URL
from ..models import SimulationRun, ServiceScenario, ArrivalProfile, QueueStudy, CapacityNote
from ..utils.serialize import record
from .erlang_algorithm import erlang_c
from .arrival_schedule import normalize_segments, expected_arrivals
from .audit_service import log

queue = Redis.from_url(REDIS_URL, decode_responses=True)


def list_runs(db):
    return [record(r) for r in db.query(SimulationRun).order_by(SimulationRun.id.desc())]


def get_run(db, rid):
    row = db.get(SimulationRun, rid)
    if not row:
        raise HTTPException(404, "运行不存在")
    return row


def create_snapshot(db, scenario):
    profile = db.get(ArrivalProfile, scenario.profile_id)
    study = db.get(QueueStudy, profile.study_id)
    profile_data = record(profile)
    if profile_data.get("segments"):
        # Freeze a normalized copy so later edits to the profile cannot alter recomputation.
        profile_data["segments"] = normalize_segments(profile_data["segments"])
        profile_data["arrival_mode"] = "time_varying"
    else:
        profile_data["segments"] = None
        profile_data["arrival_mode"] = "constant"
    return {"study": record(study), "profile": profile_data, "scenario": record(scenario),
            "time_unit": "minutes", "rate_unit": "requests/minute"}


def _validate_time_varying(snapshot, replications):
    segments = normalize_segments(snapshot["profile"]["segments"])
    expected = expected_arrivals(segments)
    if expected < 100:
        raise HTTPException(422, "有限营业试验期望到达顾客至少100人，请延长营业时长或提高时段到达率")
    if expected > 50000:
        raise HTTPException(422, "单重复期望到达不超过50000人，请收窄时段表或降低到达率")
    if expected * replications > 250000:
        raise HTTPException(422, "单任务期望总顾客不超过250000，请减少重复数或营业规模")
    return segments, expected


def create_run(db, data, user):
    scenario = db.get(ServiceScenario, data.scenario_id)
    if not scenario:
        raise HTTPException(404, "服务情景不存在")
    snapshot = create_snapshot(db, scenario)
    is_time_varying = bool(snapshot["profile"]["segments"])
    replications = data.replications
    if is_time_varying:
        # Short-term overload is a legitimate finite-window experiment; no rho gate.
        _validate_time_varying(snapshot, replications)
        customers, warmup = 0, 0
    else:
        customers = data.customers if data.customers is not None else 3000
        warmup = data.warmup if data.warmup is not None else 500
        try:
            erlang_c(snapshot['profile']['arrival_rate'], 1 / scenario.mean_service_minutes,
                     scenario.servers)
        except ValueError as e:
            raise HTTPException(422, str(e))
        if customers - warmup < 100 or customers * replications > 250000:
            raise HTTPException(422, "至少保留100顾客，且单任务总顾客不超过250000")
    row = SimulationRun(name=data.name, scenario_id=scenario.id, customers=customers, warmup=warmup,
                        replications=replications, seed=data.seed, confidence=data.confidence,
                        input_snapshot=snapshot, owner=user.name)
    db.add(row)
    db.flush()
    log(db, user.email, "simulation.enqueue", row.id)
    db.commit()
    try:
        queue.rpush("queue:jobs", row.id)
    except Exception:
        row.status = "failed"
        row.error = "队列不可用，请重新提交"
        db.commit()
        raise HTTPException(503, row.error)
    return record(row)


def export_run(db, rid):
    row = get_run(db, rid)
    if row.status != "completed" or not db.query(CapacityNote).filter_by(run_id=rid,
                                                                          status="approved").first():
        raise HTTPException(403, "仅获批的完成运行可导出")
    result = row.result
    analytic_wait = ""
    if result.get("analytical"):
        analytic_wait = result["analytical"]["mean_wait_minutes"]
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(['replication', 'mean_wait_minutes', 'mean_system_minutes', 'wait_probability',
                'busy_fraction_window', 'window_minutes', 'retained_customers', 'arrival_spawn_key',
                'service_spawn_key', 'analytic_wait_minutes', 'input_hash', 'mode'])
    for x in result['replications']:
        w.writerow([x[k] for k in ['replication', 'mean_wait_minutes', 'mean_system_minutes',
                                   'wait_probability', 'busy_fraction_window', 'window_minutes',
                                   'retained_customers', 'arrival_spawn_key', 'service_spawn_key']]
                   + [analytic_wait, result['input_hash'], result.get('mode', 'constant_fixed')])
    return out.getvalue()

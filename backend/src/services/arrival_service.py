from ..models import ArrivalProfile
from ..utils.serialize import record
def list_profiles(db):return [record(p) for p in db.query(ArrivalProfile).order_by(ArrivalProfile.code)]

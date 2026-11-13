from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..controllers.dependencies import current_user, roles
from ..constants.roles import Role
from ..schemas.arrival import ArrivalInput, ArrivalOutput
from ..services.arrival_service import list_profiles, create_profile
router = APIRouter(prefix="/profiles", tags=["profiles"])
@router.get("", response_model=list[ArrivalOutput])
def index(db: Session = Depends(get_db), user=Depends(current_user)):
    return list_profiles(db)
@router.post("", status_code=201, response_model=ArrivalOutput)
def create(data: ArrivalInput, db: Session = Depends(get_db),
           user=Depends(roles(Role.ADMIN, Role.ANALYST))):
    return create_profile(db, data, user)

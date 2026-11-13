from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..controllers.dependencies import current_user
from ..schemas.arrival import ArrivalOutput
from ..services.arrival_service import list_profiles
router=APIRouter(prefix="/profiles",tags=["profiles"])
@router.get("",response_model=list[ArrivalOutput])
def index(db:Session=Depends(get_db),user=Depends(current_user)):return list_profiles(db)

from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..controllers.dependencies import current_user,roles
from ..constants.roles import Role
from ..schemas.scenario import ScenarioInput
from ..services.scenario_service import list_scenarios,create_scenario
router=APIRouter(prefix="/scenarios",tags=["scenarios"])
@router.get("")
def index(db:Session=Depends(get_db),user=Depends(current_user)):return list_scenarios(db)
@router.post("",status_code=201)
def create(data:ScenarioInput,db:Session=Depends(get_db),user=Depends(roles(Role.ADMIN,Role.ANALYST))):return create_scenario(db,data,user)

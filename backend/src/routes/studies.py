from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..controllers.dependencies import current_user,roles
from ..constants.roles import Role
from ..schemas.study import StudyOutput,StudyAnnotation
from ..services.study_service import list_studies,annotate_study
router=APIRouter(prefix="/studies",tags=["studies"])
@router.get("",response_model=list[StudyOutput])
def index(db:Session=Depends(get_db),user=Depends(current_user)):return list_studies(db)
@router.patch("/{sid}")
def annotate(sid:int,data:StudyAnnotation,db:Session=Depends(get_db),user=Depends(roles(Role.ADMIN))):return annotate_study(db,sid,data,user)

from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..controllers.dependencies import current_user,roles
from ..constants.roles import Role
from ..schemas.note import NoteInput,ReviewInput
from ..services.note_service import list_notes,create_note,review_note
router=APIRouter(prefix="/notes",tags=["notes"])
@router.get("")
def index(db:Session=Depends(get_db),user=Depends(current_user)):return list_notes(db)
@router.post("",status_code=201)
def create(data:NoteInput,db:Session=Depends(get_db),user=Depends(roles(Role.ADMIN,Role.ANALYST))):return create_note(db,data,user)
@router.patch("/{nid}/review")
def review(nid:int,data:ReviewInput,db:Session=Depends(get_db),user=Depends(roles(Role.ADMIN))):return review_note(db,nid,data,user)

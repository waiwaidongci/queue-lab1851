from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped,mapped_column
from ..config.database import Base
from ..utils.clock import now
class CapacityNote(Base):
    __tablename__="capacity_notes"
    id:Mapped[int]=mapped_column(primary_key=True)
    run_id:Mapped[int]=mapped_column(ForeignKey("simulation_runs.id"))
    title:Mapped[str]
    interpretation:Mapped[str]
    proposal:Mapped[str]
    status:Mapped[str]=mapped_column(default="submitted")
    owner:Mapped[str]
    reviewer:Mapped[str]=mapped_column(default="")
    review_note:Mapped[str]=mapped_column(default="")
    created_at:Mapped[str]=mapped_column(default=now)

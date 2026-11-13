from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped,mapped_column
from ..config.database import Base
class ArrivalProfile(Base):
    __tablename__="arrival_profiles"
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(unique=True)
    study_id:Mapped[int]=mapped_column(ForeignKey("queue_studies.id"))
    name:Mapped[str]
    arrival_rate:Mapped[float]
    description:Mapped[str]

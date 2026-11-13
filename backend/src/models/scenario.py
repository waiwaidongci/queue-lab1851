from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped,mapped_column
from ..config.database import Base
class ServiceScenario(Base):
    __tablename__="service_scenarios"
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(unique=True)
    name:Mapped[str]=mapped_column(unique=True)
    profile_id:Mapped[int]=mapped_column(ForeignKey("arrival_profiles.id"))
    servers:Mapped[int]
    mean_service_minutes:Mapped[float]
    owner:Mapped[str]

from sqlalchemy import ForeignKey,JSON
from sqlalchemy.orm import Mapped,mapped_column
from ..config.database import Base
from ..utils.clock import now
class SimulationRun(Base):
    __tablename__="simulation_runs"
    id:Mapped[int]=mapped_column(primary_key=True)
    name:Mapped[str]
    scenario_id:Mapped[int]=mapped_column(ForeignKey("service_scenarios.id"))
    customers:Mapped[int]
    warmup:Mapped[int]
    replications:Mapped[int]
    seed:Mapped[int]
    confidence:Mapped[float]
    input_snapshot:Mapped[dict]=mapped_column(JSON)
    status:Mapped[str]=mapped_column(default="queued")
    result:Mapped[dict]=mapped_column(JSON,default=dict)
    error:Mapped[str]=mapped_column(default="")
    owner:Mapped[str]
    created_at:Mapped[str]=mapped_column(default=now)

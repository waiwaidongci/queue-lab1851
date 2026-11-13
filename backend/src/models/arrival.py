from sqlalchemy import ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from ..config.database import Base


class ArrivalProfile(Base):
    __tablename__ = "arrival_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("queue_studies.id"))
    name: Mapped[str]
    # Constant profiles keep a single lambda here. Time-varying profiles store the
    # weighted mean rate here for backward-compatible listings, while segments
    # holds the frozen piecewise-constant intensity table.
    arrival_rate: Mapped[float]
    description: Mapped[str]
    segments: Mapped[dict | None] = mapped_column(JSON, nullable=True)

from sqlalchemy.orm import Mapped,mapped_column
from ..config.database import Base
class QueueStudy(Base):
    __tablename__="queue_studies"
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(unique=True)
    name:Mapped[str]
    description:Mapped[str]
    source:Mapped[str]

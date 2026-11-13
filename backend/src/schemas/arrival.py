from pydantic import BaseModel, Field


class SegmentInput(BaseModel):
    duration_minutes: float = Field(ge=1e-3, le=100000, allow_inf_nan=False)
    arrival_rate: float = Field(ge=0, le=1000, allow_inf_nan=False)


class ArrivalInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    study_id: int
    description: str = Field(min_length=2, max_length=500)
    arrival_rate: float | None = Field(default=None, ge=1e-6, le=1000, allow_inf_nan=False)
    segments: list[SegmentInput] | None = Field(default=None, min_length=1, max_length=24)


class ArrivalOutput(BaseModel):
    id: int
    code: str
    study_id: int
    name: str
    arrival_rate: float
    description: str
    segments: list[dict] | None = None
    arrival_mode: str = "constant"

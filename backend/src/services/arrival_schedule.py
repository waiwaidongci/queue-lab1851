"""Non-homogeneous Poisson arrivals for time-varying arrival intensity.

A business day is described by consecutive intensity segments: each segment has
a duration in minutes and a constant Poisson rate lambda (requests/minute).
Arrivals are generated with Lewis-Shedler thinning over the whole finite
horizon, so the queue built in one segment carries into the next. Segments with
rate zero are legal and simply produce no arrivals; they are still first-class
intervals in the statistics.
"""
import math

RATE_MIN = 0.0
RATE_MAX = 1000.0
SEGMENTS_MIN = 1
SEGMENTS_MAX = 24
DURATION_MIN = 1e-3
DURATION_MAX = 100000.0
# Expected arrivals per replication are capped so a mis-scaled segment table
# cannot request unbounded memory; the per-task cap still applies on top.
EXPECTED_PER_REPLICATION_CAP = 50000


def normalize_segments(segments):
    """Validate and normalize a segment table to [{duration_minutes, arrival_rate}]."""
    if not isinstance(segments, list) or not SEGMENTS_MIN <= len(segments) <= SEGMENTS_MAX:
        raise ValueError(f"分时段表须为{SEGMENTS_MIN}–{SEGMENTS_MAX}个区间的列表")
    normalized = []
    for index, seg in enumerate(segments):
        if not isinstance(seg, dict):
            raise ValueError("每个时段须为含duration_minutes与arrival_rate的对象")
        duration = seg.get("duration_minutes")
        rate = seg.get("arrival_rate")
        if type(duration) not in (int, float) or not math.isfinite(duration) \
                or not DURATION_MIN <= duration <= DURATION_MAX:
            raise ValueError(f"时段{index + 1}时长须为[{DURATION_MIN},{DURATION_MAX}]分钟内有限数")
        if type(rate) not in (int, float) or not math.isfinite(rate) \
                or not RATE_MIN <= rate <= RATE_MAX:
            raise ValueError(f"时段{index + 1}到达率须为[{RATE_MIN},{RATE_MAX}]请求/分钟内有限数")
        normalized.append({"duration_minutes": float(duration), "arrival_rate": float(rate)})
    return normalized


def segment_horizon(segments):
    """Return (boundaries, rates, total_horizon). Boundaries are cumulative minutes."""
    boundaries, rates, cursor = [], [], 0.0
    for seg in segments:
        cursor += seg["duration_minutes"]
        boundaries.append(cursor)
        rates.append(seg["arrival_rate"])
    return boundaries, rates, cursor


def expected_arrivals(segments):
    return sum(seg["duration_minutes"] * seg["arrival_rate"] for seg in segments)


def segment_index_at(time, boundaries):
    """Index of the segment containing time; a time exactly on a boundary belongs to the next segment."""
    for index, boundary in enumerate(boundaries):
        if time < boundary:
            return index
    return len(boundaries) - 1


def generate_nhpp_arrivals(segments, rng):
    """Lewis-Shedler thinning for a piecewise-constant Poisson process on [0, horizon).

    Returns a sorted list of arrival times in minutes. A zero-rate table returns
    an empty list; callers decide whether an empty replication is acceptable.
    """
    boundaries, rates, horizon = segment_horizon(segments)
    peak = max(rates)
    if peak <= 0.0 or horizon <= 0.0:
        return []
    arrivals = []
    cursor = 0.0
    while True:
        cursor += rng.exponential(1.0 / peak)
        if cursor >= horizon:
            break
        index = segment_index_at(cursor, boundaries)
        if rng.random() < rates[index] / peak:
            arrivals.append(float(cursor))
    return arrivals

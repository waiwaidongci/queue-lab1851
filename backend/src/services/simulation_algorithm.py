"""Arrival-event FCFS scheduler with explicit service-completion heap and independent replications.

Two experiment modes share the same FCFS event core:

* constant fixed-customer mode: a stationary Poisson stream of a fixed number of
  customers, warmup customers dropped from the statistics, compared with an
  Erlang-C steady-state analytic value;
* time-varying finite-business mode: a piecewise-constant Poisson process over a
  finite horizon, admission stops at closing time and every arrived customer is
  still served (queue drains). Short-term overload is allowed, no steady-state
  value is produced, and business-period backlog is reported separately from
  post-closing drain waiting.
"""
import heapq
import math

import numpy as np
from scipy.stats import t

from .erlang_algorithm import erlang_c
from .arrival_schedule import generate_nhpp_arrivals, normalize_segments, segment_horizon, expected_arrivals

WAIT_EPS = 1e-12


def _finite_number(x, positive=False):
    if type(x) not in (float, int, np.float64) or abs(x) > 1e15 or not math.isfinite(x):
        return False
    return x > 0 if positive else x >= 0


def schedule_fcfs(arrivals, services, servers, warmup=0, segments=None, closing_time=None):
    if type(servers) is not int or not 1 <= servers <= 20:
        raise ValueError("服务台数量无效")
    if len(arrivals) != len(services) or (not arrivals and segments is None):
        raise ValueError("到达/服务数组长度须相同且非空")
    if type(warmup) is not int or not 0 <= warmup <= len(arrivals):
        raise ValueError("warmup必须按顾客序号且不超过顾客总数")
    if segments is not None and warmup != 0:
        raise ValueError("有限营业模式不剔除暖机顾客，warmup必须为0")
    if any(not _finite_number(x) for x in arrivals):
        raise ValueError("到达时间须非负有限")
    if any(not _finite_number(x, positive=True) for x in services):
        raise ValueError("服务时长须正且有限")
    if any(b < a for a, b in zip(arrivals, arrivals[1:])):
        raise ValueError("到达事件必须按时间升序，FCFS保留同刻输入顺序")

    completion_heap = [(0., i) for i in range(servers)]
    heapq.heapify(completion_heap)
    waiting_starts = []
    records = []
    for i, (arrival, service) in enumerate(zip(arrivals, services)):
        while waiting_starts and waiting_starts[0] <= arrival:
            heapq.heappop(waiting_starts)
        available, server = heapq.heappop(completion_heap)
        start = max(float(arrival), available)
        finish = start + float(service)
        wait = start - float(arrival)
        if wait > WAIT_EPS:
            heapq.heappush(waiting_starts, start)
        records.append({"customer": i + 1, "arrival": float(arrival), "service_start": start,
                        "completion": finish, "server": server + 1, "wait": wait,
                        "system": finish - float(arrival), "queue_after_arrival": len(waiting_starts)})
        heapq.heappush(completion_heap, (finish, server))

    retained = records[warmup:]
    if retained:
        begin = retained[0]['arrival']
        end = max(r['completion'] for r in records)
        duration = end - begin
        busy = sum(max(0., min(r['completion'], end) - max(r['service_start'], begin)) for r in records)
        summary = {
            "mean_wait_minutes": float(np.mean([r['wait'] for r in retained])),
            "mean_system_minutes": float(np.mean([r['system'] for r in retained])),
            "wait_probability": sum(r['wait'] > WAIT_EPS for r in retained) / len(retained),
            "max_wait_minutes": max(r['wait'] for r in retained),
            "busy_fraction_window": busy / (servers * duration) if duration > 0 else 0.0,
            "window_minutes": duration,
            "retained_customers": len(retained),
        }
    else:
        # Finite-business replications may draw zero arrivals (e.g. an all-zero
        # table); the interval still exists, its statistics are simply null.
        summary = {"mean_wait_minutes": None, "mean_system_minutes": None, "wait_probability": None,
                   "max_wait_minutes": None, "busy_fraction_window": None, "window_minutes": 0.0,
                   "retained_customers": 0}

    if segments is None:
        return {**summary, "records": records}

    boundaries, rates, horizon = segment_horizon(segments)
    if closing_time is None:
        closing_time = horizon
    segment_rows = _segment_statistics(records, segments, boundaries)
    drain = _drain_statistics(records, closing_time)
    return {**summary, "records": records, "segments": segment_rows, "drain": drain,
            "closing_time_minutes": float(closing_time),
            "last_completion_minutes": float(max((r['completion'] for r in records), default=closing_time))}


def _segment_statistics(records, segments, boundaries):
    """Per-interval waits and end-of-interval backlog. Empty intervals are kept as rows."""
    starts = [0.0] + boundaries[:-1]
    buckets = [[] for _ in segments]
    for r in records:
        index = 0
        while index < len(boundaries) and r['arrival'] >= boundaries[index]:
            index += 1
        if index < len(segments):
            buckets[index].append(r)
    rows = []
    for k, seg in enumerate(segments):
        boundary = boundaries[k]
        # Arrivals strictly before the boundary belong to this interval; an
        # arrival exactly on a boundary opens the next interval.
        arrived = [r for r in records if r['arrival'] < boundary]
        in_system = [r for r in arrived if r['completion'] > boundary]
        waiting = [r for r in arrived if r['service_start'] > boundary]
        in_service = [r for r in arrived if r['service_start'] <= boundary < r['completion']]
        members = buckets[k]
        rows.append({
            "segment": k + 1,
            "start_minutes": float(starts[k]),
            "end_minutes": float(boundary),
            "arrival_rate": float(seg['arrival_rate']),
            "arrivals": len(members),
            "mean_wait_minutes": float(np.mean([r['wait'] for r in members])) if members else None,
            "wait_probability": sum(r['wait'] > WAIT_EPS for r in members) / len(members) if members else None,
            "max_wait_minutes": max((r['wait'] for r in members), default=None),
            "mean_system_minutes": float(np.mean([r['system'] for r in members])) if members else None,
            "backlog_at_end": len(in_system),
            "waiting_at_end": len(waiting),
            "in_service_at_end": len(in_service),
        })
    return rows


def _drain_statistics(records, closing_time):
    """Split each wait into business-period and post-closing (drain) portions."""
    before_parts, after_parts = [], []
    waiting_at_close = in_service_at_close = 0
    drain_customers = 0
    for r in records:
        if r['arrival'] >= closing_time:
            continue
        remaining_at_close = closing_time - r['arrival']
        before = min(r['wait'], remaining_at_close)
        after = max(0.0, r['wait'] - remaining_at_close)
        before_parts.append(before)
        after_parts.append(after)
        if after > WAIT_EPS:
            drain_customers += 1
        if r['service_start'] > closing_time:
            waiting_at_close += 1
        elif r['service_start'] <= closing_time < r['completion']:
            in_service_at_close += 1
    last_completion = max((r['completion'] for r in records), default=closing_time)
    total = len(before_parts)
    return {
        "backlog_at_close": waiting_at_close + in_service_at_close,
        "waiting_at_close": waiting_at_close,
        "in_service_at_close": in_service_at_close,
        "drain_duration_minutes": max(0.0, last_completion - closing_time),
        "business_mean_wait_minutes": float(np.mean(before_parts)) if total else None,
        "drain_mean_wait_minutes": float(np.mean(after_parts)) if total else None,
        "drain_conditional_wait_minutes": float(sum(after_parts) / drain_customers) if drain_customers else None,
        "drain_customer_count": drain_customers,
        "served_customers": total,
    }


def mean_t_interval(values, confidence=.95):
    values = [v for v in values if v is not None]
    if len(values) < 2 or not all(math.isfinite(v) for v in values):
        raise ValueError("t区间至少需要2个有限重复均值")
    if type(confidence) not in (int, float) or not .8 <= confidence <= .99:
        raise ValueError("置信水平须在[.8,.99]")
    mean = float(np.mean(values))
    sd = float(np.std(values, ddof=1))
    se = sd / math.sqrt(len(values))
    critical = float(t.ppf((1 + confidence) / 2, len(values) - 1))
    return {"mean": mean, "lower": mean - critical * se, "upper": mean + critical * se,
            "standard_error": se, "degrees_of_freedom": len(values) - 1, "critical_t": critical,
            "degenerate": sd == 0, "confidence": confidence}


def _validate_replication_params(customers, warmup, replications, seed):
    if type(customers) is not int or not 500 <= customers <= 10000 or type(warmup) is not int \
            or not 0 <= warmup <= 5000 or customers - warmup < 100:
        raise ValueError("顾客500–10000，warmup最多5000且至少保留100个顾客")
    if type(replications) is not int or not 5 <= replications <= 40 or customers * replications > 250000:
        raise ValueError("重复5–40次，单任务总顾客上限250000")
    if type(seed) is not int or not 0 <= seed <= 2147483647:
        raise ValueError("随机种子须为0到2147483647整数")


def simulate_replicates(arrival_rate, service_rate, servers, customers=3000, warmup=500,
                        replications=20, seed=2026, confidence=.95):
    analytic = erlang_c(arrival_rate, service_rate, servers)
    _validate_replication_params(customers, warmup, replications, seed)
    streams = np.random.SeedSequence(seed).spawn(replications)
    results, sample = [], []
    for index, child in enumerate(streams):
        arrival_child, service_child = child.spawn(2)
        arrival_rng = np.random.default_rng(arrival_child)
        service_rng = np.random.default_rng(service_child)
        arrivals = np.cumsum(arrival_rng.exponential(1 / arrival_rate, customers)).tolist()
        services = service_rng.exponential(1 / service_rate, customers).tolist()
        simulation = schedule_fcfs(arrivals, services, servers, warmup)
        records = simulation.pop('records')
        results.append({"replication": index + 1, "arrival_spawn_key": list(arrival_child.spawn_key),
                        "service_spawn_key": list(service_child.spawn_key), **simulation})
        if index == 0:
            sample = records[::max(1, len(records) // 100)]
            if sample[-1]['customer'] != records[-1]['customer']:
                sample.append(records[-1])
    interval = mean_t_interval([r['mean_wait_minutes'] for r in results], confidence)
    return {
        "mode": "constant_fixed",
        "steady_state_applicable": True,
        "analytical": analytic,
        "replications": results,
        "wait_interval": interval,
        "system_interval": mean_t_interval([r['mean_system_minutes'] for r in results], confidence),
        "mean_wait_probability": float(np.mean([r['wait_probability'] for r in results])),
        "mean_busy_fraction_window": float(np.mean([r['busy_fraction_window'] for r in results])),
        "sample_customers": sample,
        "customers": customers, "warmup": warmup,
        "retained_per_replication": customers - warmup, "replication_count": replications, "seed": seed,
        "mean_difference_minutes": interval['mean'] - analytic['mean_wait_minutes'],
        "assumptions": "Poisson到达、同速独立指数服务、无限等待空间、FCFS、同刻按顾客输入顺序；初始系统为空。暖机按每次重复的前warmup个顾客剔除。",
        "ci_note": "区间是独立重复的平均等待均值t区间，不是顾客独立样本区间；不含模型或暖机偏差，未经非负截断。",
        "finite_window_note": "仿真生成固定顾客数并服务至全部完成；忙碌率窗口从首个保留顾客到达到全部服务完成，含排空效应，不等于稳态解析精确值。",
    }


def simulate_time_varying(segments, service_rate, servers, replications=20, seed=2026, confidence=.95):
    """Finite-business experiment with piecewise-constant arrival intensity."""
    segments = normalize_segments(segments)
    if type(service_rate) not in (int, float) or not 1e-6 <= service_rate <= 1000 or not math.isfinite(service_rate):
        raise ValueError("单台服务率必须为[1e-6,1000]内有限正数，单位每分钟")
    if type(servers) is not int or not 1 <= servers <= 20:
        raise ValueError("服务台数量必须是1到20的整数")
    if type(replications) is not int or not 5 <= replications <= 40:
        raise ValueError("重复5–40次")
    if type(seed) is not int or not 0 <= seed <= 2147483647:
        raise ValueError("随机种子须为0到2147483647整数")
    expected = expected_arrivals(segments)
    horizon = segment_horizon(segments)[2]
    if expected < 100:
        raise ValueError("有限营业试验期望到达顾客至少100人，请延长营业时长或提高时段到达率")
    if expected > 50000:
        raise ValueError("单重复期望到达不超过50000人，请收窄时段表或降低到达率")
    if expected * replications > 250000:
        raise ValueError("单任务期望总顾客不超过250000，请减少重复数或营业规模")

    streams = np.random.SeedSequence(seed).spawn(replications)
    results, sample = [], []
    for index, child in enumerate(streams):
        arrival_child, service_child = child.spawn(2)
        arrival_rng = np.random.default_rng(arrival_child)
        service_rng = np.random.default_rng(service_child)
        arrivals = generate_nhpp_arrivals(segments, arrival_rng)
        services = service_rng.exponential(1 / service_rate, len(arrivals)).tolist() if arrivals else []
        simulation = schedule_fcfs(arrivals, services, servers, warmup=0, segments=segments,
                                   closing_time=horizon)
        records = simulation.pop('records')
        results.append({"replication": index + 1, "arrival_spawn_key": list(arrival_child.spawn_key),
                        "service_spawn_key": list(service_child.spawn_key), **simulation})
        if index == 0:
            sample = records[::max(1, len(records) // 100)] if records else []
            if records and sample[-1]['customer'] != records[-1]['customer']:
                sample.append(records[-1])

    nonempty = [r for r in results if r['retained_customers'] > 0]
    if len(nonempty) < 2:
        raise ValueError("有效重复不足2次，无法构造t区间；请提高期望到达量")
    wait_interval = mean_t_interval([r['mean_wait_minutes'] for r in nonempty], confidence)
    system_interval = mean_t_interval([r['mean_system_minutes'] for r in nonempty], confidence)
    business_interval = mean_t_interval([r['drain']['business_mean_wait_minutes'] for r in nonempty], confidence)
    drain_interval = mean_t_interval([r['drain']['drain_mean_wait_minutes'] for r in nonempty], confidence)
    drain_duration_interval = mean_t_interval([r['drain']['drain_duration_minutes'] for r in results], confidence)

    segment_summary = _aggregate_segments(results, segments)
    drain_summary = _aggregate_drain(results)
    peak_rate = max(s['arrival_rate'] for s in segments)
    overload = peak_rate >= servers * service_rate
    return {
        "mode": "time_varying_finite",
        "steady_state_applicable": False,
        "analytical": None,
        "replications": results,
        "wait_interval": wait_interval,
        "system_interval": system_interval,
        "business_wait_interval": business_interval,
        "drain_wait_interval": drain_interval,
        "drain_duration_interval": drain_duration_interval,
        "segment_summary": segment_summary,
        "drain_summary": drain_summary,
        "mean_wait_probability": float(np.mean([r['wait_probability'] for r in nonempty])),
        "mean_busy_fraction_window": float(np.mean([r['busy_fraction_window'] for r in nonempty])),
        "sample_customers": sample,
        "segments": segments,
        "horizon_minutes": horizon,
        "expected_arrivals_per_replication": expected,
        "mean_arrivals_per_replication": float(np.mean([r['retained_customers'] for r in results])),
        "warmup": 0,
        "retained_per_replication": int(round(expected)),
        "replication_count": replications,
        "seed": seed,
        "short_term_overload": overload,
        "peak_segment_rate": peak_rate,
        "capacity_per_minute": servers * service_rate,
        "assumptions": "分段齐次Poisson到达（Lewis-Shedler稀疏抽样）、同速独立指数服务、无限等待空间、FCFS；初始系统为空，队列跨时段保留，营业时刻停止接收后服务完所有已到达顾客。",
        "ci_note": "区间是独立重复均值的t区间，不是顾客独立样本区间；不含模型偏差，未经非负截断。营业期/排空等待按顾客等待时间在停收时刻切分。",
        "finite_window_note": "有限营业试验不存在稳态：分段强度随时间变化且允许短时超载，故不输出Erlang-C稳态值；排空时长与排空等待是停收后的有限时段效应。",
    }


def _aggregate_segments(results, segments):
    rows = []
    for k in range(len(segments)):
        per_rep = [r['segments'][k] for r in results]
        total_arrivals = sum(row['arrivals'] for row in per_rep)
        # Pooled sums give customer-weighted descriptive means across replications.
        sum_wait = sum(row['mean_wait_minutes'] * row['arrivals'] for row in per_rep
                       if row['mean_wait_minutes'] is not None)
        sum_system = sum(row['mean_system_minutes'] * row['arrivals'] for row in per_rep
                         if row['mean_system_minutes'] is not None)
        sum_waiting = sum(row['wait_probability'] * row['arrivals'] for row in per_rep
                          if row['wait_probability'] is not None)
        rows.append({
            "segment": k + 1,
            "start_minutes": per_rep[0]['start_minutes'],
            "end_minutes": per_rep[0]['end_minutes'],
            "arrival_rate": per_rep[0]['arrival_rate'],
            "mean_arrivals": float(np.mean([row['arrivals'] for row in per_rep])),
            "total_arrivals": total_arrivals,
            "mean_wait_minutes": sum_wait / total_arrivals if total_arrivals else None,
            "mean_system_minutes": sum_system / total_arrivals if total_arrivals else None,
            "wait_probability": sum_waiting / total_arrivals if total_arrivals else None,
            "max_wait_minutes": max((row['max_wait_minutes'] for row in per_rep
                                     if row['max_wait_minutes'] is not None), default=None),
            "mean_backlog_at_end": float(np.mean([row['backlog_at_end'] for row in per_rep])),
            "mean_waiting_at_end": float(np.mean([row['waiting_at_end'] for row in per_rep])),
            "mean_in_service_at_end": float(np.mean([row['in_service_at_end'] for row in per_rep])),
        })
    return rows


def _aggregate_drain(results):
    nonempty = [r for r in results if r['retained_customers'] > 0]
    total_drain_customers = sum(r['drain']['drain_customer_count'] for r in nonempty)
    conditional = sum(r['drain']['drain_conditional_wait_minutes'] * r['drain']['drain_customer_count']
                      for r in nonempty if r['drain']['drain_conditional_wait_minutes'] is not None)
    return {
        "mean_backlog_at_close": float(np.mean([r['drain']['backlog_at_close'] for r in results])),
        "mean_waiting_at_close": float(np.mean([r['drain']['waiting_at_close'] for r in results])),
        "mean_in_service_at_close": float(np.mean([r['drain']['in_service_at_close'] for r in results])),
        "mean_drain_duration_minutes": float(np.mean([r['drain']['drain_duration_minutes'] for r in results])),
        "mean_drain_customer_count": float(np.mean([r['drain']['drain_customer_count'] for r in results])),
        "drain_conditional_wait_minutes": conditional / total_drain_customers if total_drain_customers else None,
    }

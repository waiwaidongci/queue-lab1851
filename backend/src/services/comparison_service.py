from .simulation_algorithm import simulate_replicates, simulate_time_varying
from ..utils.fingerprint import fingerprint

CONSTANT_METHOD = "erlangc-fcfs-independent-t-v1"
TIME_VARYING_METHOD = "time-varying-fcfs-drain-t-v1"


def calculate_run(snapshot, customers, warmup, replications, seed, confidence):
    s = snapshot['scenario']
    p = snapshot['profile']
    if p.get('segments'):
        result = simulate_time_varying(p['segments'], 1 / s['mean_service_minutes'], s['servers'],
                                       replications, seed, confidence)
        method = TIME_VARYING_METHOD
        fingerprint_payload = {"method": method, "snapshot": snapshot,
                               "replications": replications, "seed": seed, "confidence": confidence}
    else:
        result = simulate_replicates(p['arrival_rate'], 1 / s['mean_service_minutes'], s['servers'],
                                     customers, warmup, replications, seed, confidence)
        method = CONSTANT_METHOD
        fingerprint_payload = {"method": method, "snapshot": snapshot, "customers": customers,
                               "warmup": warmup, "replications": replications, "seed": seed,
                               "confidence": confidence}
    result['input_snapshot'] = snapshot
    result['input_hash'] = fingerprint(fingerprint_payload)
    result['method_version'] = method
    return result

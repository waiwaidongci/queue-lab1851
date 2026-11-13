from .simulation_algorithm import simulate_replicates
from ..utils.fingerprint import fingerprint

def calculate_run(snapshot,customers,warmup,replications,seed,confidence):
    s=snapshot['scenario'];p=snapshot['profile']
    result=simulate_replicates(p['arrival_rate'],1/s['mean_service_minutes'],s['servers'],customers,warmup,replications,seed,confidence)
    result['input_snapshot']=snapshot;result['input_hash']=fingerprint({"method":"erlangc-fcfs-independent-t-v1","snapshot":snapshot,"customers":customers,"warmup":warmup,"replications":replications,"seed":seed,"confidence":confidence});result['method_version']='erlangc-fcfs-independent-t-v1'
    return result

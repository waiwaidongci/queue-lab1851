"""Arrival-event FCFS scheduler with explicit service-completion heap and independent replications."""
import heapq,math
import numpy as np
from scipy.stats import t
from .erlang_algorithm import erlang_c

def schedule_fcfs(arrivals,services,servers,warmup=0):
    if type(servers) is not int or not 1<=servers<=20:raise ValueError("服务台数量无效")
    if len(arrivals)!=len(services) or not arrivals:raise ValueError("到达/服务数组长度须相同且非空")
    if type(warmup) is not int or not 0<=warmup<len(arrivals):raise ValueError("warmup必须按顾客序号且小于顾客总数")
    if any(type(x) not in (float,int,np.float64) or abs(x)>1e15 or not math.isfinite(x) or x<0 for x in arrivals):raise ValueError("到达时间须非负有限")
    if any(type(x) not in (float,int,np.float64) or abs(x)>1e15 or not math.isfinite(x) or x<=0 for x in services):raise ValueError("服务时长须正且有限")
    if any(b<a for a,b in zip(arrivals,arrivals[1:])):raise ValueError("到达事件必须按时间升序，FCFS保留同刻输入顺序")
    completion_heap=[(0.,i) for i in range(servers)];heapq.heapify(completion_heap);waiting_starts=[];records=[]
    for i,(arrival,service) in enumerate(zip(arrivals,services)):
        while waiting_starts and waiting_starts[0]<=arrival:heapq.heappop(waiting_starts)
        available,server=heapq.heappop(completion_heap);start=max(float(arrival),available);finish=start+float(service);wait=start-float(arrival)
        if wait>1e-12:heapq.heappush(waiting_starts,start)
        records.append({"customer":i+1,"arrival":float(arrival),"service_start":start,"completion":finish,"server":server+1,"wait":wait,"system":finish-float(arrival),"queue_after_arrival":len(waiting_starts)})
        heapq.heappush(completion_heap,(finish,server))
    retained=records[warmup:];begin=retained[0]['arrival'];end=max(r['completion'] for r in records);duration=end-begin
    busy=sum(max(0.,min(r['completion'],end)-max(r['service_start'],begin)) for r in records)
    return {"mean_wait_minutes":float(np.mean([r['wait'] for r in retained])),"mean_system_minutes":float(np.mean([r['system'] for r in retained])),"wait_probability":sum(r['wait']>1e-12 for r in retained)/len(retained),"max_wait_minutes":max(r['wait'] for r in retained),"busy_fraction_window":busy/(servers*duration),"window_minutes":duration,"retained_customers":len(retained),"records":retained}

def mean_t_interval(values,confidence=.95):
    if len(values)<2 or not all(math.isfinite(v) for v in values):raise ValueError("t区间至少需要2个有限重复均值")
    if type(confidence) not in (int,float) or not .8<=confidence<=.99:raise ValueError("置信水平须在[.8,.99]")
    mean=float(np.mean(values));sd=float(np.std(values,ddof=1));se=sd/math.sqrt(len(values));critical=float(t.ppf((1+confidence)/2,len(values)-1))
    return {"mean":mean,"lower":mean-critical*se,"upper":mean+critical*se,"standard_error":se,"degrees_of_freedom":len(values)-1,"critical_t":critical,"degenerate":sd==0,"confidence":confidence}

def simulate_replicates(arrival_rate,service_rate,servers,customers=3000,warmup=500,replications=20,seed=2026,confidence=.95):
    analytic=erlang_c(arrival_rate,service_rate,servers)
    if type(customers) is not int or not 500<=customers<=10000 or type(warmup) is not int or not 0<=warmup<=5000 or customers-warmup<100:raise ValueError("顾客500–10000，warmup最多5000且至少保留100个顾客")
    if type(replications) is not int or not 5<=replications<=40 or customers*replications>250000:raise ValueError("重复5–40次，单任务总顾客上限250000")
    if type(seed) is not int or not 0<=seed<=2147483647:raise ValueError("随机种子须为0到2147483647整数")
    streams=np.random.SeedSequence(seed).spawn(replications);results=[];sample=[]
    for index,child in enumerate(streams):
        arrival_child,service_child=child.spawn(2)
        arrival_rng=np.random.default_rng(arrival_child);service_rng=np.random.default_rng(service_child)
        arrivals=np.cumsum(arrival_rng.exponential(1/arrival_rate,customers)).tolist();services=service_rng.exponential(1/service_rate,customers).tolist()
        simulation=schedule_fcfs(arrivals,services,servers,warmup);records=simulation.pop('records')
        results.append({"replication":index+1,"arrival_spawn_key":list(arrival_child.spawn_key),"service_spawn_key":list(service_child.spawn_key),**simulation})
        if index==0:
            sample=records[::max(1,len(records)//100)]
            if sample[-1]['customer']!=records[-1]['customer']:sample.append(records[-1])
    interval=mean_t_interval([r['mean_wait_minutes'] for r in results],confidence)
    return {"analytical":analytic,"replications":results,"wait_interval":interval,"system_interval":mean_t_interval([r['mean_system_minutes'] for r in results],confidence),"mean_wait_probability":float(np.mean([r['wait_probability'] for r in results])),"mean_busy_fraction_window":float(np.mean([r['busy_fraction_window'] for r in results])),"sample_customers":sample,"customers":customers,"warmup":warmup,"retained_per_replication":customers-warmup,"replication_count":replications,"seed":seed,"mean_difference_minutes":interval['mean']-analytic['mean_wait_minutes'],"assumptions":"Poisson到达、同速独立指数服务、无限等待空间、FCFS、同刻按顾客输入顺序；初始系统为空。暖机按每次重复的前warmup个顾客剔除。","ci_note":"区间是独立重复的平均等待均值t区间，不是顾客独立样本区间；不含模型或暖机偏差，未经非负截断。","finite_window_note":"仿真生成固定顾客数并服务至全部完成；忙碌率窗口从首个保留顾客到达到全部服务完成，含排空效应，不等于稳态解析精确值。"}

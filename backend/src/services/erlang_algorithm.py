import math

def erlang_c(arrival_rate,service_rate,servers):
    for value in [arrival_rate,service_rate]:
        if type(value) not in (int,float) or not 1e-6<=value<=1000 or not math.isfinite(value):raise ValueError("到达率和单台服务率必须为[1e-6,1000]内有限正数，单位每分钟")
    if type(servers) is not int or not 1<=servers<=20:raise ValueError("服务台数量必须是1到20的整数")
    utilization=arrival_rate/(servers*service_rate)
    if utilization>=1:raise ValueError("lambda必须小于c*mu；此情景无M/M/c稳态，不能套用Erlang-C")
    offered=arrival_rate/service_rate;term=1.;partial=1.
    for n in range(1,servers):term*=offered/n;partial+=term
    term*=offered/servers;tail=term/(1-utilization);p0=1/(partial+tail);wait_probability=tail*p0
    wait=wait_probability/(servers*service_rate-arrival_rate)
    return {"arrival_rate":arrival_rate,"service_rate":service_rate,"servers":servers,"utilization":utilization,"p0":p0,"wait_probability":wait_probability,"mean_wait_minutes":wait,"mean_system_minutes":wait+1/service_rate,"mean_queue_length":arrival_rate*wait,"mean_system_length":arrival_rate*(wait+1/service_rate),"capacity_per_minute":servers*service_rate}

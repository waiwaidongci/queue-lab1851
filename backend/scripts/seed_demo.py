import json
from src.config.database import Base,engine,SessionLocal
from src.models import User,QueueStudy,ArrivalProfile,ServiceScenario,SimulationRun,CapacityNote
from src.utils.security import hash_password
from src.services.run_service import create_snapshot
from src.services.comparison_service import calculate_run

def seed():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for role,name in [("admin","陆潮 · 运营研究负责人"),("analyst","季遥 · 排队分析员"),("viewer","沈帆 · 窗口观察员")]:
            email=role+"@zhanqiao.demo"
            if not db.query(User).filter_by(email=email).first():db.add(User(email=email,name=name,role=role,password_hash=hash_password("Zhanqiao2026!")))
        studies=[]
        for code,name in [('Q-01','东栈桥 · 船舶票证窗口'),('Q-02','西栈桥 · 靠泊资料窗口')]:
            study=db.query(QueueStudy).filter_by(code=code).first()
            if not study:study=QueueStudy(code=code,name=name,description="匿名票证请求的容量研究，固定Poisson到达与指数服务假设，不用于实时人员调度。",source="pier-window-parameters-202611.json");db.add(study);db.flush()
            studies.append(study)
        profiles=[]
        for i,(code,name,rate) in enumerate([('AP-AM','上午常态',.45),('AP-PM','午后集中',.7),('AP-PEAK','靠泊集中时段',1.05)]):
            profile=db.query(ArrivalProfile).filter_by(code=code).first()
            if not profile:profile=ArrivalProfile(code=code,name=name,study_id=studies[0 if i<2 else 1].id,arrival_rate=rate,description="每分钟请求数lambda；仅作恒定到达率的模拟配置，不是真实预测。");db.add(profile);db.flush()
            profiles.append(profile)
        scenarios=[]
        for i,profile in enumerate(profiles):
            for servers in [2,3]:
                code=f"SC-{i+1}-{servers}";scenario=db.query(ServiceScenario).filter_by(code=code).first()
                if not scenario:scenario=ServiceScenario(code=code,name=f"{profile.name} · {servers}台服务",profile_id=profile.id,servers=servers,mean_service_minutes=2.5 if i==0 else 1/.45,owner="季遥 · 排队分析员");db.add(scenario);db.flush()
                scenarios.append(scenario)
        if not db.query(SimulationRun).filter_by(name="上午双窗口 · 基准独立重复").first():
            scenario=scenarios[0];snapshot=create_snapshot(db,scenario);result=calculate_run(snapshot,3000,500,20,2026,.95)
            run=SimulationRun(name="上午双窗口 · 基准独立重复",scenario_id=scenario.id,customers=3000,warmup=500,replications=20,seed=2026,confidence=.95,input_snapshot=snapshot,status="completed",result=result,owner="季遥 · 排队分析员");db.add(run);db.flush()
            db.add(CapacityNote(run_id=run.id,title="上午窗口容量观察底稿",interpretation="已区分稳态解析和有限顾客仿真，暖机与t区间仅描述模拟均值误差。",proposal="保留到达/服务假设，追加高负荷参数试验后再讨论现场窗口配置。",status="approved",owner="季遥 · 排队分析员",reviewer="陆潮 · 运营研究负责人",review_note="批准容量研究归档；不作为现场等待承诺或自动排班指令。"))
        db.commit();print(json.dumps({m.__tablename__:db.query(m).count() for m in [User,QueueStudy,ArrivalProfile,ServiceScenario,SimulationRun,CapacityNote]},ensure_ascii=False))
if __name__=="__main__":seed()

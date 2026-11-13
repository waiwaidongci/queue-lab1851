# 栈桥窗口排队研究席 · QUEUE LAB

用Erlang-C稳态解析和独立重复FCFS仿真，分别研究匿名票证窗口的等待与容量假设。

## 业务与权限

码头服务研究所有16位运营分析员。以往用平均服务时长乘排队人数估等待，忽略系统饱和、空系统启动和随机误差。上游是到达/服务参数底稿，本应用替代排队机制研究和容量试验段，下游是运营容量讨论，不控制真实窗口或自动排班。

| 角色 | 权限 | 典型动作 |
|---|---|---|
| admin / 运营研究负责人 | 六页读写、研究备注、创建情景/运行、批准/退回 | 核对容量建议和适用边界 |
| analyst / 排队分析员 | 六页阅读、创建情景/运行、提交建议；不能审批或改研究备注 | 比较解析与有限仿真 |
| viewer / 窗口观察员 | 六页只读，仅获批完成运行可导出 | 阅读与下载研究CSV |

所有角色导出都要求对应运行完成且有获批建议。批准是研究底稿归档，不是现场等待时间或服务水平承诺。

## 快速启动

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
docker compose exec -T backend python -m scripts.seed_demo
```

[前端](http://localhost:18220)，[API文档](http://localhost:19220/docs)。Nginx去掉`/api/`前缀代理给FastAPI，直接后端接口不加该前缀。

| 邮箱 | 密码 | 角色 |
|---|---|---|
| admin@zhanqiao.demo | Zhanqiao2026! | admin |
| analyst@zhanqiao.demo | Zhanqiao2026! | analyst |
| viewer@zhanqiao.demo | Zhanqiao2026! | viewer |

恰好frontend/backend/worker/db/redis五服务，全部有健康检查与健康依赖。PostgreSQL16、Redis7分别命名卷，backend/worker共享JSON产物卷。worker按队列执行Python计算并刷新心跳。初次ORM metadata建表，迁移目录是索引示例；后续结构升级需审查迁移。

## 输入单位与种子

时间统一**分钟**。到达率λ为请求/分钟，服务输入为单台平均分钟/人，对应每台服务率`μ=1/平均服务分钟`，总容量为cμ请求/分钟。不要把每小时到达率直接输入λ，也不要把平均服务分钟当μ。

`pier-window-parameters-202611.json`为合成参数底稿：东/西栈桥两个研究，3份到达配置λ=.45/.70/1.05，6份双台/三台服务情景。上午平均服务2.5分钟，另两配置为1/.45分钟。集中时段双台情景ρ>1，故意保留用于展示“无稳态”拒绝；其余5份满足稳态条件。预置基准运行实际生成3000顾客/暖机500/20独立重复、seed2026，并有获批研究建议。

seed按邮箱、研究code、到达配置code、服务情景code、基准运行name查重，只补缺失，不覆盖已有备注。启动`SEED_DEMO=true`自动执行，失败记日志不阻断。研究备注可由admin修改；真实seed保留修改验收在外置测试目录。

## 一天剧本

1. 09:00 季遥以analyst登录，核对午后λ=.7请求/分钟、每台平均服务2.2222分钟。
2. 创建“午后双窗口复核”，c=2，检查总容量约.9请求/分钟、ρ约77.78%。
3. 创建3000顾客、前500顾客暖机、20重复、根种子2026的容量试验。
4. worker先求稳态Erlang-C，再为每次重复生成独立到达/服务随机流，按FCFS处理服务完成事件。
5. 09:05 阅读稳态平均等待3.402778分钟，与有限顾客重复均值及t区间对照。
6. 检查20次重复、首个重复中顾客#501起的事件时刻，不把同队列顾客当独立样本算区间。
7. 提交增加第三窗口、检验到达/服务分布的后续容量假设。
8. 陆潮以admin审阅，说明稳态与有限时段、暖机偏差和现场验证边界，批准或退回。
9. 沈帆以viewer下载20行重复CSV；参数快照、根种子和完整结果通过运行API/共享JSON保存。

## 两种计算的边界

**Erlang-C稳态解析**：M/M/c，Poisson到达、独立同速指数服务、无限等待空间、FCFS。必须`λ<cμ`，否则运行422拒绝，不给伪稳态指标。令a=λ/μ、ρ=a/c：

```
p0 = 1 / [sum(a^n/n!, n=0..c-1) + a^c/(c!*(1-rho))]
P(wait) = a^c/(c!*(1-rho)) * p0
Wq = P(wait)/(c*mu-lambda)
W = Wq+1/mu; Lq=lambda*Wq
```

实现用递推项避免直接大阶乘，支持1–20台、每分钟率[1e-6,1000]。服务均值API限制[.001,120]分钟，防止倒数溢出。参考[Tufts排队论课程资料](https://www.cs.tufts.edu/comp/250P/classpages/queue.html)。

**有限顾客FCFS事件仿真**：每次重复从空系统开始。到达间隔和服务时长分别由独立指数随机流生成；按到达顺序从最早服务完成时刻堆选台，`start=max(arrival,earliest completion)`，再入堆真实完成时刻，同刻按顾客序和服务台编号稳定处理。保留前面顾客对系统状态的影响，只从统计样本中剔除每次的前warmup位顾客，不重置系统或按分钟删暖机。

每次生成总顾客数N，统计N−warmup位；每个重复独立。NumPy SeedSequence(root).spawn(R)，每次再spawn到达和服务两个子流，结果记录spawn_key。事件抽样只用于展示，均值计算使用全部保留顾客。

**t区间**：以R个独立重复的平均等待`m_r`计算`mean(m) ± t_(R-1,(1+confidence)/2)*sd(m)/sqrt(R)`，不是对全部顾客算独立样本区间。使用[SciPy Student t](https://docs.scipy.org/doc/scipy-1.15.1/reference/generated/scipy.stats.t.html)分位数，默认为95%。这是重复均值近似区间，不含参数误差、模型失配或暖机偏差，不作精确有限覆盖承诺。区间未经非负截断；零重复方差明确标degenerate并提示不能证明无不确定性。

窗口忙碌率取首个保留顾客到达到全部顾客服务完成的窗口，汇总各服务区间与窗口的交集/可用服务台时间，含暖机顾客剩余工作与尾部排空。它与稳态ρ不同。有限顾客模拟均值也不必等于稳态公式；高负荷时500顾客暖机可能远远不足。

单任务500–10000顾客、暖机0–5000且保留至少100人、5–40重复、总顾客最多250000。拒绝无稳态、非法率/服务台/时长、过量任务、错误暖机。固定种子/快照支持复算；输入hash覆盖研究/到达/服务完整快照、顾客/暖机/重复/根种子/置信水平及方法版本。worker使用持久化快照，不读取后续被改动的来源备注。

## 页面与工程

六页：容量总览、输入核对、情景与运行、等待对照、建议审阅、试验留痕。QueueStudy / ArrivalProfile / ServiceScenario / SimulationRun / CapacityNote五实体贯穿模型、schema、service、route、前端API/store及页面，User/Audit为横切。

| 部分 | 技术 |
|---|---|
| 后端 | Python3.11 / FastAPI / SQLAlchemy / NumPy / SciPy |
| 前端 | React18 / TypeScript / Vite6.4.6 / Lucide |
| 数据 | PostgreSQL16 / Redis7 AOF |
| UI | 水工橘施工纸、栈桥断面线；IBM Plex Mono + Noto Sans SC |

```
backend/src/{models,schemas,services,controllers,routes,middlewares,utils,constants,config}
backend/src/{main.py,worker.py}
backend/scripts/seed_demo.py
backend/migrations/001_initial.sql
frontend/src/{api,stores,types,components,hooks,pages,router,utils,constants}
```

QueueSummary/WaitComparison在首页、结果、建议共用，ReplicationChart跨首页/结果，ProfileSelector在配置复用；DataTable/Notice/StatusBadge、useAction/useResearchData、format各自分工。角色枚举`backend/src/constants/roles.py`、运行枚举`status.py`对应`frontend/src/constants/enums.ts`，路由/worker真实使用。JWT8小时、PBKDF2-SHA256、每次数据库角色授权。审计覆盖登录、备注、情景、运行和建议审批；错误与登录限流为两个中间件。

## 配置与开发

| 变量 | 默认 | 说明 |
|---|---|---|
| COMPOSE_PROJECT_NAME | queue-lab | 命名隔离 |
| FRONTEND_PORT | 18220 | 前端 |
| BACKEND_PORT | 19220 | 后端 |
| DB_PORT | 17720 | PostgreSQL宿主映射 |
| JWT_SECRET | local-queue-lab-change-this-key | 本地演示值，部署前更换 |
| SEED_DEMO | true | 自动seed |

本地Python3.11安装requirements，设置DATABASE_URL/REDIS_URL，`cd backend && uvicorn src.main:app --reload`并另起`python -m src.worker`。前端`npm install && npm run dev`，本地为`/api`配置反向代理；标准演示以Compose为准。

```bash
docker compose down -v --remove-orphans
```

外置测试/截图/TESTING在`../../test-artifacts/gb-0016/`。源码不含日志、截图或测试报告；.env、缓存忽略提交。

## 已知差异

合成恒定参数，无真实到达轨迹导入，不实现非平稳到达、异速服务、放弃、有限排队空间或优先级。有限顾客从空系统开始并排空，默认暖机不足以证明稳态。t区间仅重复均值近似、不会解释模型偏差。单worker无running自动恢复/事务outbox/多实例锁，中断需重提；登录限流单进程。metadata首建表不是完整迁移链，字体网络不可用时回退。不执行现场排班。

## License

MIT，见LICENSE。

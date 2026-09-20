# 空气监测点数据录入系统

面向空气质量监测业务的**监测点台账 + 片区与责任人管理 + 监测数据录入 + 超标记录标注 + 数据查询**一体化系统。
后端使用 Flask + SQLAlchemy 以蓝图/服务分层组织, 前端使用 React + Vite 按业务模块拆分页面,
超标判定严格依据 **GB 3095-2012《环境空气质量标准》二级浓度限值** 自动完成。

## 功能模块

| 模块 | 路由 | 主要能力 |
| --- | --- | --- |
| 运行概览 | `/overview` | 监测点规模、数据总量、超标与待标注统计、近 7 日数据量趋势、**片区超标待办排名**、待办超标列表 |
| 片区管理 | `/zones` | 片区台账 CRUD、责任人建档与任职管理(角色/电话/部门)、点位批量归属、片区详情下钻、归属与任职变更历史 |
| 监测点台账 | `/stations` | 台账增删改查、**片区/区域/类型/状态筛选与批量归属**、点位详情(含责任人和归属时间线)、级联清理关联数据 |
| 监测数据录入 | `/measurements` | 按“监测点 + 时刻 + 周期”成组录入多因子浓度、超标校验预览、重复数据覆盖、录入结果回执、**按片区筛选/导出** |
| 超标记录标注 | `/exceedances` | 超标自动建单、单条/批量标注、**按片区/责任人过滤与片区待办排名**、标注留痕与统计 |
| 数据查询 | `/query` | 多条件组合检索、聚合统计(**按片区/因子/站点/区域/日/月等, 结果可下钻**)、分页浏览、**CSV 导出(含片区与责任人列)** |

设计要点:

- **超标自动判定**: 数据写入时即按“因子 + 数据周期”取用限值, 计算超标倍数并分级, 同步生成待标注超标记录; 修正数据后超标记录自动更新或撤销。
- **片区汇总与下钻**: 片区下挂多个监测点与多名责任人(区分片区负责人/分管领导/运维专员); 查询、超标待办、统计排名与导出均支持按片区汇总, 点击排名或统计行即可下钻到该片区的数据/待办。
- **变更全程留痕**: 监测点归属片区调整、责任人加入/移除/角色调整都会向历史流水表**追加一条快照记录**(记录当时的片区/点位/责任人名称、操作人、说明), 历史只增不改; 有历史的片区与责任人不允许删除, 只能停用/离岗。
- **业务规则集中在后端**: 限值与分级规则位于 `backend/app/domain/`, 前端仅做展示与前置校验, 避免规则分叉。
- **模块化组织**: 后端按 `api / services / models / domain / utils` 分层; 前端每个业务模块独占目录, 公共能力沉淀在 `components/`、`hooks/`、`api/`。

## 技术栈

| 层次 | 选型 |
| --- | --- |
| 后端 | Python 3.12 · Flask 3 · Flask-SQLAlchemy 3 · Flask-CORS · Gunicorn |
| 数据库 | SQLite(默认, 零依赖) / PostgreSQL 16(可选, compose 覆盖文件) |
| 前端 | React 18 · React Router 6 · Vite 7 · Axios · 原生 CSS(设计令牌 + 组件类) |
| 部署 | Docker 多阶段构建 · Nginx 静态托管与 `/api` 反向代理 · docker compose |
| 测试 | Pytest(71 个后端用例: 接口 + 领域规则 + 片区/责任人) |

## 目录结构

```text
.
├── backend/                     # Flask 后端
│   ├── app/
│   │   ├── __init__.py          # 应用工厂 create_app
│   │   ├── config.py            # 多环境配置 (development/production/testing)
│   │   ├── extensions.py        # db / cors 单例, SQLite 外键开关
│   │   ├── errors.py            # 统一异常与 JSON 错误响应
│   │   ├── commands.py          # flask init-db / seed / reset-db / stats
│   │   ├── seed.py              # 演示数据生成与启动引导
│   │   ├── domain/              # 业务规则: 因子限值、枚举、超标分级
│   │   ├── models/              # Zone / ResponsiblePerson / Station / Measurement / Exceedance + 两张历史表
│   │   ├── services/            # 台账、录入、标注、查询统计业务逻辑
│   │   ├── api/                 # 蓝图: meta / zones / stations / measurements / exceedances / query
│   │   └── utils/               # 校验器、分页、CSV 导出
│   ├── tests/                   # Pytest 用例
│   ├── Dockerfile · docker-entrypoint.sh · requirements*.txt
│   └── run.py · wsgi.py
├── frontend/                    # React 前端
│   ├── src/
│   │   ├── api/                 # 按模块拆分的接口封装 + axios 客户端
│   │   ├── components/          # layout(侧边栏/顶栏) 与 common(表格/分页/弹窗/表单等)
│   │   ├── constants/           # 路由、标签与色板映射
│   │   ├── hooks/               # useListQuery / useAsyncData / useOptions
│   │   ├── pages/               # overview / zones / stations / measurements / exceedances / query
│   │   ├── styles/global.css    # 设计令牌与公共样式
│   │   └── utils/               # 时间/数值格式化、下载
│   ├── Dockerfile · nginx.conf · vite.config.js
│   └── package.json
├── docker-compose.yml           # 默认编排(SQLite 卷)
└── docker-compose.postgres.yml  # 可选覆盖文件(PostgreSQL)
```

## 快速开始

### 方式一: Docker Compose (推荐)

```bash
docker compose up -d --build
```

启动完成后:

| 服务 | 地址 | 说明 |
| --- | --- | --- |
| 前端 | http://localhost:8080 | Nginx 托管, `/api` 反向代理到后端 |
| 后端 | http://localhost:5000/api/meta/health | 健康检查 |

首次启动会自动建表并写入演示数据(3 个片区 / 5 名责任人 / 8 个监测点 / 1200 条监测数据 / 52 条超标记录), 可通过环境变量 `SEED_DEMO=false` 关闭。

```bash
docker compose ps          # 查看容器与健康状态
docker compose logs -f backend
docker compose down        # 停止(保留数据卷)
docker compose down -v     # 停止并删除数据卷
```

### 方式二: 本地开发

后端(默认使用 SQLite, 无需额外依赖):

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
python -m flask --app wsgi init-db      # 建表
python -m flask --app wsgi seed         # 可选: 写入演示数据
python run.py                           # http://127.0.0.1:5000
```

前端(Vite 开发服务器会把 `/api` 代理到 `http://127.0.0.1:5000`):

```bash
cd frontend
npm install
npm run dev                             # http://127.0.0.1:5173
```

> 若后端不在默认地址, 通过 `VITE_PROXY_TARGET=http://host:port npm run dev` 指定, 或复制 `.env.example` 为 `.env` 后修改。

### 方式三: 使用 PostgreSQL

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d --build
```

覆盖文件会新增 `postgres:16-alpine` 服务并把后端 `DATABASE_URL` 指向它; 后端容器会等待数据库健康检查通过后再建表初始化。

## 超标判定规则

判定逻辑位于 `backend/app/domain/exceedance_rules.py`, 限值定义位于 `backend/app/domain/standards.py`。

**GB 3095-2012 二级浓度限值**

| 监测因子 | 1 小时平均 | 24 小时平均 | 单位 |
| --- | --- | --- | --- |
| PM2.5 | 不设限值(仅记录) | 75 | μg/m³ |
| PM10 | 不设限值(仅记录) | 150 | μg/m³ |
| SO₂ | 500 | 150 | μg/m³ |
| NO₂ | 200 | 80 | μg/m³ |
| CO | 10 | 4 | mg/m³ |
| O₃ | 200 | 160 | μg/m³ |

- **判定**: `监测值 > 限值` 即判为超标, 记录限值快照与原值, 避免限值调整后历史数据失真。
- **分级**: 超标倍数 = 监测值 / 限值; `1.0 ~ 1.5 倍` 为轻度超标, `1.5 ~ 2.0 倍` 为中度超标, `≥ 2.0 倍` 为重度超标。
- **无 1 小时限值的因子**(PM2.5、PM10 小时值)仅记录数值, 不参与超标判定, 避免误报。
- **标注状态**: `待标注(pending)` 由系统自动创建, 人工标注为 `已确认(confirmed)` 或 `已忽略(ignored)`; 确认与忽略都必须填写标注说明, 用于后续追溯。

## API 概览

统一前缀 `/api`, 成功直接返回数据对象; 失败返回 `{"error": {"code": "...", "message": "...", "fields": {...}}}`。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/meta/health` | 健康检查(数据库连通性、时区、限值标准) |
| GET | `/api/meta/pollutants` | 监测因子清单与限值 |
| GET | `/api/meta/options` | 枚举选项(监测点、行政区域、**片区、责任人**、状态、类型等) |
| GET | `/api/meta/overview` | 首页概览聚合数据(含**片区超标待办排名**) |
| GET/POST | `/api/zones` | 片区分页查询(含点位数/数据量/超标/待办/责任人统计) / 新增 |
| GET/PUT/DELETE | `/api/zones/{id}` | 片区详情(责任人、点位、两类变更历史) / 更新 / 删除(有历史时拒绝) |
| GET | `/api/zones/options` | 片区下拉选项 |
| POST | `/api/zones/{id}/managers` | 为片区分配责任人(写任职历史) |
| PUT/DELETE | `/api/zones/{id}/managers/{personId}` | 调整责任人角色 / 移除责任人(均写任职历史) |
| POST | `/api/zones/assign-stations` | **批量调整点位归属片区**(逐点写归属历史, `zone_id=null` 表示移出) |
| GET | `/api/stations/{id}/zone-history` | 监测点归属片区变更流水 |
| GET/POST | `/api/persons` | 责任人分页查询(可按姓名/工号/部门/片区过滤) / 新增 |
| GET/PUT/DELETE | `/api/persons/{id}` | 责任人详情(含任职片区) / 更新 / 删除(有历史时拒绝) |
| GET | `/api/persons/options` | 在岗责任人下拉选项 |
| GET/POST | `/api/stations` | 台账分页查询(**支持 `zone_id` 过滤, `zone_id=none` 表示未划分**) / 新增 |
| GET/PUT/DELETE | `/api/stations/{id}` | 台账详情(含分因子统计、**责任人、归属历史**) / 更新 / 删除(级联) |
| GET | `/api/stations/options` | 下拉选项(监测点、行政区域、片区) |
| GET | `/api/stations/summary` | 台账规模统计(含片区覆盖情况) |
| GET | `/api/measurements` | 监测数据分页查询(含筛选汇总, 支持片区过滤) |
| POST | `/api/measurements/entries` | **成组录入**: 一个监测点 + 一个时刻 + 多个因子 |
| POST | `/api/measurements/preview` | 超标校验预览(不写库) |
| DELETE | `/api/measurements/{id}` | 删除监测数据 |
| GET | `/api/measurements/export` | 按条件导出 CSV(含所属片区、片区责任人列) |
| GET | `/api/exceedances` | 超标记录查询(**支持片区 `zone_id`、责任人 `manager_id` 过滤**) |
| GET | `/api/exceedances/{id}` | 超标记录详情(含关联监测数据) |
| PATCH | `/api/exceedances/{id}` | 单条标注 |
| POST | `/api/exceedances/annotations` | 批量标注 |
| GET | `/api/exceedances/summary` | 超标统计(状态/等级/高发因子/站点排名/**片区待办排名**) |
| GET | `/api/query/measurements` | 高级条件检索(支持片区过滤, 行数据携带责任人) |
| GET | `/api/query/statistics` | 聚合统计(`group_by=zone` 按片区, 结果含 zone_id 供下钻) |
| GET | `/api/query/export` | 查询结果导出 CSV(含所属片区、片区责任人列) |

`POST /api/measurements/entries` 请求示例:

```json
{
  "station_id": 1,
  "measured_at": "2026-09-14 10:00",
  "period": "hourly",
  "data_source": "manual",
  "recorder": "王敏",
  "remark": "在线设备人工比对",
  "overwrite": false,
  "entries": [
    { "pollutant": "PM25", "value": 82.5 },
    { "pollutant": "SO2", "value": 640 },
    { "pollutant": "CO", "value": 1.4 }
  ]
}
```

响应会返回本次新增/更新条数、超标记录、重复项与逐因子判定结果:

```json
{
  "created": [ "..." ],
  "updated": [],
  "exceedances": [ { "pollutant": "SO2", "level": "moderate", "exceed_ratio": 1.28 } ],
  "duplicates": [],
  "summary": { "created_count": 3, "updated_count": 0, "exceeded_count": 1, "duplicate_count": 0 }
}
```

## 数据模型

| 表 | 关键字段 | 说明 |
| --- | --- | --- |
| `zones` | `code`(唯一) `name` `description` `status` | 监测点片区(启用/停用) |
| `responsible_persons` | `name` `employee_no`(唯一) `phone` `department` `title` `status` | 责任人独立台账(在岗/离岗) |
| `zone_managers` | `zone_id` `person_id`(联合唯一) `role` `assigned_at` | 片区-责任人多对多, 角色为负责人/分管领导/运维专员 |
| `station_zone_histories` | `station_id` `zone_id` `previous_zone_id` `reason` `operator` `note` + 名称快照 | 点位归属变更流水, 只追加不修改 |
| `zone_manager_histories` | `zone_id` `person_id` `change_type` `role` `previous_role` `operator` + 名称快照 | 责任人任职变动流水(加入/移除/角色调整), 只追加 |
| `stations` | `code`(唯一) `name` `area`(行政区域) **`zone_id`(所属片区, 可空)** `station_type` `status` `longitude/latitude` `installed_at` | 监测点台账 |
| `measurements` | `station_id` `pollutant` `period` `value` `limit_value` `exceed_ratio` `is_exceeded` `measured_at` `data_source` `recorder` | 监测数据; `(station_id, pollutant, period, measured_at)` 唯一 |
| `exceedances` | `measurement_id`(唯一) `status` `level` `note` `annotator` `annotated_at` | 超标记录与人工标注 |

- **当前归属**通过 `stations.zone_id` 与 `zone_managers` 关联获得; **历史归属**全部保留在两张历史表中, 名称字段做快照, 片区/责任人改名或停用后历史仍可正常展示。
- 已有数据库升级时, 启动引导会幂等地补齐新表并为旧 `stations` 表 `ADD COLUMN zone_id`(见 `backend/app/migrations.py`), 无需手工迁移。
- 删除监测点会级联清理其监测数据与超标记录(其归属历史同时级联删除); 删除监测数据会同时删除对应超标记录。片区/责任人一旦有点位或历史关联则禁止删除(只能停用/离岗), 以保证追溯链条完整。

## 配置项

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `FLASK_ENV` | `development` | `development` / `production` / `testing` |
| `DATABASE_URL` | SQLite(`backend/instance/air_monitor.db`) | 如 `postgresql+psycopg2://user:pass@host:5432/db` |
| `CORS_ORIGINS` | `*` | 允许的前端来源, 逗号分隔 |
| `TIMEZONE` | `Asia/Shanghai` | 展示时区 |
| `AUTO_INIT_DB` / `AUTO_SEED` | `true`(开发) | 启动时自动建表 / 写入演示数据 |
| `SEED_DEMO` | `true` | Docker 容器启动时是否写入演示数据 |
| `GUNICORN_WORKERS` | `2` | 生产容器 worker 数量 |
| `VITE_API_BASE` | `/api` | 前端接口前缀 |
| `VITE_PROXY_TARGET` | `http://127.0.0.1:5000` | 开发代理的后端地址 |

## 测试与校验

```bash
cd backend
python -m pytest -q          # 71 个用例: 台账 CRUD/级联、片区/责任人/历史留痕、录入与超标判定、标注规则、查询统计与导出、元数据接口、旧库升级

cd frontend
npm run build                # 生产构建校验
```

健康检查与常用命令:

```bash
curl http://localhost:5000/api/meta/health
python -m flask --app wsgi stats      # 查看监测点/数据/超标记录数量
python -m flask --app wsgi reset-db   # 重置数据库并重建演示数据
```

## 常见问题

- **端口被占用**: 后端改 `PORT=5001 python run.py`(同时调整 `VITE_PROXY_TARGET`), 或修改 compose 的端口映射。
- **想清空演示数据**: `python -m flask --app wsgi reset-db --empty`, 或 `docker compose down -v` 后重新启动。
- **SQLite 文件位置**: 本地开发为 `backend/instance/air_monitor.db`; Docker 部署为数据卷 `air-monitor-data` 中的 `/data/air_monitor.db`。
- **前端页面 404 / 刷新报错**: Nginx 已配置 SPA 回退(`try_files ... /index.html`), 自定义部署时需保留该配置。
- **时区**: 系统按“本地墙钟时间”存储与展示监测时间, 部署时请保持后端 `TIMEZONE` 与业务所在地一致。

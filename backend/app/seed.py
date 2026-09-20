"""演示数据生成与启动引导."""
import random
from datetime import date, datetime, timedelta

from .extensions import db
from .models import Area, AreaMembership, Exceedance, Measurement, Person, Station, StationAssignment

# 片区划分 (片区 -> 该片区下的监测点编码), 支持一个片区挂多个点位
DEMO_AREAS = [
    {
        "code": "GRID-CITY", "name": "中心城区片区", "manager": "周建华", "phone": "0755-88001",
        "station_codes": ["SZ-AQ-001", "SZ-AQ-003", "SZ-AQ-006"],
        "persons": [("李静", "EMP-101", "leader"), ("王敏", "EMP-102", "officer")],
    },
    {
        "code": "GRID-WEST", "name": "西部高新片区", "manager": "吴凯", "phone": "0755-88002",
        "station_codes": ["SZ-AQ-002", "SZ-AQ-008"],
        "persons": [("陈志强", "EMP-201", "leader"), ("赵宇", "EMP-202", "inspector")],
    },
    {
        "code": "GRID-NORTH", "name": "北部产业片区", "manager": "郑琳", "phone": "0755-88003",
        "station_codes": ["SZ-AQ-004", "SZ-AQ-005", "SZ-AQ-007"],
        "persons": [("孙倩", "EMP-301", "leader"), ("王敏", "EMP-102", "officer")],
    },
]

# 演示一次历史划转: 前海自贸区站(SZ-AQ-008) 2 天前从中心城区片区划到西部高新片区
# (演示数据默认覆盖近 5 天, 划转前后两侧都有数据, 可直观对比历史片区归属)
DEMO_TRANSFERS = {
    "SZ-AQ-008": {"from_area": "GRID-CITY", "days_ago": 2, "reason": "自贸区管理职能调整, 点位移交西部片区"},
}

# 演示一次责任人变动: 赵宇 3 天前才到西部高新片区任职
DEMO_MEMBERSHIP_CHANGES = [
    {"employee_no": "EMP-202", "area_code": "GRID-WEST", "days_ago": 3,
     "previous_area": "GRID-NORTH", "role": "inspector",
     "reason": "岗位轮岗, 调整至西部高新片区任督查员"},
]

DEMO_STATIONS = [
    {
        "code": "SZ-AQ-001", "name": "市民中心站", "area": "福田区",
        "address": "福田区福中三路市民中心广场", "station_type": "ambient",
        "status": "active", "longitude": 114.0579, "latitude": 22.5410,
        "installed_at": date(2019, 5, 12), "remark": "城市环境评价点",
    },
    {
        "code": "SZ-AQ-002", "name": "华侨城站", "area": "南山区",
        "address": "南山区华侨城生态广场", "station_type": "ambient",
        "status": "active", "longitude": 113.9711, "latitude": 22.5356,
        "installed_at": date(2020, 3, 1), "remark": "城市环境评价点",
    },
    {
        "code": "SZ-AQ-003", "name": "罗湖口岸站", "area": "罗湖区",
        "address": "罗湖区火车站东广场", "station_type": "traffic",
        "status": "active", "longitude": 114.1276, "latitude": 22.5329,
        "installed_at": date(2018, 11, 20), "remark": "道路交通监测点, 早晚高峰浓度偏高",
    },
    {
        "code": "SZ-AQ-004", "name": "宝安中心站", "area": "宝安区",
        "address": "宝安区中心区宝安大道", "station_type": "ambient",
        "status": "active", "longitude": 113.8830, "latitude": 22.5551,
        "installed_at": date(2021, 6, 18), "remark": None,
    },
    {
        "code": "SZ-AQ-005", "name": "龙岗工业园站", "area": "龙岗区",
        "address": "龙岗区宝龙工业区龙岗大道", "station_type": "industrial",
        "status": "active", "longitude": 114.2465, "latitude": 22.7204,
        "installed_at": date(2019, 9, 8), "remark": "周边为工业排放源, 需重点关注 SO₂",
    },
    {
        "code": "SZ-AQ-006", "name": "梧桐山背景站", "area": "罗湖区",
        "address": "罗湖区梧桐山风景区", "station_type": "background",
        "status": "active", "longitude": 114.1837, "latitude": 22.5862,
        "installed_at": date(2017, 4, 2), "remark": "区域背景点, 用于对照评价",
    },
    {
        "code": "SZ-AQ-007", "name": "大鹏生态站", "area": "大鹏新区",
        "address": "大鹏新区葵涌街道", "station_type": "rural",
        "status": "maintenance", "longitude": 114.4798, "latitude": 22.5964,
        "installed_at": date(2022, 8, 15), "remark": "设备检修中, 计划本周恢复",
    },
    {
        "code": "SZ-AQ-008", "name": "前海自贸区站", "area": "南山区",
        "address": "南山区前海湾保税港区", "station_type": "ambient",
        "status": "offline", "longitude": 113.8980, "latitude": 22.5253,
        "installed_at": date(2023, 1, 10), "remark": "站点搬迁停用",
    },
]

POLLUTANT_BASE = {"PM25": 45.0, "PM10": 80.0, "SO2": 30.0, "NO2": 45.0, "CO": 1.5, "O3": 120.0}
HOURLY_FACTOR = {"PM25": 1.0, "PM10": 1.05, "SO2": 0.8, "NO2": 1.1, "CO": 0.9, "O3": 1.3}
STATION_FACTOR = {
    "ambient": 1.0, "traffic": 1.2, "industrial": 1.35, "background": 0.55, "rural": 0.75,
}
HOURLY_POINTS = (2, 8, 14, 20)
RECORDERS = ("李静", "王敏", "陈志强", "赵宇", "孙倩")


def _value(pollutant, period, station_type, rng):
    base = POLLUTANT_BASE[pollutant] * STATION_FACTOR.get(station_type, 1.0)
    if period == "hourly":
        base *= HOURLY_FACTOR[pollutant]
    value = base * rng.uniform(0.72, 1.22)
    if rng.random() < 0.12:  # 少量明显超标样本, 便于演示超标标注
        value *= rng.uniform(1.8, 2.6)
    return round(value, 2 if pollutant == "CO" else 1)


def seed_demo_data(days=5, rng=None, recorder_pool=RECORDERS):
    """Generate demo stations, areas, persons and monitoring records."""
    from .services import measurement_service

    rng = rng or random.Random(20260914)
    now = datetime.now()
    today = date.today()

    # 1) 片区
    area_map = {}
    for spec in DEMO_AREAS:
        area = Area(
            code=spec["code"], name=spec["name"], manager=spec["manager"],
            phone=spec["phone"], status="active", remark="演示片区",
        )
        db.session.add(area)
        area_map[spec["code"]] = area
    db.session.flush()

    # 2) 责任人 (同一人可能服务多个片区, 如王敏)
    person_specs = {}
    for spec in DEMO_AREAS:
        for name, employee_no, role in spec["persons"]:
            person_specs.setdefault(employee_no, {"name": name, "areas": []})
            person_specs[employee_no]["areas"].append((spec["code"], role))
    person_map = {}
    for employee_no, info in person_specs.items():
        person = Person(
            name=info["name"], employee_no=employee_no,
            department="环境监测中心", role=info["areas"][0][1],
            status="active",
        )
        db.session.add(person)
        person_map[employee_no] = (person, info["areas"])
    db.session.flush()

    # 3) 任职关系 (时间分段): 默认从一年前任职, 个别责任人按演示变动处理
    member_change_index = {item["employee_no"]: item for item in DEMO_MEMBERSHIP_CHANGES}
    for employee_no, (person, areas) in person_map.items():
        change = member_change_index.get(employee_no)
        if change:
            started_at = now - timedelta(days=change["days_ago"])
            for area_code, role in areas:
                if area_code == change["area_code"]:
                    db.session.add(AreaMembership(
                        area_id=area_map[area_code].id, person_id=person.id, role=role,
                        effective_from=started_at, effective_end=None,
                        change_reason=change["reason"], changed_by="系统管理员",
                    ))
                elif area_code == change["previous_area"]:
                    db.session.add(AreaMembership(
                        area_id=area_map[area_code].id, person_id=person.id, role=role,
                        effective_from=now - timedelta(days=400), effective_end=started_at,
                        change_reason=change["reason"], changed_by="系统管理员",
                    ))
        else:
            for area_code, role in areas:
                db.session.add(AreaMembership(
                    area_id=area_map[area_code].id, person_id=person.id, role=role,
                    effective_from=now - timedelta(days=400), effective_end=None,
                ))

    # 4) 监测点
    code_to_area = {}
    for spec in DEMO_AREAS:
        for station_code in spec["station_codes"]:
            code_to_area[station_code] = spec["code"]

    created_stations = []
    for item in DEMO_STATIONS:
        station = Station(**item)
        station.area_id = area_map[code_to_area[item["code"]]].id
        db.session.add(station)
        created_stations.append(station)
    db.session.flush()

    # 5) 归属历史: 划转点先在旧片区放一段, 再划到新片区; 其余从 400 天前起算
    station_by_code = {station.code: station for station in created_stations}
    for station_code, transfer in DEMO_TRANSFERS.items():
        station = station_by_code[station_code]
        moved_at = now - timedelta(days=transfer["days_ago"])
        db.session.add(StationAssignment(
            station_id=station.id, area_id=area_map[transfer["from_area"]].id,
            effective_from=now - timedelta(days=400), effective_end=moved_at,
            change_reason=transfer["reason"], changed_by="系统管理员",
        ))
        db.session.add(StationAssignment(
            station_id=station.id, area_id=station.area_id,
            effective_from=moved_at, effective_end=None,
            change_reason=transfer["reason"], changed_by="系统管理员",
        ))
    for station in created_stations:
        if station.code in DEMO_TRANSFERS:
            continue
        db.session.add(StationAssignment(
            station_id=station.id, area_id=station.area_id,
            effective_from=now - timedelta(days=400), effective_end=None,
        ))
    db.session.commit()

    totals = {"stations": len(created_stations), "areas": len(area_map),
              "persons": len(person_map), "measurements": 0, "exceedances": 0}
    for station in created_stations:
        for offset in range(days):
            day = today - timedelta(days=offset)
            daily_entries = [
                {"pollutant": code, "value": _value(code, "daily", station.station_type, rng)}
                for code in POLLUTANT_BASE
            ]
            result = measurement_service.record_entries(
                station_id=station.id,
                measured_at=datetime(day.year, day.month, day.day, 0, 0),
                period="daily",
                entries=daily_entries,
                data_source="device",
                recorder=rng.choice(recorder_pool),
                remark="日均值自动汇总",
            )
            totals["measurements"] += result["summary"]["created_count"]
            totals["exceedances"] += result["summary"]["exceeded_count"]

            for hour in HOURLY_POINTS:
                hourly_entries = [
                    {"pollutant": code, "value": _value(code, "hourly", station.station_type, rng)}
                    for code in HOURLY_FACTOR
                ]
                result = measurement_service.record_entries(
                    station_id=station.id,
                    measured_at=datetime(day.year, day.month, day.day, hour, 0),
                    period="hourly",
                    entries=hourly_entries,
                    data_source="manual",
                    recorder=rng.choice(recorder_pool),
                )
                totals["measurements"] += result["summary"]["created_count"]
                totals["exceedances"] += result["summary"]["exceeded_count"]

    # 标注一部分超标记录, 让工作台同时存在待办与已处理记录
    from .services import exceedance_service

    exceedances = Exceedance.query.order_by(Exceedance.id.asc()).all()
    annotated = 0
    for index, record in enumerate(exceedances):
        if index % 3 == 0:
            continue
        if index % 3 == 1:
            exceedance_service.annotate(
                record, status="confirmed", note="数据经复核属实, 已通知运维排查周边排放源",
                annotator=rng.choice(recorder_pool),
            )
        else:
            exceedance_service.annotate(
                record, status="ignored", note="仪器校准期间异常值, 已在原始数据中标记无效",
                annotator=rng.choice(recorder_pool),
            )
        annotated += 1
    totals["annotated"] = annotated
    return totals


def reset_database():
    db.drop_all()
    db.create_all()


def ensure_schema_compat(db):
    """轻量级结构升级 (项目未使用 Alembic): 为老库补建新增表与新增列。

    ``db.create_all()`` 只会创建缺失的表, 不会给已存在的表加列, 因此这里显式
    检查并补齐 ``stations.area_id``。新库不受影响。
    """
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()

    if "stations" in table_names:
        columns = {column["name"] for column in inspector.get_columns("stations")}
        if "area_id" not in columns:
            db.session.execute(text("ALTER TABLE stations ADD COLUMN area_id INTEGER"))
            db.session.commit()
    return table_names


def backfill_after_migrate(app):
    """结构升级 + 老数据片区归属回填。"""
    from .services import area_service

    ensure_schema_compat(db)
    backfilled = area_service.backfill_station_areas()
    return backfilled


def ensure_bootstrap(app):
    """Create tables / seed demo data at startup when enabled by config."""
    auto_init = app.config.get("AUTO_INIT_DB")
    auto_seed = app.config.get("AUTO_SEED")
    if not auto_init and not auto_seed:
        return
    with app.app_context():
        try:
            if auto_init:
                db.create_all()
                # 老库可能已有 stations 但缺少片区相关表/字段, 启动时幂等升级并回填
                from .services import area_service

                ensure_schema_compat(db)
                backfilled = area_service.backfill_station_areas()
                if backfilled:
                    app.logger.info("backfilled area assignments for %s stations", backfilled)
            if auto_seed and db.session.query(Station.id).first() is None:
                app.logger.info("seeding demo data ...")
                seed_demo_data()
        except Exception as exc:  # pragma: no cover - depends on external database
            app.logger.warning("bootstrap skipped: %s", exc)

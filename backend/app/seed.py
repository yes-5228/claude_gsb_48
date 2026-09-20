"""演示数据生成与启动引导."""
import random
from datetime import date, datetime, timedelta

from .extensions import db
from .models import Exceedance, Measurement, ResponsiblePerson, Station, Zone

# (片区编码, 片区名称, 说明, [(责任人姓名, 工号, 角色, 电话, 部门)])
DEMO_ZONES = [
    (
        "ZN-CENTER", "中心城区片区", "覆盖福田、罗湖核心城区监测点",
        [
            ("张伟", "EMP1001", "manager", "13800001001", "监测中心运维一部"),
            ("李娜", "EMP1002", "supervisor", "13800001002", "市生态环境局"),
        ],
    ),
    (
        "ZN-WEST", "西部沿海片区", "覆盖南山、宝安沿海区域",
        [
            ("王强", "EMP1003", "manager", "13800001003", "监测中心运维二部"),
            ("陈晨", "EMP1004", "engineer", "13800001004", "监测中心运维二部"),
        ],
    ),
    (
        "ZN-EAST", "东部产业片区", "覆盖龙岗、大鹏等产业与生态区域",
        [
            ("刘洋", "EMP1005", "manager", "13800001005", "监测中心运维三部"),
        ],
    ),
]

# 站点编码 -> (片区编码); 未列出的站点默认不划分片区, 便于演示“未划分”筛选
STATION_ZONE_MAP = {
    "SZ-AQ-001": "ZN-CENTER",
    "SZ-AQ-003": "ZN-CENTER",
    "SZ-AQ-006": "ZN-CENTER",
    "SZ-AQ-002": "ZN-WEST",
    "SZ-AQ-008": "ZN-WEST",
    "SZ-AQ-005": "ZN-EAST",
    "SZ-AQ-007": "ZN-EAST",
}

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
    """Generate demo stations and monitoring records through the normal service path."""
    from .services import measurement_service, zone_service

    rng = rng or random.Random(20260914)
    created_stations = []
    for item in DEMO_STATIONS:
        station = Station(**item)
        db.session.add(station)
        created_stations.append(station)
    db.session.commit()

    # 建立片区、责任人与任职关系
    created_zones = {}
    for code, name, description, persons in DEMO_ZONES:
        zone = Zone(code=code, name=name, description=description, status="active")
        db.session.add(zone)
        db.session.commit()
        created_zones[code] = zone
        for person_name, employee_no, role, phone, department in persons:
            person = ResponsiblePerson(
                name=person_name,
                employee_no=employee_no,
                phone=phone,
                department=department,
                title="片区责任人" if role == "manager" else "分管领导"
                if role == "supervisor" else "运维专员",
                status="active",
            )
            db.session.add(person)
            db.session.commit()
            zone_service.add_zone_manager(
                zone, person.id, role, operator="系统初始化", note="片区建立时分配"
            )

    # 点位归属片区(走服务层以写入归属历史)
    zone_by_code = {zone.code: zone for zone in created_zones.values()}
    for station in created_stations:
        zone_code = STATION_ZONE_MAP.get(station.code)
        if zone_code:
            zone_service.assign_station_zone(
                station, zone_by_code[zone_code].id,
                operator="系统初始化", note="片区台账初始化分配",
            )
    # 模拟一次历史调整: 宝安中心站最初归属中心城区, 后调整到西部沿海
    baoan = next((item for item in created_stations if item.code == "SZ-AQ-004"), None)
    if baoan is not None:
        center = created_zones.get("ZN-CENTER")
        west = created_zones.get("ZN-WEST")
        zone_service.assign_station_zone(
            baoan, center.id, operator="系统初始化", note="建点时临时挂靠中心城区"
        )
        zone_service.assign_station_zone(
            baoan, west.id, operator="李娜", note="按行政片区重新划分, 调整至西部沿海片区"
        )

    today = date.today()
    totals = {"stations": len(created_stations), "measurements": 0, "exceedances": 0}
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


def ensure_bootstrap(app):
    """Create tables / seed demo data at startup when enabled by config."""
    auto_init = app.config.get("AUTO_INIT_DB")
    auto_seed = app.config.get("AUTO_SEED")
    if not auto_init and not auto_seed:
        return
    with app.app_context():
        try:
            from .migrations import ensure_schema

            if auto_init:
                ensure_schema()
            if auto_seed and db.session.query(Station.id).first() is None:
                app.logger.info("seeding demo data ...")
                seed_demo_data()
        except Exception as exc:  # pragma: no cover - depends on external database
            app.logger.warning("bootstrap skipped: %s", exc)

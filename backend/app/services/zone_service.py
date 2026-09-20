"""片区与责任人业务逻辑.

- 片区 / 责任人台账 CRUD
- 片区责任人任职关系维护(含历史流水)
- 监测点归属片区调整(含历史流水)
- 面向列表 / 导出 / 统计的责任人与片区聚合
"""
from datetime import datetime

from sqlalchemy import case, func, or_

from ..domain.constants import (
    CHANGE_REASON_LABELS,
    PERSON_STATUS_LABELS,
    ZONE_ROLE_LABELS,
    ZONE_STATUS_LABELS,
)
from ..errors import ConflictError, NotFoundError, ValidationError
from ..extensions import db
from ..models import (
    Exceedance,
    Measurement,
    ResponsiblePerson,
    Station,
    StationZoneHistory,
    Zone,
    ZoneManager,
    ZoneManagerHistory,
)

ROLE_CHOICES = tuple(ZONE_ROLE_LABELS.keys())
CHANGE_REASON_CHOICES = tuple(CHANGE_REASON_LABELS.keys())


def _split(value):
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


# ---------------------------------------------------------------------------
# 片区台账
# ---------------------------------------------------------------------------

def get_zone(zone_id):
    zone = db.session.get(Zone, zone_id)
    if zone is None:
        raise NotFoundError("片区不存在: id=%s" % zone_id)
    return zone


def zone_query(args):
    query = Zone.query
    keyword = (args.get("keyword") or "").strip()
    if keyword:
        like = "%" + keyword + "%"
        query = query.filter(or_(Zone.name.like(like), Zone.code.like(like)))
    statuses = _split(args.get("status"))
    if statuses:
        query = query.filter(Zone.status.in_(statuses))
    sort_field = {"code": Zone.code, "name": Zone.name, "created_at": Zone.created_at}.get(
        args.get("sort"), Zone.code
    )
    direction = sort_field.desc() if (args.get("order") or "asc") == "desc" else sort_field.asc()
    return query.order_by(direction)


def create_zone(data):
    code = data["code"]
    if Zone.query.filter(func.lower(Zone.code) == code.lower()).first():
        raise ConflictError("片区编码 %s 已存在" % code)
    zone = Zone(**data)
    db.session.add(zone)
    db.session.commit()
    return zone


def update_zone(zone, data):
    code = data.get("code")
    if code and code.lower() != zone.code.lower():
        exists = Zone.query.filter(func.lower(Zone.code) == code.lower()).first()
        if exists and exists.id != zone.id:
            raise ConflictError("片区编码 %s 已存在" % code)
    for field, value in data.items():
        setattr(zone, field, value)
    db.session.commit()
    return zone


def delete_zone(zone):
    """仅允许删除从未使用过的片区; 有点位或存在归属历史时拒绝以保留追溯链条."""
    station_count = Station.query.filter_by(zone_id=zone.id).count()
    if station_count:
        raise ConflictError("片区下仍有 %d 个监测点, 请先调整点位归属后再删除" % station_count)
    history_count = StationZoneHistory.query.filter(
        or_(
            StationZoneHistory.zone_id == zone.id,
            StationZoneHistory.previous_zone_id == zone.id,
        )
    ).count()
    if history_count:
        raise ConflictError("该片区存在点位归属历史记录, 为保留追溯信息不允许删除, 可将其停用")
    db.session.delete(zone)
    db.session.commit()
    return {"id": zone.id, "deleted": True}


def zone_stats(zone_ids):
    """片区维度的点位 / 数据 / 超标 / 待办计数."""
    if not zone_ids:
        return {}
    station_counts = dict(
        db.session.query(Station.zone_id, func.count(Station.id))
        .filter(Station.zone_id.in_(zone_ids))
        .group_by(Station.zone_id)
        .all()
    )
    measurement_counts = dict(
        db.session.query(Station.zone_id, func.count(Measurement.id))
        .join(Measurement, Measurement.station_id == Station.id)
        .filter(Station.zone_id.in_(zone_ids))
        .group_by(Station.zone_id)
        .all()
    )
    exceeded_counts = dict(
        db.session.query(Station.zone_id, func.count(Measurement.id))
        .join(Measurement, Measurement.station_id == Station.id)
        .filter(Station.zone_id.in_(zone_ids), Measurement.is_exceeded.is_(True))
        .group_by(Station.zone_id)
        .all()
    )
    pending_counts = dict(
        db.session.query(Station.zone_id, func.count(Exceedance.id))
        .join(Exceedance, Exceedance.station_id == Station.id)
        .filter(Station.zone_id.in_(zone_ids), Exceedance.status == "pending")
        .group_by(Station.zone_id)
        .all()
    )
    manager_map = manager_names_by_zone(zone_ids)
    return {
        zone_id: {
            "station_count": int(station_counts.get(zone_id, 0)),
            "measurement_count": int(measurement_counts.get(zone_id, 0)),
            "exceeded_count": int(exceeded_counts.get(zone_id, 0)),
            "pending_count": int(pending_counts.get(zone_id, 0)),
            "managers": manager_map.get(zone_id, []),
        }
        for zone_id in zone_ids
    }


def zone_detail(zone):
    stations = Station.query.filter_by(zone_id=zone.id).order_by(Station.code.asc()).all()
    from . import station_service

    per_station = station_service.stats_map([item.id for item in stations])
    station_items = []
    for station in stations:
        item = station.to_dict()
        item["stats"] = per_station.get(station.id, {})
        station_items.append(item)
    aggregate = zone_stats([zone.id]).get(zone.id, {})
    return {
        "zone": zone.to_dict(include_managers=True),
        "stations": station_items,
        "stats": aggregate,
        "station_history": [
            item.to_dict()
            for item in StationZoneHistory.query.filter_by(zone_id=zone.id)
            .order_by(StationZoneHistory.changed_at.desc(), StationZoneHistory.id.desc())
            .all()
        ],
        "manager_history": [
            item.to_dict()
            for item in ZoneManagerHistory.query.filter_by(zone_id=zone.id)
            .order_by(ZoneManagerHistory.changed_at.desc(), ZoneManagerHistory.id.desc())
            .all()
        ],
    }


def zone_option_list(include_inactive=False):
    query = Zone.query
    if not include_inactive:
        query = query.filter(Zone.status == "active")
    zones = query.order_by(Zone.code.asc()).all()
    return [zone.to_option() for zone in zones]


def unassigned_station_count():
    return Station.query.filter(Station.zone_id.is_(None)).count()


# ---------------------------------------------------------------------------
# 责任人台账
# ---------------------------------------------------------------------------

def get_person(person_id):
    person = db.session.get(ResponsiblePerson, person_id)
    if person is None:
        raise NotFoundError("责任人不存在: id=%s" % person_id)
    return person


def person_query(args):
    query = ResponsiblePerson.query
    keyword = (args.get("keyword") or "").strip()
    if keyword:
        like = "%" + keyword + "%"
        query = query.filter(
            or_(
                ResponsiblePerson.name.like(like),
                ResponsiblePerson.employee_no.like(like),
                ResponsiblePerson.department.like(like),
                ResponsiblePerson.phone.like(like),
            )
        )
    statuses = _split(args.get("status"))
    if statuses:
        query = query.filter(ResponsiblePerson.status.in_(statuses))
    zone_ids = [int(item) for item in _split(args.get("zone_id")) if item.isdigit()]
    if zone_ids:
        query = query.join(ZoneManager, ZoneManager.person_id == ResponsiblePerson.id).filter(
            ZoneManager.zone_id.in_(zone_ids)
        )
    sort_field = {
        "name": ResponsiblePerson.name,
        "created_at": ResponsiblePerson.created_at,
    }.get(args.get("sort"), ResponsiblePerson.id)
    direction = sort_field.desc() if (args.get("order") or "asc") == "desc" else sort_field.asc()
    return query.order_by(direction)


def create_person(data):
    employee_no = data.get("employee_no")
    if employee_no and ResponsiblePerson.query.filter(
        func.lower(ResponsiblePerson.employee_no) == employee_no.lower()
    ).first():
        raise ConflictError("工号 %s 已存在" % employee_no)
    person = ResponsiblePerson(**data)
    db.session.add(person)
    db.session.commit()
    return person


def update_person(person, data):
    employee_no = data.get("employee_no")
    if employee_no and employee_no.lower() != (person.employee_no or "").lower():
        exists = ResponsiblePerson.query.filter(
            func.lower(ResponsiblePerson.employee_no) == employee_no.lower()
        ).first()
        if exists and exists.id != person.id:
            raise ConflictError("工号 %s 已存在" % employee_no)
    for field, value in data.items():
        setattr(person, field, value)
    db.session.commit()
    return person


def delete_person(person):
    """责任人存在任职(当前或历史)时拒绝删除, 建议改为离岗; 避免历史流水悬空."""
    if ZoneManager.query.filter_by(person_id=person.id).count():
        raise ConflictError("该责任人仍关联片区, 请先移除任职或在台账中改为离岗")
    if ZoneManagerHistory.query.filter_by(person_id=person.id).count():
        raise ConflictError("该责任人存在任职历史记录, 为保留追溯信息不允许删除, 可将其改为离岗")
    db.session.delete(person)
    db.session.commit()
    return {"id": person.id, "deleted": True}


def person_option_list():
    persons = (
        ResponsiblePerson.query.filter_by(status="active")
        .order_by(ResponsiblePerson.id.asc())
        .all()
    )
    return [person.to_option() for person in persons]


# ---------------------------------------------------------------------------
# 片区责任人任职关系(含历史流水)
# ---------------------------------------------------------------------------

def _get_assignment(zone, person_id):
    assignment = ZoneManager.query.filter_by(zone_id=zone.id, person_id=person_id).first()
    if assignment is None:
        raise NotFoundError("该责任人未在当前片区任职")
    return assignment


def add_zone_manager(zone, person_id, role, operator=None, note=None):
    person = get_person(person_id)
    if person.status != "active":
        raise ValidationError(
            "责任人 %s 当前为离岗状态, 不能分配任职" % person.name,
            fields={"person_id": "person_inactive"},
        )
    if ZoneManager.query.filter_by(zone_id=zone.id, person_id=person.id).first():
        raise ConflictError("%s 已在片区「%s」任职" % (person.name, zone.name))

    db.session.add(
        ZoneManager(zone_id=zone.id, person_id=person.id, role=role, assigned_at=datetime.now())
    )
    db.session.add(
        ZoneManagerHistory(
            zone_id=zone.id,
            person_id=person.id,
            change_type="person_added",
            role=role,
            operator=operator,
            note=note,
            zone_name=zone.name,
            person_name=person.name,
            person_employee_no=person.employee_no,
        )
    )
    db.session.commit()
    return zone


def change_zone_manager_role(zone, person_id, role, operator=None, note=None):
    assignment = _get_assignment(zone, person_id)
    previous_role = assignment.role
    if previous_role == role:
        raise ValidationError("角色未发生变化", fields={"role": "unchanged"})
    assignment.role = role
    person = assignment.person
    db.session.add(
        ZoneManagerHistory(
            zone_id=zone.id,
            person_id=person_id,
            change_type="role_changed",
            role=role,
            previous_role=previous_role,
            operator=operator,
            note=note,
            zone_name=zone.name,
            person_name=person.name if person else None,
            person_employee_no=person.employee_no if person else None,
        )
    )
    db.session.commit()
    return zone


def remove_zone_manager(zone, person_id, operator=None, note=None):
    assignment = _get_assignment(zone, person_id)
    person = assignment.person
    role = assignment.role
    db.session.delete(assignment)
    db.session.add(
        ZoneManagerHistory(
            zone_id=zone.id,
            person_id=person_id,
            change_type="person_removed",
            role=role,
            operator=operator,
            note=note,
            zone_name=zone.name,
            person_name=person.name if person else None,
            person_employee_no=person.employee_no if person else None,
        )
    )
    db.session.commit()
    return zone


# ---------------------------------------------------------------------------
# 监测点归属调整(含历史流水)
# ---------------------------------------------------------------------------

def validate_zone_id(zone_id):
    """Station 表单校验: None 表示暂不划分片区."""
    if zone_id is None:
        return None
    zone = db.session.get(Zone, int(zone_id))
    if zone is None:
        raise ValidationError("所选片区不存在", fields={"zone_id": "unknown"})
    return zone.id


def _derive_reason(previous_zone_id, zone_id):
    if previous_zone_id is None and zone_id is not None:
        return "assign"
    if zone_id is None:
        return "unassign"
    return "transfer"


def assign_station_zone(station, zone_id, operator=None, note=None):
    zone_id = validate_zone_id(zone_id)
    previous_zone_id = station.zone_id
    if zone_id == previous_zone_id:
        raise ValidationError("监测点所属片区未发生变化", fields={"zone_id": "unchanged"})

    reason = _derive_reason(previous_zone_id, zone_id)
    previous_zone = db.session.get(Zone, previous_zone_id) if previous_zone_id else None
    target_zone = db.session.get(Zone, zone_id) if zone_id else None
    station.zone_id = zone_id
    db.session.add(
        StationZoneHistory(
            station_id=station.id,
            zone_id=zone_id,
            previous_zone_id=previous_zone_id,
            reason=reason,
            changed_at=datetime.now(),
            operator=operator,
            note=note,
            station_code=station.code,
            station_name=station.name,
            zone_name=target_zone.name if target_zone else None,
            previous_zone_name=previous_zone.name if previous_zone else None,
        )
    )
    db.session.commit()
    return station


def assign_stations_zone(station_ids, zone_id, operator=None, note=None):
    """批量归属: 仅对实际发生变化的点位写历史, 返回各计数."""
    ids = list(dict.fromkeys(int(item) for item in station_ids))
    if not ids:
        raise ValidationError("请至少选择一个监测点", fields={"station_ids": "empty"})
    stations = Station.query.filter(Station.id.in_(ids)).all()
    found = {station.id for station in stations}
    missing = [item for item in ids if item not in found]

    target_zone = get_zone(zone_id) if zone_id else None
    changed = 0
    for station in stations:
        current_zone_id = station.zone_id
        next_zone_id = target_zone.id if target_zone else None
        if current_zone_id == next_zone_id:
            continue
        previous_zone = db.session.get(Zone, current_zone_id) if current_zone_id else None
        reason = _derive_reason(current_zone_id, next_zone_id)
        station.zone_id = next_zone_id
        db.session.add(
            StationZoneHistory(
                station_id=station.id,
                zone_id=target_zone.id if target_zone else None,
                previous_zone_id=previous_zone.id if previous_zone else None,
                reason=reason,
                changed_at=datetime.now(),
                operator=operator,
                note=note,
                station_code=station.code,
                station_name=station.name,
                zone_name=target_zone.name if target_zone else None,
                previous_zone_name=previous_zone.name if previous_zone else None,
            )
        )
        changed += 1
    db.session.commit()
    return {
        "selected": len(ids),
        "changed": changed,
        "unchanged": len(ids) - changed - len(missing),
        "missing": missing,
        "zone_id": target_zone.id if target_zone else None,
        "zone_name": target_zone.name if target_zone else None,
    }


def station_zone_history(station_id):
    return [
        item.to_dict()
        for item in StationZoneHistory.query.filter_by(station_id=station_id)
        .order_by(StationZoneHistory.changed_at.desc(), StationZoneHistory.id.desc())
        .all()
    ]


# ---------------------------------------------------------------------------
# 批量聚合辅助(列表 / 导出)
# ---------------------------------------------------------------------------

def _manager_rows(zone_ids):
    if not zone_ids:
        return []
    return (
        db.session.query(
            ZoneManager.zone_id,
            ZoneManager.role,
            ResponsiblePerson.id,
            ResponsiblePerson.name,
            ResponsiblePerson.phone,
            ResponsiblePerson.status,
        )
        .join(ResponsiblePerson, ResponsiblePerson.id == ZoneManager.person_id)
        .filter(ZoneManager.zone_id.in_(zone_ids))
        .order_by(ZoneManager.zone_id.asc(), ZoneManager.assigned_at.asc())
        .all()
    )


def manager_names_by_zone(zone_ids, active_only=True):
    """{zone_id: [{id,name,role,role_label,phone,status}...]}."""
    result = {zone_id: [] for zone_id in zone_ids}
    for zone_id, role, person_id, name, phone, status in _manager_rows(zone_ids):
        if active_only and status != "active":
            continue
        result.setdefault(zone_id, []).append(
            {
                "id": person_id,
                "name": name,
                "role": role,
                "role_label": ZONE_ROLE_LABELS.get(role, role),
                "phone": phone,
                "status": status,
                "status_label": PERSON_STATUS_LABELS.get(status, status),
            }
        )
    return result


def station_manager_map(station_ids, active_only=True):
    """{station_id: [责任人...]} 供监测数据 / 超标列表批量挂载, 避免 N+1."""
    if not station_ids:
        return {}
    zone_rows = (
        db.session.query(Station.id, Station.zone_id)
        .filter(Station.id.in_(station_ids))
        .all()
    )
    station_zone = {station_id: zone_id for station_id, zone_id in zone_rows}
    zone_ids = list({zone_id for zone_id in station_zone.values() if zone_id})
    manager_map = manager_names_by_zone(zone_ids, active_only=active_only)
    return {
        station_id: manager_map.get(zone_id, [])
        for station_id, zone_id in station_zone.items()
    }


def manager_text_by_zone(zone_ids, active_only=True):
    """CSV 导出用: 片区 -> '张三(片区负责人)、李四'."""
    manager_map = manager_names_by_zone(zone_ids, active_only=active_only)
    return {
        zone_id: "、".join(
            "%s(%s)" % (item["name"], item["role_label"]) for item in persons
        )
        for zone_id, persons in manager_map.items()
    }


def manager_text_for_stations(stations):
    """CSV 导出用: {station_id: 责任人文本}, 入参为 Station 行列表."""
    station_ids = [station.id for station in stations]
    manager_map = station_manager_map(station_ids)
    return {
        station_id: "、".join(
            "%s(%s)" % (item["name"], item["role_label"]) for item in manager_map.get(station_id, [])
        )
        for station_id in station_ids
    }


def top_zones(subquery, limit=5):
    """超标(含待办)片区排名, 供超标工作台与首页概览使用."""
    pending_expr = func.sum(
        case((subquery.c.status == "pending", 1), else_=0)
    )
    rows = (
        db.session.query(
            Station.zone_id,
            Zone.name,
            func.count().label("total_count"),
            pending_expr.label("pending_count"),
        )
        .join(Station, Station.id == subquery.c.station_id)
        .outerjoin(Zone, Zone.id == Station.zone_id)
        .group_by(Station.zone_id, Zone.name)
        .order_by(pending_expr.desc(), func.count().desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "zone_id": zone_id,
            "zone_name": zone_name or "未划分片区",
            "count": int(total),
            "pending_count": int(pending or 0),
        }
        for zone_id, zone_name, total, pending in rows
    ]


def zone_label_maps():
    return {
        "zone_status": ZONE_STATUS_LABELS,
        "person_status": PERSON_STATUS_LABELS,
        "zone_role": ZONE_ROLE_LABELS,
        "change_reason": CHANGE_REASON_LABELS,
    }

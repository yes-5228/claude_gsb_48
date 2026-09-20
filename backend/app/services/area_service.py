"""片区与责任人管理: CRUD、时间分段归属、片区排名、历史归属解析.

归属/任职变动采用时间分段 (SCD-2 风格): 变动时把当前记录的 ``effective_end``
置为生效时刻并记录变更原因与操作人, 再插入一条新的当前记录, 历史永不覆盖。
"""
from datetime import datetime

from sqlalchemy import and_, cast, func, or_, select

from ..domain.constants import AREA_STATUS_LABELS, PERSON_ROLE_LABELS, PERSON_STATUS_LABELS
from ..errors import ConflictError, NotFoundError, ValidationError
from ..extensions import db
from ..models import (
    Area,
    AreaMembership,
    Exceedance,
    Measurement,
    Person,
    Station,
    StationAssignment,
)
from ..models.base import iso

# 早于一切业务数据的时间: 老数据回填归属时使用, 保证历史查询都能命中片区
LEGACY_FROM = datetime(1970, 1, 1)


def _split(value):
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def get_area(area_id):
    area = db.session.get(Area, area_id)
    if area is None:
        raise NotFoundError("片区不存在: id=%s" % area_id)
    return area


def get_person(person_id):
    person = db.session.get(Person, person_id)
    if person is None:
        raise NotFoundError("责任人不存在: id=%s" % person_id)
    return person


# ---------------------------------------------------------------------------
# 片区 CRUD
# ---------------------------------------------------------------------------
def area_query(args):
    query = Area.query
    keyword = (args.get("keyword") or "").strip()
    if keyword:
        like = "%" + keyword + "%"
        query = query.filter(or_(Area.name.like(like), Area.code.like(like), Area.manager.like(like)))
    statuses = _split(args.get("status"))
    if statuses:
        query = query.filter(Area.status.in_(statuses))
    person_id = (args.get("person_id") or "").strip()
    if person_id:
        query = query.join(AreaMembership, and_(
            AreaMembership.area_id == Area.id,
            AreaMembership.person_id == int(person_id),
            AreaMembership.effective_end.is_(None),
        ))
    sort_field = {
        "code": Area.code,
        "name": Area.name,
        "created_at": Area.created_at,
    }.get(args.get("sort"), Area.code)
    direction = sort_field.desc() if (args.get("order") or "asc") == "desc" else sort_field.asc()
    return query.order_by(direction)


def create_area(data):
    code = data["code"]
    if Area.query.filter(func.lower(Area.code) == code.lower()).first():
        raise ConflictError("片区编码 %s 已存在" % code)
    name = data["name"]
    if Area.query.filter(Area.name == name).first():
        raise ConflictError("片区名称 %s 已存在" % name)
    area = Area(**data)
    db.session.add(area)
    db.session.commit()
    return area


def update_area(area, data):
    code = data.get("code")
    if code and code.lower() != area.code.lower():
        exists = Area.query.filter(func.lower(Area.code) == code.lower()).first()
        if exists and exists.id != area.id:
            raise ConflictError("片区编码 %s 已存在" % code)
    name = data.get("name")
    if name and name != area.name:
        exists = Area.query.filter(Area.name == name).first()
        if exists and exists.id != area.id:
            raise ConflictError("片区名称 %s 已存在" % name)
    old_name = area.name
    for field, value in data.items():
        setattr(area, field, value)
    if name and name != old_name:
        # 名称同步到监测点冗余字段, 保证列表/导出里的区域名一致
        Station.query.filter(Station.area_id == area.id).update({"area": name})
    db.session.commit()
    return area


def area_stats_map(area_ids):
    """每个片区当前挂接的点位数、监测数据与超标待办计数。"""
    if not area_ids:
        return {}
    stations = dict(
        db.session.query(Station.area_id, func.count(Station.id))
        .filter(Station.area_id.in_(area_ids))
        .group_by(Station.area_id)
        .all()
    )
    measurements = dict(
        db.session.query(Station.area_id, func.count(Measurement.id))
        .join(Station, Measurement.station_id == Station.id)
        .filter(Station.area_id.in_(area_ids))
        .group_by(Station.area_id)
        .all()
    )
    exceeded = dict(
        db.session.query(Station.area_id, func.count(Measurement.id))
        .join(Station, Measurement.station_id == Station.id)
        .filter(Station.area_id.in_(area_ids), Measurement.is_exceeded.is_(True))
        .group_by(Station.area_id)
        .all()
    )
    pending = dict(
        db.session.query(Station.area_id, func.count(Exceedance.id))
        .join(Station, Exceedance.station_id == Station.id)
        .filter(Station.area_id.in_(area_ids), Exceedance.status == "pending")
        .group_by(Station.area_id)
        .all()
    )
    return {
        area_id: {
            "station_count": int(stations.get(area_id, 0)),
            "measurement_count": int(measurements.get(area_id, 0)),
            "exceeded_count": int(exceeded.get(area_id, 0)),
            "pending_count": int(pending.get(area_id, 0)),
        }
        for area_id in area_ids
    }


def current_persons_map(area_ids):
    """片区当前在任责任人 (含任职角色), 按片区分组。"""
    if not area_ids:
        return {}
    rows = (
        AreaMembership.query.join(Person, AreaMembership.person_id == Person.id)
        .filter(
            AreaMembership.area_id.in_(area_ids),
            AreaMembership.effective_end.is_(None),
        )
        .order_by(AreaMembership.effective_from.asc())
        .all()
    )
    result = {area_id: [] for area_id in area_ids}
    for membership in rows:
        person = membership.person
        result[membership.area_id].append(
            {
                "membership_id": membership.id,
                "person_id": person.id,
                "name": person.name,
                "employee_no": person.employee_no,
                "phone": person.phone,
                "department": person.department,
                "role": membership.role or person.role,
                "role_label": (PERSON_ROLE_LABELS.get(membership.role or person.role)
                               or membership.role or person.role),
            }
        )
    return result


def area_list():
    return Area.query.order_by(Area.code.asc()).all()


def area_options():
    return [area.to_option() for area in area_list()]


def area_detail(area):
    stats = area_stats_map([area.id]).get(area.id, {})
    persons = current_persons_map([area.id]).get(area.id, [])
    station_rows = (
        Station.query.filter(Station.area_id == area.id)
        .order_by(Station.code.asc())
        .all()
    )
    stations = [
        {
            "id": station.id,
            "code": station.code,
            "name": station.name,
            "status": station.status,
            "status_label": station.to_dict()["status_label"],
            "station_type_label": station.to_dict()["station_type_label"],
        }
        for station in station_rows
    ]
    return {
        "area": area.to_dict(),
        "stats": stats,
        "persons": persons,
        "stations": stations,
    }


# ---------------------------------------------------------------------------
# 责任人 CRUD
# ---------------------------------------------------------------------------
def person_query(args):
    query = Person.query
    keyword = (args.get("keyword") or "").strip()
    if keyword:
        like = "%" + keyword + "%"
        query = query.filter(
            or_(Person.name.like(like), Person.employee_no.like(like),
                Person.department.like(like), Person.phone.like(like))
        )
    statuses = _split(args.get("status"))
    if statuses:
        query = query.filter(Person.status.in_(statuses))
    roles = _split(args.get("role"))
    if roles:
        query = query.filter(Person.role.in_(roles))
    area_id = (args.get("area_id") or "").strip()
    if area_id:
        query = query.join(AreaMembership, and_(
            AreaMembership.person_id == Person.id,
            AreaMembership.area_id == int(area_id),
            AreaMembership.effective_end.is_(None),
        ))
    sort_field = {
        "name": Person.name,
        "employee_no": Person.employee_no,
        "created_at": Person.created_at,
    }.get(args.get("sort"), Person.employee_no)
    direction = sort_field.desc() if (args.get("order") or "asc") == "desc" else sort_field.asc()
    return query.order_by(direction.nullslast(), Person.id.asc())


def person_current_areas(person_ids):
    if not person_ids:
        return {}
    rows = (
        AreaMembership.query.join(Area, AreaMembership.area_id == Area.id)
        .filter(
            AreaMembership.person_id.in_(person_ids),
            AreaMembership.effective_end.is_(None),
        )
        .all()
    )
    result = {person_id: [] for person_id in person_ids}
    for membership in rows:
        result[membership.person_id].append(membership.area.to_option())
    return result


def create_person(data):
    employee_no = (data.get("employee_no") or "").strip()
    if employee_no:
        if Person.query.filter(Person.employee_no == employee_no).first():
            raise ConflictError("工号 %s 已存在" % employee_no)
    else:
        data["employee_no"] = None
    area_id = data.pop("_area_id", None)
    person = Person(**data)
    db.session.add(person)
    db.session.flush()

    if area_id:
        area = db.session.get(Area, area_id)
        if area is None:
            raise ValidationError("归属片区不存在: id=%s" % area_id,
                                  fields={"area_id": "not_found"})
        _open_membership(area, person, role=None,
                         reason=None, changed_by=None, effective_from=datetime.now())
    db.session.commit()
    return person


def update_person(person, data):
    data.pop("_area_id", None)
    employee_no = data.get("employee_no")
    if employee_no is not None:
        employee_no = employee_no.strip() or None
        if employee_no and employee_no != (person.employee_no or ""):
            exists = Person.query.filter(Person.employee_no == employee_no).first()
            if exists and exists.id != person.id:
                raise ConflictError("工号 %s 已存在" % employee_no)
        data["employee_no"] = employee_no
    for field, value in data.items():
        setattr(person, field, value)
    db.session.commit()
    return person


def delete_person(person):
    """责任人只在没有任何任职历史时允许删除, 有历史时建议改为离岗。"""
    history_count = AreaMembership.query.filter_by(person_id=person.id).count()
    if history_count:
        raise ConflictError("该责任人存在任职记录, 不能删除; 可将状态改为“离岗”以保留历史")
    db.session.delete(person)
    db.session.commit()


def person_options():
    return [person.to_option() for person in Person.query.order_by(Person.id.asc()).all()]


# ---------------------------------------------------------------------------
# 时间分段归属: 监测点 <-> 片区
# ---------------------------------------------------------------------------
def _get_open_assignment(station_id):
    return StationAssignment.query.filter(
        StationAssignment.station_id == station_id,
        StationAssignment.effective_end.is_(None),
    ).first()


def assign_station(station, area, effective_from=None, reason=None, changed_by=None,
                   replace_current=False):
    """把监测点划入片区 (时间分段)。同片区重复划转直接返回当前记录。

    ``replace_current=True`` 时直接更正当前生效记录 (用于建档时间录错等场景),
    不留新分段; 默认追加新分段并要求生效时间不早于当前记录。
    """
    effective_from = effective_from or datetime.now()
    current = _get_open_assignment(station.id)
    if current and current.area_id == area.id:
        return current, False

    if current:
        if replace_current:
            current.area_id = area.id
            current.effective_from = effective_from
            current.change_reason = reason or current.change_reason
            current.changed_by = changed_by or current.changed_by
            station.area_id = area.id
            station.area = area.name
            db.session.flush()
            return current, True
        if effective_from < current.effective_from:
            raise ValidationError(
                "生效时间不能早于当前归属的生效时间 %s"
                % iso(current.effective_from),
                fields={"effective_from": "invalid_range"},
            )
        current.effective_end = effective_from
        current.change_reason = reason or current.change_reason
        current.changed_by = changed_by or current.changed_by

    assignment = StationAssignment(
        station_id=station.id,
        area_id=area.id,
        effective_from=effective_from,
        effective_end=None,
        change_reason=reason,
        changed_by=changed_by,
    )
    db.session.add(assignment)
    station.area_id = area.id
    station.area = area.name
    db.session.flush()
    return assignment, True


def assign_stations(station_ids, area_id, effective_from=None, reason=None, changed_by=None,
                    replace_current=False):
    """批量把多个点位划到同一片区。"""
    if not station_ids:
        raise ValidationError("请至少选择一个监测点", fields={"station_ids": "empty"})
    station_ids = list(dict.fromkeys(int(item) for item in station_ids))
    area = get_area(area_id)
    if area.status != "active":
        raise ValidationError("片区 %s 已停用, 不能继续挂接监测点" % area.name,
                              fields={"area_id": "inactive"})
    stations = Station.query.filter(Station.id.in_(station_ids)).all()
    found = {station.id for station in stations}
    missing = [sid for sid in station_ids if sid not in found]
    if missing:
        raise NotFoundError("监测点不存在: %s" % ", ".join(str(i) for i in missing))

    changed = 0
    for station in stations:
        _, moved = assign_station(station, area, effective_from=effective_from,
                                  reason=reason, changed_by=changed_by,
                                  replace_current=replace_current)
        changed += int(moved)
    db.session.commit()
    return {"area_id": area.id, "requested": len(station_ids), "moved": changed,
            "unchanged": len(station_ids) - changed, "missing": missing}


def open_assignment_for(station):
    """确保监测点存在当前归属记录, 没有则按其当前 area_id/area 补建。"""
    current = _get_open_assignment(station.id)
    if current:
        return current
    area = db.session.get(Area, station.area_id) if station.area_id else None
    if area is None:
        area = ensure_area_by_name(station.area)
        station.area_id = area.id
    current = StationAssignment(
        station_id=station.id, area_id=area.id,
        effective_from=LEGACY_FROM, effective_end=None,
        change_reason="历史数据回填",
    )
    db.session.add(current)
    return current


def station_assignment_history(station_id=None, area_id=None, limit=200):
    query = StationAssignment.query
    if station_id:
        query = query.filter(StationAssignment.station_id == int(station_id))
    if area_id:
        query = query.filter(StationAssignment.area_id == int(area_id))
    return query.order_by(
        StationAssignment.effective_from.desc(), StationAssignment.id.desc()
    ).limit(limit).all()


# ---------------------------------------------------------------------------
# 时间分段任职: 责任人 <-> 片区
# ---------------------------------------------------------------------------
def _get_open_membership(area_id, person_id):
    return AreaMembership.query.filter(
        AreaMembership.area_id == area_id,
        AreaMembership.person_id == person_id,
        AreaMembership.effective_end.is_(None),
    ).first()


def _open_membership(area, person, role=None, reason=None, changed_by=None,
                     effective_from=None):
    effective_from = effective_from or datetime.now()
    membership = AreaMembership(
        area_id=area.id,
        person_id=person.id,
        role=role or person.role,
        effective_from=effective_from,
        effective_end=None,
        change_reason=reason,
        changed_by=changed_by,
    )
    db.session.add(membership)
    db.session.flush()
    return membership


def add_membership(area, person, role=None, effective_from=None, reason=None, changed_by=None):
    effective_from = effective_from or datetime.now()
    current = _get_open_membership(area.id, person.id)
    if current:
        raise ConflictError("%s 当前已在片区「%s」任职" % (person.name, area.name))
    membership = _open_membership(area, person, role=role, reason=reason,
                                  changed_by=changed_by, effective_from=effective_from)
    db.session.commit()
    return membership


def end_membership(membership, effective_from=None, reason=None, changed_by=None):
    effective_from = effective_from or datetime.now()
    if effective_from < membership.effective_from:
        raise ValidationError("卸任时间不能早于任职时间", fields={"effective_from": "invalid_range"})
    membership.effective_end = effective_from
    membership.change_reason = reason or membership.change_reason
    membership.changed_by = changed_by or membership.changed_by
    db.session.commit()
    return membership


def get_membership(membership_id):
    membership = db.session.get(AreaMembership, membership_id)
    if membership is None:
        raise NotFoundError("任职记录不存在: id=%s" % membership_id)
    return membership


def membership_history(area_id=None, person_id=None, limit=200):
    query = AreaMembership.query
    if area_id:
        query = query.filter(AreaMembership.area_id == int(area_id))
    if person_id:
        query = query.filter(AreaMembership.person_id == int(person_id))
    return query.order_by(
        AreaMembership.effective_from.desc(), AreaMembership.id.desc()
    ).limit(limit).all()


def area_ids_for_person(person_id, at=None):
    """责任人在某时刻(默认当前)任职的片区 id 集合, 用于按责任人筛选数据/待办。"""
    at = at or datetime.now()
    rows = AreaMembership.query.with_entities(AreaMembership.area_id).filter(
        AreaMembership.person_id == int(person_id),
        AreaMembership.effective_from <= at,
        or_(AreaMembership.effective_end.is_(None), AreaMembership.effective_end > at),
    ).all()
    return [row[0] for row in rows]


# ---------------------------------------------------------------------------
# 历史片区归属解析 (供查询/统计/导出使用)
# ---------------------------------------------------------------------------
def effective_area_id_expr(owner_col, moment_col):
    """返回 “某主体在某时刻所属片区 id” 的相关子查询表达式。

    归属记录互不重叠, 同一时刻至多命中一条; 未命中历史记录时回退到监测点当前片区。
    """
    return (
        select(StationAssignment.area_id)
        .where(
            StationAssignment.station_id == owner_col,
            StationAssignment.effective_from <= moment_col,
            or_(StationAssignment.effective_end.is_(None),
                StationAssignment.effective_end > moment_col),
        )
        .order_by(StationAssignment.effective_from.desc())
        .limit(1)
        .correlate_except(StationAssignment)
        .scalar_subquery()
    )


def area_name_expr(area_id_expr):
    return (
        select(Area.name)
        .where(Area.id == area_id_expr)
        .correlate_except(Area)
        .scalar_subquery()
    )


def resolve_area_names(area_ids):
    if not area_ids:
        return {}
    rows = Area.query.filter(Area.id.in_(list({aid for aid in area_ids if aid}))).all()
    return {area.id: area.name for area in rows}


def historical_area_resolver(rows, station_attr="station"):
    """为一批监测/超标记录批量还原“数据产生时所属片区”, 返回 row -> area_id 函数。

    一次性取出这些点位的全部归属时间段, 在内存按时点匹配, 避免逐行子查询。
    """
    station_ids = {getattr(row, "station_id", None) for row in rows}
    station_ids.discard(None)
    assignments = {}
    if station_ids:
        records = StationAssignment.query.filter(
            StationAssignment.station_id.in_(station_ids)
        ).order_by(StationAssignment.effective_from.desc()).all()
        for record in records:
            assignments.setdefault(record.station_id, []).append(record)
    current_area = {}
    stations = Station.query.filter(Station.id.in_(station_ids)).all() if station_ids else []
    for station in stations:
        current_area[station.id] = station.area_id

    def resolve(row):
        moment = getattr(row, "measured_at", None)
        station_id = getattr(row, "station_id", None)
        for record in assignments.get(station_id, []):
            if record.effective_from <= moment and (
                record.effective_end is None or record.effective_end > moment
            ):
                return record.area_id
        return current_area.get(station_id)

    return resolve


def build_export_context(rows, area_id_resolver):
    """为导出行批量补齐“片区名称 + 责任人”。

    ``area_id_resolver(row)`` 按历史归属给出片区 id。责任人取该片区当前在任人员
    (快照语义与超标限值一致: 数据归属按历史, 联系人按当前)。
    """
    area_ids = [area_id_resolver(row) for row in rows]
    name_map = resolve_area_names(area_ids)
    persons_map = current_persons_map(list(name_map.keys()))
    context = {}
    for area_id in set(area_ids):
        if area_id is None:
            continue
        context[area_id] = {
            "name": name_map.get(area_id, "未分组片区"),
            "persons": "、".join(p["name"] for p in persons_map.get(area_id, [])),
        }
    return context


# ---------------------------------------------------------------------------
# 兼容老数据: 以名称获取/创建片区, 并完成归属回填
# ---------------------------------------------------------------------------
def ensure_area_by_name(name, commit=False):
    name = (name or "").strip() or "未分组片区"
    area = Area.query.filter(Area.name == name).first()
    if area:
        return area
    count = Area.query.count()
    code = "AREA-%03d" % (count + 1)
    while Area.query.filter(Area.code == code).first():
        count += 1
        code = "AREA-%03d" % (count + 1)
    area = Area(code=code, name=name, status="active", remark="按历史区域名自动建立")
    db.session.add(area)
    db.session.flush()
    if commit:
        db.session.commit()
    return area


def backfill_station_areas():
    """老库启动时执行一次: 为没有片区归属的监测点补建片区与历史归属段。"""
    changed = 0
    stations = Station.query.all()
    for station in stations:
        if station.area_id and _get_open_assignment(station.id):
            continue
        if not station.area_id:
            area = ensure_area_by_name(station.area)
            station.area_id = area.id
        if not _get_open_assignment(station.id):
            db.session.add(
                StationAssignment(
                    station_id=station.id,
                    area_id=station.area_id,
                    effective_from=LEGACY_FROM,
                    effective_end=None,
                    change_reason="历史数据回填",
                )
            )
            changed += 1
    if changed:
        db.session.commit()
    return changed


# ---------------------------------------------------------------------------
# 片区排名 (统计与超标待办)
# ---------------------------------------------------------------------------
def area_ranking(filters=None):
    """按监测点历史归属的片区聚合: 数据量、超标、超标率、待办待标注。"""
    from . import query_service

    filters = filters if filters is not None else query_service.parse_filters({})
    effective_id = effective_area_id_expr(Measurement.station_id, Measurement.measured_at)
    effective_name = area_name_expr(effective_id)

    query = query_service.apply_filters(
        db.session.query(
            effective_id.label("area_id"),
            effective_name.label("area_name"),
            func.count(Measurement.id).label("measurement_count"),
            func.sum(cast(Measurement.is_exceeded, db.Integer)).label("exceeded_count"),
        ),
        filters,
    )
    rows = query.group_by(effective_id, effective_name).all()

    pending_rows = dict(
        db.session.query(Station.area_id, func.count(Exceedance.id))
        .join(Station, Exceedance.station_id == Station.id)
        .filter(Exceedance.status == "pending")
        .group_by(Station.area_id)
        .all()
    )

    items = []
    for row in rows:
        area_id = row.area_id
        count = int(row.measurement_count or 0)
        exceeded = int(row.exceeded_count or 0)
        items.append({
            "area_id": area_id,
            "key": row.area_name or ("未分组#%s" % area_id if area_id else "未分组"),
            "label": row.area_name or "未分组片区",
            "measurement_count": count,
            "exceeded_count": exceeded,
            "exceed_rate": round(exceeded / count, 4) if count else 0.0,
            "pending_count": int(pending_rows.get(area_id, 0)),
        })
    items.sort(key=lambda item: (-item["pending_count"], -item["exceeded_count"],
                                 -item["measurement_count"]))
    totals = {
        "measurement_count": sum(i["measurement_count"] for i in items),
        "exceeded_count": sum(i["exceeded_count"] for i in items),
        "pending_count": sum(i["pending_count"] for i in items),
    }
    return {"items": items, "totals": totals, "generated_at": iso(datetime.now())}

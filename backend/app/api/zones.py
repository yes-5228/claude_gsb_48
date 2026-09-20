"""监测点片区与责任人管理 API."""
from flask import Blueprint, request

from ..domain.constants import (
    PERSON_STATUS_LABELS,
    ZONE_ROLE_LABELS,
    ZONE_STATUS_LABELS,
)
from ..services import zone_service
from ..utils.pagination import paginate_query
from ..utils.validation import Validator
from .helpers import json_payload, list_payload

bp = Blueprint("zones", __name__)


# ---------------------------------------------------------------------------
# 参数校验
# ---------------------------------------------------------------------------

def _validate_zone(data, partial=False):
    validator = Validator(data)
    validator.text("code", "片区编码", required=not partial, max_length=32)
    validator.text("name", "片区名称", required=not partial, max_length=120)
    validator.text("description", "片区说明", required=False, max_length=500)
    validator.choice(
        "status", "片区状态",
        choices=tuple(ZONE_STATUS_LABELS.keys()),
        required=False,
        default="active",
    )
    cleaned = validator.raise_if_invalid("片区信息不合法")
    if partial:
        cleaned = {key: value for key, value in cleaned.items() if key in data}
    return cleaned


def _validate_person(data, partial=False):
    validator = Validator(data)
    validator.text("name", "姓名", required=not partial, max_length=64)
    validator.text("employee_no", "工号", required=False, max_length=32)
    validator.text("phone", "联系电话", required=False, max_length=32)
    validator.text("department", "所属部门", required=False, max_length=120)
    validator.text("title", "职务", required=False, max_length=64)
    validator.choice(
        "status", "在岗状态",
        choices=tuple(PERSON_STATUS_LABELS.keys()),
        required=False,
        default="active",
    )
    validator.text("remark", "备注", required=False, max_length=500)
    cleaned = validator.raise_if_invalid("责任人信息不合法")
    if partial:
        cleaned = {key: value for key, value in cleaned.items() if key in data}
    return cleaned


def _validate_assignment(data, role_required=True):
    validator = Validator(data)
    person_id = validator.number("person_id", "责任人", required=True, minimum=1)
    role = validator.choice(
        "role", "责任角色",
        choices=tuple(ZONE_ROLE_LABELS.keys()),
        required=role_required,
        default="manager",
    )
    validator.text("operator", "操作人", required=False, max_length=64)
    validator.text("note", "变动说明", required=False, max_length=500)
    validator.raise_if_invalid("任职信息不合法")
    cleaned = dict(validator.cleaned)
    cleaned["person_id"] = int(person_id) if person_id is not None else None
    return cleaned


def _validate_assign_stations(data):
    validator = Validator(data)
    raw_zone_id = data.get("zone_id")
    if raw_zone_id in (None, ""):
        zone_id = None
    else:
        zone_id = validator.number("zone_id", "片区", required=False, minimum=1)
        zone_id = int(zone_id) if zone_id is not None else None
    validator.text("operator", "操作人", required=False, max_length=64)
    validator.text("note", "变动说明", required=False, max_length=500)
    validator.raise_if_invalid("归属信息不合法")
    station_ids = list_payload("station_ids", data)
    return {
        "zone_id": zone_id,
        "station_ids": station_ids,
        "operator": validator.cleaned.get("operator"),
        "note": validator.cleaned.get("note"),
    }


# ---------------------------------------------------------------------------
# 片区
# ---------------------------------------------------------------------------

@bp.get("/zones", strict_slashes=False)
def list_zones():
    query = zone_service.zone_query(request.args)
    result = paginate_query(query, lambda zone: zone.to_dict())
    stats = zone_service.zone_stats([item["id"] for item in result["items"]])
    for item in result["items"]:
        item["stats"] = stats.get(item["id"], {})
    result["unassigned_station_count"] = zone_service.unassigned_station_count()
    return result


@bp.post("/zones", strict_slashes=False)
def create_zone():
    payload = _validate_zone(json_payload())
    zone = zone_service.create_zone(payload)
    return zone.to_dict(), 201


@bp.get("/zones/options")
def zone_options():
    return {"items": zone_service.zone_option_list()}


@bp.get("/zones/<int:zone_id>")
def get_zone(zone_id):
    zone = zone_service.get_zone(zone_id)
    return zone_service.zone_detail(zone)


@bp.put("/zones/<int:zone_id>")
def update_zone(zone_id):
    zone = zone_service.get_zone(zone_id)
    payload = _validate_zone(json_payload(), partial=True)
    return zone_service.update_zone(zone, payload).to_dict()


@bp.delete("/zones/<int:zone_id>")
def delete_zone(zone_id):
    zone = zone_service.get_zone(zone_id)
    return zone_service.delete_zone(zone)


@bp.get("/zones/<int:zone_id>/stations")
def zone_stations(zone_id):
    zone = zone_service.get_zone(zone_id)
    return zone_service.zone_detail(zone)["stations"]


@bp.get("/zones/<int:zone_id>/history")
def zone_history(zone_id):
    zone = zone_service.get_zone(zone_id)
    detail = zone_service.zone_detail(zone)
    return {
        "station_history": detail["station_history"],
        "manager_history": detail["manager_history"],
    }


@bp.post("/zones/<int:zone_id>/managers")
def add_zone_manager(zone_id):
    zone = zone_service.get_zone(zone_id)
    payload = _validate_assignment(json_payload())
    zone_service.add_zone_manager(
        zone,
        payload["person_id"],
        payload["role"],
        operator=payload.get("operator"),
        note=payload.get("note"),
    )
    return zone_service.zone_detail(zone)["zone"], 201


@bp.put("/zones/<int:zone_id>/managers/<int:person_id>")
def change_manager_role(zone_id, person_id):
    zone = zone_service.get_zone(zone_id)
    payload = _validate_assignment(
        {**json_payload(), "person_id": person_id}, role_required=True
    )
    zone_service.change_zone_manager_role(
        zone,
        person_id,
        payload["role"],
        operator=payload.get("operator"),
        note=payload.get("note"),
    )
    return zone_service.zone_detail(zone)["zone"]


@bp.delete("/zones/<int:zone_id>/managers/<int:person_id>")
def remove_zone_manager(zone_id, person_id):
    zone = zone_service.get_zone(zone_id)
    data = request.args
    zone_service.remove_zone_manager(
        zone, person_id, operator=data.get("operator"), note=data.get("note")
    )
    return zone_service.zone_detail(zone)["zone"]


@bp.post("/zones/assign-stations")
def assign_stations():
    payload = _validate_assign_stations(json_payload())
    result = zone_service.assign_stations_zone(
        payload["station_ids"],
        payload["zone_id"],
        operator=payload.get("operator"),
        note=payload.get("note"),
    )
    return result


@bp.get("/stations/<int:station_id>/zone-history")
def station_zone_history(station_id):
    from ..services import station_service

    station = station_service.get_station(station_id)
    return {"items": zone_service.station_zone_history(station.id)}


# ---------------------------------------------------------------------------
# 责任人
# ---------------------------------------------------------------------------

@bp.get("/persons", strict_slashes=False)
def list_persons():
    query = zone_service.person_query(request.args)
    result = paginate_query(
        query, lambda person: person.to_dict(include_zones=True)
    )
    return result


@bp.post("/persons", strict_slashes=False)
def create_person():
    payload = _validate_person(json_payload())
    person = zone_service.create_person(payload)
    return person.to_dict(include_zones=True), 201


@bp.get("/persons/options")
def person_options():
    return {"items": zone_service.person_option_list()}


@bp.get("/persons/<int:person_id>")
def get_person(person_id):
    person = zone_service.get_person(person_id)
    return person.to_dict(include_zones=True)


@bp.put("/persons/<int:person_id>")
def update_person(person_id):
    person = zone_service.get_person(person_id)
    payload = _validate_person(json_payload(), partial=True)
    return zone_service.update_person(person, payload).to_dict(include_zones=True)


@bp.delete("/persons/<int:person_id>")
def delete_person(person_id):
    person = zone_service.get_person(person_id)
    return zone_service.delete_person(person)

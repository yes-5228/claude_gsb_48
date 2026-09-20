"""片区与责任人管理 API: 片区/责任人 CRUD、归属划转、任职管理、历史记录、片区排名."""
from flask import Blueprint, request

from ..domain.constants import (
    AREA_STATUS_LABELS,
    PERSON_ROLE_LABELS,
    PERSON_STATUS_LABELS,
)
from ..services import area_service, query_service
from ..utils.pagination import paginate_query
from ..utils.validation import Validator, parse_datetime
from .helpers import json_payload, list_payload

bp = Blueprint("areas", __name__)


# ---------------------------------------------------------------------------
# 校验器
# ---------------------------------------------------------------------------
def _validate_area(data, partial=False):
    validator = Validator(data)
    validator.text("code", "片区编码", required=not partial, max_length=32)
    validator.text("name", "片区名称", required=not partial, max_length=120)
    validator.text("manager", "片区主管", required=False, max_length=64)
    validator.text("phone", "联系电话", required=False, max_length=32)
    validator.choice(
        "status", "状态",
        choices=tuple(AREA_STATUS_LABELS.keys()),
        required=False, default="active",
    )
    validator.text("remark", "备注", required=False, max_length=500)
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
    validator.choice(
        "role", "岗位",
        choices=tuple(PERSON_ROLE_LABELS.keys()),
        required=False, default="officer",
    )
    validator.choice(
        "status", "状态",
        choices=tuple(PERSON_STATUS_LABELS.keys()),
        required=False, default="active",
    )
    validator.text("remark", "备注", required=False, max_length=500)
    validator.number("area_id", "归属片区", minimum=1)
    cleaned = validator.raise_if_invalid("责任人信息不合法")
    if "area_id" in data and data.get("area_id") not in (None, ""):
        cleaned["_area_id"] = int(cleaned["area_id"])
    cleaned.pop("area_id", None)
    if partial:
        cleaned = {key: value for key, value in cleaned.items() if key in data or key == "_area_id"}
    return cleaned


def _effective_from(data):
    raw = (data or {}).get("effective_from")
    return parse_datetime(raw, "生效时间") if raw not in (None, "") else None


# ---------------------------------------------------------------------------
# 片区
# ---------------------------------------------------------------------------
@bp.get("/", strict_slashes=False)
def list_areas():
    query = area_service.area_query(request.args)
    result = paginate_query(query, lambda area: area.to_dict())
    stats = area_service.area_stats_map([item["id"] for item in result["items"]])
    persons = area_service.current_persons_map([item["id"] for item in result["items"]])
    for item in result["items"]:
        item["stats"] = stats.get(item["id"], {})
        item["persons"] = persons.get(item["id"], [])
    return result


@bp.post("/", strict_slashes=False)
def create_area():
    payload = _validate_area(json_payload())
    area = area_service.create_area(payload)
    return area.to_dict(), 201


@bp.get("/options")
def area_options():
    return {"items": area_service.area_options()}


@bp.get("/ranking")
def area_ranking():
    """片区统计排名 (数据量/超标/超标率/待办), 支持与数据查询相同的筛选条件。"""
    filters = query_service.parse_filters(request.args)
    return area_service.area_ranking(filters)


@bp.get("/history")
def assignment_history():
    """归属划转历史 (可按片区或点位过滤)。"""
    station_id = request.args.get("station_id", type=int)
    area_id = request.args.get("area_id", type=int)
    limit = min(request.args.get("limit", default=100, type=int) or 100, 500)
    rows = area_service.station_assignment_history(
        station_id=station_id, area_id=area_id, limit=limit
    )
    return {"items": [row.to_dict() for row in rows], "total": len(rows)}


@bp.post("/assignments")
def assign_stations():
    """批量把监测点划转到某片区, 记录生效时间与变更原因。"""
    data = json_payload()
    validator = Validator(data)
    area_id = validator.number("area_id", "目标片区", required=True, minimum=1)
    validator.text("change_reason", "变更原因", required=True, max_length=200)
    validator.text("changed_by", "操作人", required=False, max_length=64)
    validator.raise_if_invalid("归属划转信息不合法")
    station_ids = list_payload("station_ids", data)
    return area_service.assign_stations(
        station_ids=station_ids,
        area_id=int(area_id),
        effective_from=_effective_from(data),
        reason=((data.get("change_reason") or "").strip() or None),
        changed_by=(data.get("changed_by") or None),
    )


@bp.get("/<int:area_id>")
def get_area(area_id):
    area = area_service.get_area(area_id)
    return area_service.area_detail(area)


@bp.put("/<int:area_id>")
def update_area(area_id):
    area = area_service.get_area(area_id)
    payload = _validate_area(json_payload(), partial=True)
    return area_service.update_area(area, payload).to_dict()


# ---------------------------------------------------------------------------
# 责任人
# ---------------------------------------------------------------------------
@bp.get("/persons/options")
def person_options():
    return {"items": area_service.person_options()}


@bp.get("/persons", strict_slashes=False)
def list_persons():
    query = area_service.person_query(request.args)
    result = paginate_query(query, lambda person: person.to_dict())
    areas_map = area_service.person_current_areas([item["id"] for item in result["items"]])
    for item in result["items"]:
        item["areas"] = areas_map.get(item["id"], [])
    return result


@bp.post("/persons", strict_slashes=False)
def create_person():
    payload = _validate_person(json_payload())
    person = area_service.create_person(payload)
    return person.to_dict(), 201


@bp.get("/persons/<int:person_id>")
def get_person(person_id):
    person = area_service.get_person(person_id)
    payload = person.to_dict()
    payload["areas"] = area_service.person_current_areas([person.id]).get(person.id, [])
    payload["memberships"] = [
        row.to_dict() for row in area_service.membership_history(person_id=person.id)
    ]
    return payload


@bp.put("/persons/<int:person_id>")
def update_person(person_id):
    person = area_service.get_person(person_id)
    payload = _validate_person(json_payload(), partial=True)
    payload.pop("_area_id", None)  # 任职关系走 memberships 接口
    return area_service.update_person(person, payload).to_dict()


@bp.delete("/persons/<int:person_id>")
def delete_person(person_id):
    person = area_service.get_person(person_id)
    area_service.delete_person(person)
    return {"id": person_id, "deleted": True}


# ---------------------------------------------------------------------------
# 任职管理 (责任人 <-> 片区, 时间分段)
# ---------------------------------------------------------------------------
@bp.get("/memberships/history")
def membership_history():
    area_id = request.args.get("area_id", type=int)
    person_id = request.args.get("person_id", type=int)
    limit = min(request.args.get("limit", default=100, type=int) or 100, 500)
    rows = area_service.membership_history(area_id=area_id, person_id=person_id, limit=limit)
    return {"items": [row.to_dict() for row in rows], "total": len(rows)}


@bp.post("/memberships")
def add_membership():
    data = json_payload()
    validator = Validator(data)
    area_id = validator.number("area_id", "片区", required=True, minimum=1)
    person_id = validator.number("person_id", "责任人", required=True, minimum=1)
    validator.choice(
        "role", "岗位", choices=tuple(PERSON_ROLE_LABELS.keys()), required=False
    )
    validator.text("change_reason", "变更原因", required=False, max_length=200)
    validator.text("changed_by", "操作人", required=False, max_length=64)
    validator.raise_if_invalid("任职信息不合法")
    area = area_service.get_area(int(area_id))
    person = area_service.get_person(int(person_id))
    role = data.get("role") or None
    membership = area_service.add_membership(
        area, person, role=role,
        effective_from=_effective_from(data),
        reason=(data.get("change_reason") or None),
        changed_by=(data.get("changed_by") or None),
    )
    return membership.to_dict(), 201


@bp.post("/memberships/<int:membership_id>/leave")
def leave_membership(membership_id):
    data = json_payload()
    validator = Validator(data)
    validator.text("change_reason", "变更原因", required=True, max_length=200)
    validator.text("changed_by", "操作人", required=False, max_length=64)
    validator.raise_if_invalid("卸任信息不合法")
    membership = area_service.get_membership(membership_id)
    updated = area_service.end_membership(
        membership,
        effective_from=_effective_from(data),
        reason=(data.get("change_reason") or "").strip(),
        changed_by=(data.get("changed_by") or None),
    )
    return updated.to_dict()

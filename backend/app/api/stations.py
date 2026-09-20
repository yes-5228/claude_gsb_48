"""监测点台账 API."""
from flask import Blueprint, request

from ..domain.constants import STATION_STATUS_LABELS, STATION_TYPE_LABELS
from ..extensions import db
from ..services import station_service, zone_service
from ..utils.pagination import paginate_query
from ..utils.validation import Validator
from .helpers import json_payload

bp = Blueprint("stations", __name__)


def _validate_station(data, partial=False):
    validator = Validator(data)
    validator.text("code", "监测点编码", required=not partial, max_length=32)
    validator.text("name", "监测点名称", required=not partial, max_length=120)
    validator.text("area", "所属区域", required=not partial, max_length=64)
    validator.text("address", "详细地址", required=False, max_length=200)
    raw_zone_id = data.get("zone_id")
    if raw_zone_id in (None, ""):
        validator.cleaned["zone_id"] = None
    else:
        zone_id = validator.number("zone_id", "所属片区", required=False, minimum=1)
        if zone_id is not None:
            validator.cleaned["zone_id"] = int(zone_id)
    validator.choice(
        "station_type", "监测点类型",
        choices=tuple(STATION_TYPE_LABELS.keys()),
        required=False,
        default="ambient",
    )
    validator.choice(
        "status", "运行状态",
        choices=tuple(STATION_STATUS_LABELS.keys()),
        required=False,
        default="active",
    )
    validator.number("longitude", "经度", minimum=-180, maximum=180)
    validator.number("latitude", "纬度", minimum=-90, maximum=90)
    validator.date_field("installed_at", "投运日期")
    validator.text("remark", "备注", required=False, max_length=1000)
    cleaned = validator.raise_if_invalid("监测点信息不合法")

    # 片区存在性校验(给出友好的字段级错误)
    if "zone_id" in cleaned:
        from ..models import Zone as _Zone

        zone_id = cleaned["zone_id"]
        if zone_id is not None and db.session.get(_Zone, int(zone_id)) is None:
            validator.fail("zone_id", "所选片区不存在")

    cleaned = validator.raise_if_invalid("监测点信息不合法")

    if partial:
        # 未提交的字段保持原值; 显式提交空值表示清空该字段
        cleaned = {key: value for key, value in cleaned.items() if key in data}
    return cleaned


@bp.get("/", strict_slashes=False)
def list_stations():
    query = station_service.station_query(request.args)
    result = paginate_query(query, lambda station: station.to_dict())
    stats = station_service.stats_map([item["id"] for item in result["items"]])
    managers = zone_service.station_manager_map([item["id"] for item in result["items"]])
    for item in result["items"]:
        item["stats"] = stats.get(item["id"], {})
        item["managers"] = managers.get(item["id"], [])
    result["areas"] = station_service.area_list()
    result["zones"] = zone_service.zone_option_list(include_inactive=True)
    return result


@bp.post("/", strict_slashes=False)
def create_station():
    payload = _validate_station(json_payload())
    station = station_service.create_station(payload)
    return station.to_dict(), 201


@bp.get("/options")
def station_options():
    return {
        "items": station_service.option_list(),
        "areas": station_service.area_list(),
        "zones": zone_service.zone_option_list(include_inactive=True),
    }


@bp.get("/summary")
def station_summary():
    return station_service.metadata_summary()


@bp.get("/<int:station_id>")
def get_station(station_id):
    station = station_service.get_station(station_id)
    payload = station.to_dict(include_stats=True, stats=station_service.detail_stats(station))
    payload["managers"] = zone_service.station_manager_map([station.id]).get(station.id, [])
    payload["zone_history"] = zone_service.station_zone_history(station.id)
    return payload


@bp.put("/<int:station_id>")
def update_station(station_id):
    station = station_service.get_station(station_id)
    payload = _validate_station(json_payload(), partial=True)
    return station_service.update_station(station, payload).to_dict()


@bp.delete("/<int:station_id>")
def delete_station(station_id):
    station = station_service.get_station(station_id)
    removed = station_service.delete_station(station)
    return {"id": station_id, "removed": removed}

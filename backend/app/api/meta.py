"""元数据与健康检查 API."""
from datetime import date, datetime, timedelta

from flask import Blueprint, current_app

from ..domain.constants import (
    DATA_SOURCE_LABELS,
    EXCEEDANCE_LEVEL_LABELS,
    EXCEEDANCE_STATUS_LABELS,
    PERIOD_LABELS,
    PERSON_STATUS_LABELS,
    STATION_STATUS_LABELS,
    STATION_TYPE_LABELS,
    ZONE_ROLE_LABELS,
    ZONE_STATUS_LABELS,
    options_payload,
)
from ..domain.standards import POLLUTANTS
from ..extensions import db
from ..services import exceedance_service, query_service, station_service, zone_service

bp = Blueprint("meta", __name__)


@bp.get("/health")
def health():
    database = "ok"
    try:
        db.session.execute(db.text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - defensive
        database = "error: %s" % exc
    return {
        "status": "ok" if database == "ok" else "degraded",
        "database": database,
        "time": datetime.now().isoformat(timespec="seconds"),
        "timezone": current_app.config["TIMEZONE"],
        "limit_policy": current_app.config["LIMIT_POLICY"],
    }


@bp.get("/pollutants")
def pollutants():
    return {
        "items": list(POLLUTANTS.values()),
        "policy": current_app.config["LIMIT_POLICY"],
        "periods": [{"value": key, "label": label} for key, label in PERIOD_LABELS.items()],
    }


@bp.get("/options")
def options():
    payload = options_payload()
    payload["stations"] = station_service.option_list()
    payload["areas"] = station_service.area_list()
    payload["zones"] = zone_service.zone_option_list(include_inactive=True)
    payload["persons"] = zone_service.person_option_list()
    return payload


@bp.get("/overview")
def overview():
    """首页概览: 台账规模 / 数据量 / 超标待办 / 近 7 日趋势."""
    today = date.today()
    trend_args = {
        "group_by": "day",
        "metric": "count",
        "date_from": (today - timedelta(days=6)).isoformat(),
    }
    trend = query_service.statistics(trend_args)
    filters = query_service.parse_filters({})

    pending_args = {"status": "pending"}
    pending_records = (
        exceedance_service.exceedance_query({**pending_args, "order": "desc"})
        .limit(5)
        .all()
    )
    pending_managers = zone_service.station_manager_map(
        [record.station_id for record in pending_records]
    )
    pending_items = []
    for record in pending_records:
        item = record.to_dict()
        item["managers"] = pending_managers.get(record.station_id, [])
        pending_items.append(item)

    # 片区维度的待办超标排名(供首页下钻入口)
    zone_ranking = exceedance_service.summary({}).get("top_zones", [])
    return {
        "stations": station_service.metadata_summary(),
        "measurements": query_service.summary(filters),
        "exceedances": exceedance_service.summary({}),
        "pending_exceedances": pending_items,
        "zone_ranking": zone_ranking,
        "trend": trend,
        "labels": {
            "station_status": STATION_STATUS_LABELS,
            "station_type": STATION_TYPE_LABELS,
            "exceedance_status": EXCEEDANCE_STATUS_LABELS,
            "exceedance_level": EXCEEDANCE_LEVEL_LABELS,
            "data_source": DATA_SOURCE_LABELS,
            "zone_status": ZONE_STATUS_LABELS,
            "person_status": PERSON_STATUS_LABELS,
            "zone_role": ZONE_ROLE_LABELS,
        },
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }

"""片区与责任人管理接口及历史留痕测试."""
import pytest

from app.extensions import db
from app.models import (
    ResponsiblePerson,
    Station,
    StationZoneHistory,
    Zone,
    ZoneManager,
    ZoneManagerHistory,
)


@pytest.fixture
def zone(app):
    from app.services import zone_service

    return zone_service.create_zone(
        {"code": "ZN-01", "name": "测试片区", "description": "用于测试", "status": "active"}
    )


@pytest.fixture
def person(app):
    from app.services import zone_service

    return zone_service.create_person(
        {
            "name": "赵负责人",
            "employee_no": "E001",
            "phone": "13800000000",
            "department": "运维一部",
            "status": "active",
        }
    )


# ---------------------------------------------------------------------------
# 片区台账
# ---------------------------------------------------------------------------

def test_create_zone(client):
    response = client.post(
        "/api/zones",
        json={"code": "ZN-100", "name": "新区", "description": "新设立片区"},
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["code"] == "ZN-100"
    assert body["status"] == "active"
    assert body["station_count"] == 0


def test_zone_code_unique(client, zone):
    response = client.post("/api/zones", json={"code": "ZN-01", "name": "重复"})
    assert response.status_code == 409


def test_list_zones_with_stats(client, app, zone, station):
    from app.services import zone_service

    zone_service.assign_station_zone(station, zone.id, operator="测试员")
    response = client.get("/api/zones")
    body = response.get_json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["stats"]["station_count"] == 1
    assert item["stats"]["managers"] == []


def test_update_and_delete_empty_zone(client, zone):
    response = client.put("/api/zones/%d" % zone.id, json={"status": "inactive"})
    assert response.status_code == 200
    assert response.get_json()["status"] == "inactive"

    deleted = client.delete("/api/zones/%d" % zone.id)
    assert deleted.status_code == 200
    assert Zone.query.count() == 0


def test_delete_zone_with_stations_rejected(client, zone, station):
    from app.services import zone_service

    zone_service.assign_station_zone(station, zone.id)
    response = client.delete("/api/zones/%d" % zone.id)
    assert response.status_code == 409


def test_zone_detail_contains_history(client, app, zone, station):
    from app.services import zone_service

    zone_service.assign_station_zone(station, zone.id, operator="测试员", note="初次分配")
    body = client.get("/api/zones/%d" % zone.id).get_json()
    assert body["zone"]["code"] == "ZN-01"
    assert len(body["stations"]) == 1
    assert body["stats"]["station_count"] == 1
    assert len(body["station_history"]) == 1
    assert body["station_history"][0]["reason"] == "assign"
    assert body["station_history"][0]["operator"] == "测试员"


# ---------------------------------------------------------------------------
# 责任人台账与任职
# ---------------------------------------------------------------------------

def test_create_person_and_listing(client, person):
    response = client.get("/api/persons")
    assert response.status_code == 200
    body = response.get_json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "赵负责人"
    assert body["items"][0]["zones"] == []


def test_person_employee_no_unique(client, person):
    response = client.post(
        "/api/persons", json={"name": "另一个人", "employee_no": "E001"}
    )
    assert response.status_code == 409


def test_add_change_remove_manager_writes_history(client, zone, person):
    # 加入
    add = client.post(
        "/api/zones/%d/managers" % zone.id,
        json={"person_id": person.id, "role": "manager", "operator": "管理员"},
    )
    assert add.status_code == 201
    managers = add.get_json()["managers"]
    assert managers[0]["person"]["name"] == "赵负责人"
    assert ZoneManager.query.count() == 1
    assert ZoneManagerHistory.query.filter_by(change_type="person_added").count() == 1

    # 调整角色
    change = client.put(
        "/api/zones/%d/managers/%d" % (zone.id, person.id),
        json={"role": "supervisor", "operator": "管理员"},
    )
    assert change.status_code == 200
    assert change.get_json()["managers"][0]["role"] == "supervisor"
    role_history = ZoneManagerHistory.query.filter_by(change_type="role_changed").one()
    assert role_history.previous_role == "manager"
    assert role_history.role == "supervisor"

    # 移除
    remove = client.delete(
        "/api/zones/%d/managers/%d?operator=%s" % (zone.id, person.id, "管理员")
    )
    assert remove.status_code == 200
    assert ZoneManager.query.count() == 0
    assert ZoneManagerHistory.query.filter_by(change_type="person_removed").count() == 1
    # 历史流水共 3 条, 且永不删除
    assert ZoneManagerHistory.query.count() == 3


def test_duplicate_manager_assignment_rejected(client, zone, person):
    client.post(
        "/api/zones/%d/managers" % zone.id,
        json={"person_id": person.id, "role": "manager"},
    )
    response = client.post(
        "/api/zones/%d/managers" % zone.id,
        json={"person_id": person.id, "role": "engineer"},
    )
    assert response.status_code == 409


def test_inactive_person_cannot_be_assigned(client, zone, person):
    client.put("/api/persons/%d" % person.id, json={"status": "inactive"})
    response = client.post(
        "/api/zones/%d/managers" % zone.id,
        json={"person_id": person.id, "role": "manager"},
    )
    assert response.status_code == 422


def test_person_with_history_cannot_be_deleted(client, zone, person):
    client.post(
        "/api/zones/%d/managers" % zone.id,
        json={"person_id": person.id, "role": "manager"},
    )
    client.delete("/api/zones/%d/managers/%d" % (zone.id, person.id))
    response = client.delete("/api/persons/%d" % person.id)
    assert response.status_code == 409
    # 改为离岗后仍保留档案
    updated = client.put("/api/persons/%d" % person.id, json={"status": "inactive"})
    assert updated.status_code == 200
    assert ResponsiblePerson.query.count() == 1


# ---------------------------------------------------------------------------
# 点位归属调整与历史
# ---------------------------------------------------------------------------

def test_station_create_with_zone_writes_history(client, app, zone):
    response = client.post(
        "/api/stations/",
        json={
            "code": "SZ-ZN-001",
            "name": "片区内点位",
            "area": "测试区",
            "zone_id": zone.id,
        },
    )
    assert response.status_code == 201
    station_id = response.get_json()["id"]
    history = StationZoneHistory.query.filter_by(station_id=station_id).all()
    assert len(history) == 1
    assert history[0].reason == "assign"
    assert history[0].zone_name == "测试片区"


def test_station_zone_transfer_records_history(client, app, station, zone):
    from app.services import zone_service

    second = zone_service.create_zone({"code": "ZN-02", "name": "第二片区"})
    zone_service.assign_station_zone(station, zone.id, operator="张三")
    zone_service.assign_station_zone(station, second.id, operator="李四", note="区划调整")

    history = StationZoneHistory.query.order_by(StationZoneHistory.id.asc()).all()
    assert [item.reason for item in history] == ["assign", "transfer"]
    latest = history[-1].to_dict()
    assert latest["previous_zone_name"] == "测试片区"
    assert latest["zone_name"] == "第二片区"
    assert latest["operator"] == "李四"


def test_assign_same_zone_rejected(client, zone, station):
    from app.services import zone_service

    zone_service.assign_station_zone(station, zone.id)
    with pytest.raises(Exception):
        zone_service.assign_station_zone(station, zone.id)


def test_batch_assign_stations(client, app, zone, station, second_station):
    response = client.post(
        "/api/zones/assign-stations",
        json={"station_ids": [station.id, second_station.id], "zone_id": zone.id,
              "operator": "批量操作"},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["changed"] == 2
    assert db.session.get(Station, station.id).zone_id == zone.id
    assert StationZoneHistory.query.count() == 2


def test_station_detail_includes_managers_and_history(client, zone, person, station):
    client.post(
        "/api/zones/%d/managers" % zone.id,
        json={"person_id": person.id, "role": "manager"},
    )
    client.put("/api/stations/%d" % station.id, json={"zone_id": zone.id})
    detail = client.get("/api/stations/%d" % station.id).get_json()
    assert detail["zone_id"] == zone.id
    assert detail["zone_name"] == "测试片区"
    assert detail["managers"][0]["name"] == "赵负责人"
    assert detail["managers"][0]["role_label"] == "片区负责人"
    assert len(detail["zone_history"]) == 1


def test_station_zone_history_endpoint(client, zone, station):
    client.put("/api/stations/%d" % station.id, json={"zone_id": zone.id})
    response = client.get("/api/stations/%d/zone-history" % station.id)
    assert response.status_code == 200
    assert len(response.get_json()["items"]) == 1


# ---------------------------------------------------------------------------
# 查询 / 超标 / 统计按片区过滤与汇总
# ---------------------------------------------------------------------------

def _setup_zoned_station_with_exceedance(client, station, zone, entry_payload):
    client.post(
        "/api/zones/%d/managers" % zone.id,
        json={"person_id": _create_person_id(client, "钱运维"), "role": "engineer"},
    )
    client.put("/api/stations/%d" % station.id, json={"zone_id": zone.id})
    client.post("/api/measurements/entries", json=entry_payload(station.id))


def _create_person_id(client, name):
    response = client.post("/api/persons", json={"name": name, "employee_no": name})
    return response.get_json()["id"]


def test_station_list_filter_by_zone_and_none(client, zone, station, second_station):
    client.put("/api/stations/%d" % station.id, json={"zone_id": zone.id})
    zoned = client.get("/api/stations?zone_id=%d" % zone.id).get_json()
    assert zoned["total"] == 1
    assert zoned["items"][0]["zone_name"] == "测试片区"

    none_items = client.get("/api/stations?zone_id=none").get_json()
    assert none_items["total"] == 1
    assert none_items["items"][0]["id"] == second_station.id


def test_query_measurements_filter_by_zone(client, zone, station, second_station, entry_payload):
    _setup_zoned_station_with_exceedance(client, station, zone, entry_payload)
    body = client.get("/api/query/measurements?zone_id=%d" % zone.id).get_json()
    assert body["total"] == 3
    assert all(item["station"]["zone_id"] == zone.id for item in body["items"])
    assert body["items"][0]["managers"][0]["name"] == "钱运维"

    none_body = client.get("/api/query/measurements?zone_id=none").get_json()
    assert none_body["total"] == 0


def test_statistics_group_by_zone(client, zone, station, entry_payload):
    _setup_zoned_station_with_exceedance(client, station, zone, entry_payload)
    body = client.get("/api/query/statistics?group_by=zone&metric=count").get_json()
    assert body["group_by"] == "zone"
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["zone_id"] == zone.id
    assert item["label"] == "测试片区"
    assert item["count"] == 3
    assert item["exceeded_count"] == 1
    assert item["station_count"] == 1


def test_exceedances_filter_by_zone_and_top_zones(client, zone, station, entry_payload):
    _setup_zoned_station_with_exceedance(client, station, zone, entry_payload)
    listing = client.get("/api/exceedances?zone_id=%d" % zone.id).get_json()
    assert listing["total"] == 1
    assert listing["items"][0]["zone_name"] == "测试片区"
    assert listing["items"][0]["managers"]

    summary = client.get("/api/exceedances/summary").get_json()
    assert summary["top_zones"][0]["zone_id"] == zone.id
    assert summary["top_zones"][0]["pending_count"] == 1


def test_exceedances_filter_by_manager(client, zone, person, station, entry_payload):
    client.post(
        "/api/zones/%d/managers" % zone.id,
        json={"person_id": person.id, "role": "manager"},
    )
    client.put("/api/stations/%d" % station.id, json={"zone_id": zone.id})
    client.post("/api/measurements/entries", json=entry_payload(station.id))
    body = client.get("/api/exceedances?manager_id=%d" % person.id).get_json()
    assert body["total"] == 1
    assert client.get("/api/exceedances?manager_id=99999").get_json()["total"] == 0


def test_export_csv_contains_zone_and_manager_columns(client, zone, person, station, entry_payload):
    client.post(
        "/api/zones/%d/managers" % zone.id,
        json={"person_id": person.id, "role": "manager"},
    )
    client.put("/api/stations/%d" % station.id, json={"zone_id": zone.id})
    client.post("/api/measurements/entries", json=entry_payload(station.id))
    response = client.get("/api/query/export")
    assert response.status_code == 200
    text = response.data.decode("utf-8-sig")
    assert "所属片区" in text
    assert "片区责任人" in text
    assert "测试片区" in text
    assert "赵负责人" in text


def test_zone_options_and_meta_options(client, zone, person):
    client.post(
        "/api/zones/%d/managers" % zone.id,
        json={"person_id": person.id, "role": "manager"},
    )
    zones = client.get("/api/zones/options").get_json()
    assert zones["items"][0]["name"] == "测试片区"
    persons = client.get("/api/persons/options").get_json()
    assert persons["items"][0]["name"] == "赵负责人"
    meta = client.get("/api/meta/options").get_json()
    assert any(item["id"] == zone.id for item in meta["zones"])
    assert any(item["id"] == person.id for item in meta["persons"])


def test_overview_contains_zone_ranking(client, zone, station, entry_payload):
    _setup_zoned_station_with_exceedance(client, station, zone, entry_payload)
    body = client.get("/api/meta/overview").get_json()
    ranking = body["zone_ranking"]
    assert ranking
    assert ranking[0]["zone_id"] == zone.id
    assert body["stations"]["zone_count"] == 1
    assert body["stations"]["zoned_station_count"] == 1
    assert body["stations"]["unzoned_station_count"] == 0

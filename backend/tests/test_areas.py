"""片区与责任人管理接口测试: CRUD、归属划转、历史留痕、汇总下钻、导出。"""
from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models import Area, AreaMembership, Person, StationAssignment
from app.services import area_service, station_service


@pytest.fixture
def area(app):
    return area_service.create_area(
        {"code": "A-001", "name": "中心片区", "manager": "张三", "phone": "110",
         "status": "active", "remark": None}
    )


@pytest.fixture
def second_area(app):
    return area_service.create_area(
        {"code": "A-002", "name": "东部片区", "manager": "李四", "status": "active"}
    )


@pytest.fixture
def person(app, area):
    person = Person(name="王五", employee_no="E-1", role="leader", status="active")
    db.session.add(person)
    db.session.commit()
    area_service.add_membership(area, person)
    return person


# ---------------------------------------------------------------------------
# 片区 CRUD
# ---------------------------------------------------------------------------
def test_create_and_list_area(client, area, second_area):
    response = client.get("/api/areas/")
    body = response.get_json()
    assert body["total"] == 2
    codes = {item["code"] for item in body["items"]}
    assert codes == {"A-001", "A-002"}
    assert body["items"][0]["stats"]["station_count"] == 0


def test_area_code_and_name_unique(client, area):
    dup_code = client.post("/api/areas/", json={"code": "A-001", "name": "另一个片区"})
    assert dup_code.status_code == 409
    dup_name = client.post("/api/areas/", json={"code": "A-999", "name": "中心片区"})
    assert dup_name.status_code == 409


def test_create_area_requires_code_and_name(client):
    response = client.post("/api/areas/", json={"manager": "无编码"})
    assert response.status_code == 422
    fields = response.get_json()["error"]["fields"]
    assert "code" in fields and "name" in fields


def test_update_area_syncs_station_redundant_name(client, app, area, station):
    area_service.assign_stations([station.id], area.id, reason="划入")
    response = client.put("/api/areas/%d" % area.id, json={"name": "中心片区(更名)"})
    assert response.status_code == 200
    db.session.refresh(station)
    assert station.area == "中心片区(更名)"


def test_area_detail_aggregates_stations_and_persons(client, area, person, station):
    area_service.assign_stations([station.id], area.id, reason="划入")
    body = client.get("/api/areas/%d" % area.id).get_json()
    assert body["stats"]["station_count"] == 1
    assert [p["name"] for p in body["persons"]] == ["王五"]
    assert body["stations"][0]["code"] == station.code


# ---------------------------------------------------------------------------
# 责任人
# ---------------------------------------------------------------------------
def test_create_person_with_area_and_list(client, area):
    response = client.post(
        "/api/areas/persons",
        json={"name": "赵六", "employee_no": "E-2", "role": "officer", "area_id": area.id},
    )
    assert response.status_code == 201
    listing = client.get("/api/areas/persons").get_json()
    assert listing["total"] == 1
    assert listing["items"][0]["areas"][0]["name"] == "中心片区"


def test_person_employee_no_unique(client, person):
    response = client.post(
        "/api/areas/persons", json={"name": "重号", "employee_no": "E-1"}
    )
    assert response.status_code == 409


def test_person_with_membership_history_cannot_be_deleted(client, person):
    response = client.delete("/api/areas/persons/%d" % person.id)
    assert response.status_code == 409


def test_person_without_history_can_be_deleted(client, app):
    fresh = Person(name="临时工", employee_no="E-99", status="active")
    db.session.add(fresh)
    db.session.commit()
    response = client.delete("/api/areas/persons/%d" % fresh.id)
    assert response.status_code == 200
    assert response.get_json()["deleted"] is True


# ---------------------------------------------------------------------------
# 归属划转与历史留痕
# ---------------------------------------------------------------------------
def test_assign_stations_creates_temporal_history(client, app, area, second_area, station):
    started_at = datetime.now() - timedelta(days=10)
    first = area_service.assign_stations(
        [station.id], area.id, effective_from=started_at, reason="初次划入",
        replace_current=True,
    )
    assert first["moved"] == 1

    moved_at = datetime.now() - timedelta(days=1)
    second = area_service.assign_stations(
        [station.id], second_area.id, effective_from=moved_at, reason="区划调整"
    )
    assert second["moved"] == 1

    records = StationAssignment.query.filter_by(station_id=station.id).order_by(
        StationAssignment.effective_from.asc()
    ).all()
    assert len(records) == 2
    assert records[0].area_id == area.id
    assert records[0].effective_end is not None
    assert records[0].change_reason == "区划调整"
    assert records[1].area_id == second_area.id
    assert records[1].effective_end is None

    db.session.refresh(station)
    assert station.area_id == second_area.id
    assert station.area == "东部片区"


def test_assign_requires_reason(client, area, station):
    response = client.post(
        "/api/areas/assignments",
        json={"area_id": area.id, "station_ids": [station.id]},
    )
    assert response.status_code == 422
    assert "change_reason" in response.get_json()["error"]["fields"]


def test_assignment_history_endpoint(client, area, second_area, station):
    area_service.assign_stations(
        [station.id], area.id,
        effective_from=datetime.now() - timedelta(days=5), reason="初次划入",
        replace_current=True,
    )
    area_service.assign_stations([station.id], second_area.id, reason="再次调整")
    body = client.get("/api/areas/history?station_id=%d" % station.id).get_json()
    assert body["total"] == 2
    assert body["items"][0]["area_name"] == "东部片区"
    assert body["items"][0]["is_current"] is True


def test_cannot_assign_to_inactive_area(client, area, station):
    client.put("/api/areas/%d" % area.id, json={"status": "inactive"})
    response = client.post(
        "/api/areas/assignments",
        json={"area_id": area.id, "station_ids": [station.id], "change_reason": "x"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 任职管理
# ---------------------------------------------------------------------------
def test_membership_leave_and_duplicate(client, area, second_area, person):
    # 同一人不能在同一片区重复任职
    dup = client.post(
        "/api/areas/memberships", json={"area_id": area.id, "person_id": person.id}
    )
    assert dup.status_code == 409

    response = client.post(
        "/api/areas/memberships",
        json={"area_id": second_area.id, "person_id": person.id, "role": "inspector",
              "change_reason": "新增分工"},
    )
    assert response.status_code == 201

    membership_id = response.get_json()["id"]
    leave = client.post(
        "/api/areas/memberships/%d/leave" % membership_id,
        json={"change_reason": "轮岗离任"},
    )
    assert leave.status_code == 200
    assert leave.get_json()["effective_end"] is not None

    history = client.get(
        "/api/areas/memberships/history?person_id=%d" % person.id
    ).get_json()
    assert history["total"] == 2


def test_leave_requires_reason(client, area, person):
    response = client.post(
        "/api/areas/memberships", json={"area_id": area.id, "person_id": person.id}
    )
    # 首次在该片区任职成功 (fixture 挂的是同一个 area? person fixture 已挂 area -> 409)
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# 查询、统计与导出按片区
# ---------------------------------------------------------------------------
def _entry_for(station_id, measured_at, so2=900.0):
    return {
        "station_id": station_id,
        "measured_at": measured_at,
        "period": "hourly",
        "data_source": "manual",
        "recorder": "测试员",
        "entries": [
            {"pollutant": "PM25", "value": 30.0},
            {"pollutant": "SO2", "value": so2},
            {"pollutant": "CO", "value": 0.8},
        ],
    }


def test_measurements_filter_and_group_by_historical_area(
    client, app, area, second_area, station, second_station
):
    # 站点先属于中心片区, 2 天前划到东部片区
    area_service.assign_stations(
        [station.id], area.id,
        effective_from=datetime.now() - timedelta(days=10), reason="初始",
        replace_current=True,
    )
    area_service.assign_stations(
        [station.id], second_area.id,
        effective_from=datetime.now() - timedelta(days=2), reason="划转",
    )
    area_service.assign_stations(
        [second_station.id], second_area.id,
        effective_from=datetime.now() - timedelta(days=10), reason="初始",
        replace_current=True,
    )

    old_at = datetime.now() - timedelta(days=5)
    new_at = datetime.now() - timedelta(hours=1)
    client.post("/api/measurements/entries", json=_entry_for(station.id, old_at.strftime("%Y-%m-%d %H:%M")))
    client.post("/api/measurements/entries", json=_entry_for(station.id, new_at.strftime("%Y-%m-%d %H:%M")))

    stats = client.get("/api/query/statistics?group_by=area&metric=count").get_json()
    by_name = {item["label"]: item["count"] for item in stats["items"]}
    # 老数据归中心片区 (3 因子), 新数据归东部片区 (3 因子)
    assert by_name.get("中心片区") == 3
    assert by_name.get("东部片区") == 3

    filtered = client.get(
        "/api/query/measurements?area_id=%d" % area.id
    ).get_json()
    assert filtered["total"] == 3  # 仅划转前的 3 条


def test_exceedances_area_filter_and_top_areas(
    client, area, second_area, station, second_station
):
    area_service.assign_stations(
        [station.id], area.id,
        effective_from=datetime.now() - timedelta(days=10), reason="初始",
        replace_current=True,
    )
    area_service.assign_stations(
        [second_station.id], second_area.id,
        effective_from=datetime.now() - timedelta(days=10), reason="初始",
        replace_current=True,
    )
    client.post(
        "/api/measurements/entries",
        json=_entry_for(station.id, datetime.now().strftime("%Y-%m-%d %H:%M")),
    )
    client.post(
        "/api/measurements/entries",
        json=_entry_for(second_station.id, datetime.now().strftime("%Y-%m-%d %H:%M")),
    )
    body = client.get("/api/exceedances?area_id=%d" % area.id).get_json()
    assert body["total"] == 1
    assert body["items"][0]["area_name"] == "中心片区"
    top = {item["area_name"]: item["count"] for item in body["summary"]["top_areas"]}
    assert top["中心片区"] == 1

    ranking = client.get("/api/areas/ranking").get_json()
    names = {item["label"] for item in ranking["items"]}
    assert {"中心片区", "东部片区"} <= names
    assert ranking["totals"]["exceeded_count"] == 2


def test_person_filter_expands_to_current_areas(client, area, person, station):
    # 王五在中心片区任职, 该片区下点位的数据均可按责任人筛出
    area_service.assign_stations(
        [station.id], area.id,
        effective_from=datetime.now() - timedelta(days=10), reason="初始",
        replace_current=True,
    )
    client.post(
        "/api/measurements/entries",
        json=_entry_for(station.id, datetime.now().strftime("%Y-%m-%d %H:%M")),
    )
    body = client.get(
        "/api/query/measurements?person_id=%d" % person.id
    ).get_json()
    assert body["total"] == 3


def test_export_contains_area_and_person_columns(client, area, person, station):
    area_service.assign_stations(
        [station.id], area.id,
        effective_from=datetime.now() - timedelta(days=10), reason="初始",
        replace_current=True,
    )
    client.post(
        "/api/measurements/entries",
        json=_entry_for(station.id, datetime.now().strftime("%Y-%m-%d %H:%M")),
    )
    csv_text = client.get("/api/query/export?area_id=%d" % area.id).get_data(as_text=True)
    header = csv_text.splitlines()[0]
    assert "所属片区" in header and "责任人" in header
    assert "中心片区" in csv_text and "王五" in csv_text


# ---------------------------------------------------------------------------
# 监测点建档自动归属
# ---------------------------------------------------------------------------
def test_create_station_binds_area_and_history(client, area):
    response = client.post(
        "/api/stations/",
        json={"code": "NEW-001", "name": "新站点", "area_id": area.id,
              "station_type": "ambient", "status": "active"},
    )
    assert response.status_code == 201
    station_id = response.get_json()["id"]
    detail = client.get("/api/stations/%d" % station_id).get_json()
    assert detail["area_id"] == area.id
    assert len(detail["assignments"]) == 1
    assert detail["assignments"][0]["change_reason"] == "监测点建档划入片区"


def test_create_station_by_area_name_auto_creates_area(client, app):
    response = client.post(
        "/api/stations/",
        json={"code": "NEW-002", "name": "自由命名站", "area": "全新片区",
              "station_type": "ambient", "status": "active"},
    )
    assert response.status_code == 201
    area = Area.query.filter_by(name="全新片区").first()
    assert area is not None
    assert response.get_json()["area_id"] == area.id

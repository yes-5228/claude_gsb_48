"""Lightweight startup schema migration tests (old DB without stations.zone_id)."""
from sqlalchemy import inspect, text

from app.extensions import db
from app.migrations import ensure_schema


def _legacy_stations_ddl():
    """Full stations table shape as it existed before the zone feature."""
    return (
        "CREATE TABLE stations ("
        "id INTEGER NOT NULL PRIMARY KEY, "
        "code VARCHAR(32) NOT NULL UNIQUE, "
        "name VARCHAR(120) NOT NULL, "
        "area VARCHAR(64) NOT NULL, "
        "address VARCHAR(200), "
        "station_type VARCHAR(32) NOT NULL, "
        "status VARCHAR(32) NOT NULL, "
        "longitude FLOAT, latitude FLOAT, installed_at DATE, "
        "remark TEXT, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)"
    )


def test_ensure_schema_adds_zone_id_to_legacy_stations(app):
    # Simulate a legacy database: create the current schema (so all unrelated
    # tables exist), then replace stations with its pre-zone-feature shape and
    # keep a data row.
    db.drop_all()
    db.create_all()
    with db.engine.begin() as conn:
        conn.execute(text("DROP TABLE stations"))
        conn.execute(text(_legacy_stations_ddl()))
        conn.execute(
            text(
                "INSERT INTO stations (id, code, name, area, station_type, status, created_at, updated_at) "
                "VALUES (1, 'OLD-001', '老站点', '老城区', 'ambient', 'active', '2020-01-01 00:00:00', '2020-01-01 00:00:00')"
            )
        )

    ensure_schema()

    columns = {column["name"] for column in inspect(db.engine).get_columns("stations")}
    assert "zone_id" in columns
    tables = inspect(db.engine).get_table_names()
    assert {"zones", "responsible_persons", "zone_managers",
            "station_zone_histories", "zone_manager_histories"} <= set(tables)

    # Legacy row survives and is reported as unassigned
    from app.models import Station

    station = db.session.get(Station, 1)
    assert station.code == "OLD-001"
    assert station.zone_id is None


def test_ensure_schema_is_idempotent(app):
    db.drop_all()
    db.create_all()
    ensure_schema()
    ensure_schema()  # running again must not error
    columns = {column["name"] for column in inspect(db.engine).get_columns("stations")}
    assert "zone_id" in columns

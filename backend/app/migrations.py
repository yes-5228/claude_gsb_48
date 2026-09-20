"""Lightweight idempotent schema sync for deployments on pre-existing databases.

``db.create_all()`` creates missing tables but never adds columns to an existing
table.  When the zone/person feature ships, older SQLite/PostgreSQL databases
already contain a ``stations`` table without ``zone_id``; inspecting and
issuing a portable ``ALTER TABLE ... ADD COLUMN`` keeps those installs working
without requiring a migration framework.

The function is deliberately small and idempotent: every check is based on the
live database inspector and it is safe to run on every startup.
"""
from sqlalchemy import inspect, text

from .extensions import db

# column -> column DDL fragment for the portable ADD COLUMN
_STATION_COLUMNS = {
    "zone_id": "INTEGER REFERENCES zones (id) ON DELETE SET NULL",
}


def ensure_schema():
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())

    # New tables (zones, responsible_persons, zone_managers, histories) are
    # created normally by db.create_all() afterwards; ensure order here so the
    # stations.zone_id foreign key has a target table.
    db.create_all()

    if "stations" in tables:
        existing_columns = {column["name"] for column in inspector.get_columns("stations")}
        for column, ddl in _STATION_COLUMNS.items():
            if column not in existing_columns:
                db.session.execute(text("ALTER TABLE stations ADD COLUMN %s %s" % (column, ddl)))
                db.session.commit()

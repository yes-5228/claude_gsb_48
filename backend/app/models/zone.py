"""监测点片区 / 责任人及历史留痕模型.

片区(Zone)下挂多个监测点(Station)与多个责任人(ResponsiblePerson, 通过
ZoneManager 关联并区分角色). 点位归属与责任人任职的每一次变动都会向对应的
历史表追加一条快照记录(不修改旧记录), 用于长期追溯.
"""
from ..domain.constants import (
    CHANGE_REASON_LABELS,
    CHANGE_TYPE_LABELS,
    PERSON_STATUS_LABELS,
    ZONE_ROLE_LABELS,
    ZONE_STATUS_LABELS,
    label_of,
)
from ..extensions import db
from .base import TimestampMixin, iso, iso_date


class Zone(TimestampMixin, db.Model):
    __tablename__ = "zones"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(500))
    status = db.Column(db.String(16), nullable=False, default="active", index=True)

    stations = db.relationship(
        "Station",
        back_populates="zone",
        passive_deletes=True,
    )
    managers = db.relationship(
        "ZoneManager",
        back_populates="zone",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def active_managers(self):
        return [item for item in self.managers if item.person and item.person.status == "active"]

    def to_dict(self, include_managers=False):
        payload = {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "status_label": label_of(ZONE_STATUS_LABELS, self.status),
            "station_count": len(self.stations),
            "created_at": iso(self.created_at),
            "updated_at": iso(self.updated_at),
        }
        if include_managers:
            payload["managers"] = [item.to_dict(include_person=True) for item in self.managers]
        return payload

    def to_option(self):
        return {"id": self.id, "code": self.code, "name": self.name, "status": self.status}

    def __repr__(self):
        return "<Zone %s %s>" % (self.code, self.name)


class ResponsiblePerson(TimestampMixin, db.Model):
    __tablename__ = "responsible_persons"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, index=True)
    employee_no = db.Column(db.String(32), unique=True)
    phone = db.Column(db.String(32))
    department = db.Column(db.String(120))
    title = db.Column(db.String(64))
    status = db.Column(db.String(16), nullable=False, default="active", index=True)
    remark = db.Column(db.String(500))

    assignments = db.relationship(
        "ZoneManager",
        back_populates="person",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def to_dict(self, include_zones=False):
        payload = {
            "id": self.id,
            "name": self.name,
            "employee_no": self.employee_no,
            "phone": self.phone,
            "department": self.department,
            "title": self.title,
            "status": self.status,
            "status_label": label_of(PERSON_STATUS_LABELS, self.status),
            "remark": self.remark,
            "created_at": iso(self.created_at),
            "updated_at": iso(self.updated_at),
        }
        if include_zones:
            payload["zones"] = [
                item.to_dict(include_zone=True) for item in self.assignments if item.zone
            ]
        return payload

    def to_option(self):
        return {
            "id": self.id,
            "name": self.name,
            "employee_no": self.employee_no,
            "department": self.department,
            "title": self.title,
            "status": self.status,
        }

    def __repr__(self):
        return "<ResponsiblePerson %s>" % self.name


class ZoneManager(db.Model):
    """责任人与片区的多对多关联(一个人可负责多个片区, 角色可不同)."""

    __tablename__ = "zone_managers"
    __table_args__ = (
        db.UniqueConstraint("zone_id", "person_id", name="uq_zone_person"),
    )

    id = db.Column(db.Integer, primary_key=True)
    zone_id = db.Column(
        db.Integer, db.ForeignKey("zones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    person_id = db.Column(
        db.Integer,
        db.ForeignKey("responsible_persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = db.Column(db.String(32), nullable=False, default="manager")
    assigned_at = db.Column(db.DateTime, nullable=False, default=db.func.now())

    zone = db.relationship("Zone", back_populates="managers")
    person = db.relationship("ResponsiblePerson", back_populates="assignments")

    def to_dict(self, include_person=False, include_zone=False):
        payload = {
            "id": self.id,
            "zone_id": self.zone_id,
            "person_id": self.person_id,
            "role": self.role,
            "role_label": label_of(ZONE_ROLE_LABELS, self.role),
            "assigned_at": iso(self.assigned_at),
        }
        if include_person and self.person:
            payload["person"] = self.person.to_option() | {
                "phone": self.person.phone,
                "status_label": label_of(PERSON_STATUS_LABELS, self.person.status),
            }
        if include_zone and self.zone:
            payload["zone"] = self.zone.to_option()
        return payload


class StationZoneHistory(db.Model):
    """监测点归属片区的变更流水(只追加, 不修改)."""

    __tablename__ = "station_zone_histories"

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(
        db.Integer, db.ForeignKey("stations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    zone_id = db.Column(
        db.Integer, db.ForeignKey("zones.id", ondelete="CASCADE"), nullable=True, index=True
    )
    previous_zone_id = db.Column(
        db.Integer, db.ForeignKey("zones.id", ondelete="CASCADE"), nullable=True
    )
    reason = db.Column(db.String(16), nullable=False, default="assign")
    changed_at = db.Column(db.DateTime, nullable=False, default=db.func.now(), index=True)
    operator = db.Column(db.String(64))
    note = db.Column(db.String(500))
    # 变更发生时的名称快照, 片区后续改名/删除后历史仍可读
    station_code = db.Column(db.String(32))
    station_name = db.Column(db.String(120))
    zone_name = db.Column(db.String(120))
    previous_zone_name = db.Column(db.String(120))

    def to_dict(self):
        return {
            "id": self.id,
            "station_id": self.station_id,
            "zone_id": self.zone_id,
            "previous_zone_id": self.previous_zone_id,
            "reason": self.reason,
            "reason_label": label_of(CHANGE_REASON_LABELS, self.reason),
            "changed_at": iso(self.changed_at),
            "operator": self.operator,
            "note": self.note,
            "station_code": self.station_code,
            "station_name": self.station_name,
            "zone_name": self.zone_name,
            "previous_zone_name": self.previous_zone_name,
        }


class ZoneManagerHistory(db.Model):
    """片区责任人任职变动流水(加入 / 移除 / 角色调整, 只追加)."""

    __tablename__ = "zone_manager_histories"

    id = db.Column(db.Integer, primary_key=True)
    zone_id = db.Column(
        db.Integer, db.ForeignKey("zones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    person_id = db.Column(
        db.Integer,
        db.ForeignKey("responsible_persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    change_type = db.Column(db.String(16), nullable=False)
    role = db.Column(db.String(32))
    previous_role = db.Column(db.String(32))
    changed_at = db.Column(db.DateTime, nullable=False, default=db.func.now(), index=True)
    operator = db.Column(db.String(64))
    note = db.Column(db.String(500))
    # 名称快照
    zone_name = db.Column(db.String(120))
    person_name = db.Column(db.String(64))
    person_employee_no = db.Column(db.String(32))

    def to_dict(self):
        return {
            "id": self.id,
            "zone_id": self.zone_id,
            "person_id": self.person_id,
            "change_type": self.change_type,
            "change_type_label": label_of(CHANGE_TYPE_LABELS, self.change_type),
            "role": self.role,
            "role_label": label_of(ZONE_ROLE_LABELS, self.role) if self.role else None,
            "previous_role": self.previous_role,
            "previous_role_label": (
                label_of(ZONE_ROLE_LABELS, self.previous_role) if self.previous_role else None
            ),
            "changed_at": iso(self.changed_at),
            "operator": self.operator,
            "note": self.note,
            "zone_name": self.zone_name,
            "person_name": self.person_name,
            "person_employee_no": self.person_employee_no,
        }

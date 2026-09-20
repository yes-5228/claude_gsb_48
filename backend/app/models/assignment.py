"""监测点-片区归属历史 (时间分段表).

人员或归属发生变动时不覆盖旧记录: 旧记录写入 ``effective_end`` 并留痕变更原因,
新记录从生效时刻起算。任意时刻点监测点归属的片区都可以通过
``effective_from <= t < effective_end`` 还原, 满足历史数据按当时片区汇总的要求。
"""
from datetime import datetime

from ..extensions import db
from .base import iso


class StationAssignment(db.Model):
    __tablename__ = "station_assignments"
    __table_args__ = (
        db.Index("ix_station_assignment_active", "station_id", "effective_end"),
    )

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(
        db.Integer, db.ForeignKey("stations.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    area_id = db.Column(
        db.Integer, db.ForeignKey("areas.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    effective_from = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True)
    effective_end = db.Column(db.DateTime)  # NULL = 当前生效
    change_reason = db.Column(db.String(200))
    changed_by = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    station = db.relationship("Station", back_populates="assignments")
    area = db.relationship("Area", back_populates="assignments")

    def to_dict(self):
        return {
            "id": self.id,
            "station_id": self.station_id,
            "station_name": self.station.name if self.station else None,
            "station_code": self.station.code if self.station else None,
            "area_id": self.area_id,
            "area_name": self.area.name if self.area else None,
            "area_code": self.area.code if self.area else None,
            "effective_from": iso(self.effective_from),
            "effective_end": iso(self.effective_end),
            "is_current": self.effective_end is None,
            "change_reason": self.change_reason,
            "changed_by": self.changed_by,
            "created_at": iso(self.created_at),
        }

    def __repr__(self):
        return "<StationAssignment station=%s area=%s %s>" % (
            self.station_id, self.area_id, self.effective_from,
        )


class AreaMembership(db.Model):
    """责任人-片区任职历史, 同样按时间分段保留。"""

    __tablename__ = "area_memberships"
    __table_args__ = (
        db.Index("ix_area_membership_active", "area_id", "person_id", "effective_end"),
    )

    id = db.Column(db.Integer, primary_key=True)
    area_id = db.Column(
        db.Integer, db.ForeignKey("areas.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    person_id = db.Column(
        db.Integer, db.ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    role = db.Column(db.String(32))
    effective_from = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True)
    effective_end = db.Column(db.DateTime)
    change_reason = db.Column(db.String(200))
    changed_by = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    area = db.relationship("Area", back_populates="memberships")
    person = db.relationship("Person", back_populates="memberships")

    def to_dict(self):
        return {
            "id": self.id,
            "area_id": self.area_id,
            "area_name": self.area.name if self.area else None,
            "person_id": self.person_id,
            "person_name": self.person.name if self.person else None,
            "employee_no": self.person.employee_no if self.person else None,
            "role": self.role or (self.person.role if self.person else None),
            "role_label": self.role_label,
            "phone": self.person.phone if self.person else None,
            "effective_from": iso(self.effective_from),
            "effective_end": iso(self.effective_end),
            "is_current": self.effective_end is None,
            "change_reason": self.change_reason,
            "changed_by": self.changed_by,
            "created_at": iso(self.created_at),
        }

    @property
    def role_label(self):
        from ..domain.constants import PERSON_ROLE_LABELS

        role = self.role or (self.person.role if self.person else None)
        return PERSON_ROLE_LABELS.get(role, role)

    def __repr__(self):
        return "<AreaMembership area=%s person=%s>" % (self.area_id, self.person_id)

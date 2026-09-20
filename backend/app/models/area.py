"""监测点片区 (网格). 片区下挂多个监测点与责任人."""
from ..domain.constants import AREA_STATUS_LABELS
from ..extensions import db
from .base import TimestampMixin, iso


class Area(TimestampMixin, db.Model):
    __tablename__ = "areas"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), unique=True, nullable=False, index=True)
    manager = db.Column(db.String(64))
    phone = db.Column(db.String(32))
    status = db.Column(db.String(16), nullable=False, default="active", index=True)
    remark = db.Column(db.Text)

    stations = db.relationship("Station", back_populates="area_ref")
    assignments = db.relationship(
        "StationAssignment",
        back_populates="area",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    memberships = db.relationship(
        "AreaMembership",
        back_populates="area",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def to_dict(self, include_counts=False, stats=None, persons=None):
        payload = {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "manager": self.manager,
            "phone": self.phone,
            "status": self.status,
            "status_label": AREA_STATUS_LABELS.get(self.status, self.status),
            "remark": self.remark,
            "created_at": iso(self.created_at),
            "updated_at": iso(self.updated_at),
        }
        if include_counts:
            payload["stats"] = stats or {}
            payload["persons"] = persons or []
        return payload

    def to_option(self):
        return {"id": self.id, "code": self.code, "name": self.name, "status": self.status}

    def __repr__(self):
        return "<Area %s %s>" % (self.code, self.name)

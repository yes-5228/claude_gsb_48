"""监测点台账."""
from ..domain.constants import STATION_STATUS_LABELS, STATION_TYPE_LABELS, label_of
from ..extensions import db
from .base import TimestampMixin, iso, iso_date


class Station(TimestampMixin, db.Model):
    __tablename__ = "stations"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    area_id = db.Column(
        db.Integer, db.ForeignKey("areas.id", ondelete="SET NULL"), index=True
    )
    area = db.Column(db.String(64), nullable=False)
    address = db.Column(db.String(200))
    station_type = db.Column(db.String(32), nullable=False, default="ambient")
    status = db.Column(db.String(32), nullable=False, default="active", index=True)
    longitude = db.Column(db.Float)
    latitude = db.Column(db.Float)
    installed_at = db.Column(db.Date)
    remark = db.Column(db.Text)

    measurements = db.relationship(
        "Measurement",
        back_populates="station",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    exceedances = db.relationship(
        "Exceedance",
        back_populates="station",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    area_ref = db.relationship("Area", back_populates="stations")
    assignments = db.relationship(
        "StationAssignment",
        back_populates="station",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="StationAssignment.effective_from.desc()",
    )

    def to_dict(self, include_stats=False, stats=None):
        payload = {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "area_id": self.area_id,
            "area": self.area,
            "address": self.address,
            "station_type": self.station_type,
            "station_type_label": label_of(STATION_TYPE_LABELS, self.station_type),
            "status": self.status,
            "status_label": label_of(STATION_STATUS_LABELS, self.status),
            "longitude": self.longitude,
            "latitude": self.latitude,
            "installed_at": iso_date(self.installed_at),
            "remark": self.remark,
            "created_at": iso(self.created_at),
            "updated_at": iso(self.updated_at),
        }
        if include_stats:
            payload["stats"] = stats or {}
        return payload

    def to_option(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "area": self.area,
            "area_id": self.area_id,
        }

    def __repr__(self):
        return "<Station %s %s>" % (self.code, self.name)

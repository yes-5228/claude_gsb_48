"""责任人 (片区运维/负责人员)."""
from ..domain.constants import PERSON_ROLE_LABELS, PERSON_STATUS_LABELS
from ..extensions import db
from .base import TimestampMixin, iso


class Person(TimestampMixin, db.Model):
    __tablename__ = "persons"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, index=True)
    employee_no = db.Column(db.String(32), unique=True, index=True)
    phone = db.Column(db.String(32))
    department = db.Column(db.String(120))
    role = db.Column(db.String(32), nullable=False, default="officer")
    status = db.Column(db.String(16), nullable=False, default="active", index=True)
    remark = db.Column(db.Text)

    memberships = db.relationship(
        "AreaMembership",
        back_populates="person",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def to_dict(self, area=None):
        payload = {
            "id": self.id,
            "name": self.name,
            "employee_no": self.employee_no,
            "phone": self.phone,
            "department": self.department,
            "role": self.role,
            "role_label": PERSON_ROLE_LABELS.get(self.role, self.role),
            "status": self.status,
            "status_label": PERSON_STATUS_LABELS.get(self.status, self.status),
            "remark": self.remark,
            "created_at": iso(self.created_at),
            "updated_at": iso(self.updated_at),
        }
        if area is not None:
            payload["area"] = area
        return payload

    def to_option(self):
        return {
            "id": self.id,
            "name": self.name,
            "employee_no": self.employee_no,
            "role": self.role,
            "role_label": PERSON_ROLE_LABELS.get(self.role, self.role),
        }

    def __repr__(self):
        return "<Person %s %s>" % (self.employee_no or "-", self.name)

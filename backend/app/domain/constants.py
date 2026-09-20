"""Enumerations shared by the API layer and the frontend."""

PERIOD_LABELS = {"hourly": "小时均值", "daily": "日均值"}

DATA_SOURCE_LABELS = {"manual": "手工录入", "device": "设备上传", "import": "历史导入"}

STATION_TYPE_LABELS = {
    "ambient": "环境空气",
    "traffic": "道路交通",
    "background": "区域背景",
    "industrial": "工业园区",
    "rural": "农村站点",
}

STATION_STATUS_LABELS = {"active": "运行中", "maintenance": "维护中", "offline": "停用"}

EXCEEDANCE_LEVEL_LABELS = {"light": "轻度超标", "moderate": "中度超标", "severe": "重度超标"}

EXCEEDANCE_STATUS_LABELS = {"pending": "待标注", "confirmed": "已确认", "ignored": "已忽略"}

ZONE_STATUS_LABELS = {"active": "启用", "inactive": "停用"}

PERSON_STATUS_LABELS = {"active": "在岗", "inactive": "离岗"}

ZONE_ROLE_LABELS = {"manager": "片区负责人", "supervisor": "分管领导", "engineer": "运维专员"}

CHANGE_REASON_LABELS = {
    "assign": "归属分配",
    "transfer": "片区调整",
    "unassign": "解除归属",
}

CHANGE_TYPE_LABELS = {
    "person_added": "责任人加入",
    "person_removed": "责任人移除",
    "role_changed": "角色调整",
}


def as_options(label_map):
    return [{"value": key, "label": label} for key, label in label_map.items()]


def options_payload():
    return {
        "station_type": as_options(STATION_TYPE_LABELS),
        "station_status": as_options(STATION_STATUS_LABELS),
        "period": as_options(PERIOD_LABELS),
        "data_source": as_options(DATA_SOURCE_LABELS),
        "exceedance_level": as_options(EXCEEDANCE_LEVEL_LABELS),
        "exceedance_status": as_options(EXCEEDANCE_STATUS_LABELS),
        "zone_status": as_options(ZONE_STATUS_LABELS),
        "person_status": as_options(PERSON_STATUS_LABELS),
        "zone_role": as_options(ZONE_ROLE_LABELS),
    }


def label_of(label_map, key):
    return label_map.get(key, key)

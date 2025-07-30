import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class CallbackStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class RobotStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    WORKING = "working"
    IDLE = "idle"
    CHARGING = "charging"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class CleaningMode(Enum):
    AUTO = "auto"
    SPOT = "spot"
    EDGE = "edge"
    MANUAL = "manual"


@dataclass
class CallbackResponse:
    status: CallbackStatus
    message: str
    timestamp: Optional[int] = None
    data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = int(time.time())

    def to_dict(self) -> Dict[str, Any]:
        result = {"status": self.status.value, "message": self.message, "timestamp": self.timestamp}
        if self.data:
            result["data"] = self.data
        return result


@dataclass
class RobotInfo:
    robot_sn: Optional[str] = None
    robot_status: Optional[str] = None
    timestamp: Optional[int] = None


@dataclass
class ErrorInfo:
    robot_sn: Optional[str] = None
    timestamp: Optional[int] = None
    error_type: Optional[str] = None
    error_level: Optional[str] = None
    error_detail: Optional[str] = None
    error_id: Optional[str] = None


@dataclass
class RobotPose:
    x: Optional[float] = None  # X coordinate
    y: Optional[float] = None  # Y coordinate
    yaw: Optional[float] = None  # Yaw angle
    robot_sn: Optional[str] = None  # robot sn
    robot_mac: Optional[str] = None  # robot mac address
    timestamp: Optional[int] = None


@dataclass
class PowerInfo:
    robot_sn: Optional[str] = None  # robot sn
    robot_mac: Optional[str] = None  # robot mac address
    charge_state: Optional[str] = None  # charging, discharging, full, etc.
    power: Optional[int] = None  # percentage from 0 to 100
    timestamp: Optional[int] = None  # timestamp in seconds

from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Event:
    title: str = ""
    start: datetime | None = None
    end: datetime | None = None
    location: str = ""
    description: str = ""
    warnings: list[str] = field(default_factory=list)

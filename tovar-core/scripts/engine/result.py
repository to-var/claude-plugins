from dataclasses import dataclass, field


@dataclass
class Result:
    message: str = ""
    lines: list = field(default_factory=list)
    data: object = None
    ok: bool = True

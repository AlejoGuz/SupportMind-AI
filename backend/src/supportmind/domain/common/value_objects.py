from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TicketNumber:
    value: str

    @staticmethod
    def generate(year: int, sequence: int) -> TicketNumber:
        return TicketNumber(f"SM-{year}-{sequence:06d}")


@dataclass(frozen=True)
class IncidentNumber:
    value: str

    @staticmethod
    def generate(year: int, sequence: int) -> IncidentNumber:
        return IncidentNumber(f"INC-{year}-{sequence:06d}")


@dataclass(frozen=True)
class ProblemFingerprint:
    value: str

    @staticmethod
    def build(*, leaf_node_code: str, product_family: str, path_codes: list[str]) -> ProblemFingerprint:
        raw = "|".join([product_family.lower().strip(), leaf_node_code, *path_codes])
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
        return ProblemFingerprint(digest)


@dataclass(frozen=True)
class Email:
    value: str

    def __post_init__(self) -> None:
        pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not re.match(pattern, self.value):
            raise ValueError(f"Invalid email: {self.value}")


@dataclass(frozen=True)
class Phone:
    value: str


@dataclass(frozen=True)
class OrderNumber:
    value: str

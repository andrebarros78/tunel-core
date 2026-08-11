from __future__ import annotations

from dataclasses import dataclass
import hashlib


@dataclass(frozen=True, slots=True)
class ProcessIdentity:
    pid: int
    executable_path: str
    command_line: str
    parent_pid: int | None = None

    @property
    def fingerprint(self) -> str:
        payload = "\0".join(
            [
                self.executable_path.strip().lower(),
                self.command_line.strip(),
                str(self.parent_pid or ""),
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def same_owner(self, other: "ProcessIdentity") -> bool:
        """PID equality alone is deliberately insufficient."""
        return (
            self.executable_path.strip().lower() == other.executable_path.strip().lower()
            and self.command_line.strip() == other.command_line.strip()
            and self.fingerprint == other.fingerprint
        )


def authorize_termination(expected: ProcessIdentity, actual: ProcessIdentity) -> bool:
    """Fail closed if Windows reused a stale PID for an unrelated process."""
    return expected.pid == actual.pid and expected.same_owner(actual)

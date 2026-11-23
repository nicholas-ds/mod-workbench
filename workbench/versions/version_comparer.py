"""Compare dotted version strings part by part."""

from __future__ import annotations

import re


class VersionComparer:
    """Decide whether a latest version is newer than an installed version."""

    _leading_digits = re.compile(r"\d+")

    def is_newer(self, latest: str, installed: str) -> bool:
        latest_parts = self._parts(latest)
        installed_parts = self._parts(installed)
        if latest_parts is None or installed_parts is None:
            return False
        width = max(len(latest_parts), len(installed_parts))
        padded_latest = latest_parts + (0,) * (width - len(latest_parts))
        padded_installed = installed_parts + (0,) * (width - len(installed_parts))
        return padded_latest > padded_installed

    def _parts(self, version: str) -> tuple[int, ...] | None:
        if version == "":
            return None
        parts = tuple(
            self._leading_digits.match(part)
            for part in version.split(".")
        )
        if any(match is None for match in parts):
            return None
        return tuple(int(match.group()) for match in parts)

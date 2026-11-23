"""Read the operations of an OpenCode OpenAPI spec into endpoint surfaces."""

from __future__ import annotations

from workbench.surfaces.surface_markdown_writer import EndpointSurface

_HTTP_METHODS = ("get", "post", "put", "patch", "delete")


class OpencodeEndpointReader:
    """Turn the spec dict into endpoints, grouped by the first path segment after an optional /api prefix (OpenCode 2)."""

    def read(self, spec: dict) -> dict[str, tuple[EndpointSurface, ...]]:
        groups: dict[str, list[EndpointSurface]] = {}
        for path, operations in sorted(spec.get("paths", {}).items()):
            for method in _HTTP_METHODS:
                operation = operations.get(method)
                if isinstance(operation, dict):
                    endpoint = EndpointSurface(method.upper(), path, self._summary(operation))
                    groups.setdefault(self._group(path), []).append(endpoint)
        return {name: tuple(endpoints) for name, endpoints in groups.items()}

    def _group(self, path: str) -> str:
        segments = [segment for segment in path.split("/") if segment]
        if segments[:1] == ["api"]:
            segments = segments[1:]
        return segments[0] if segments else "root"

    def _summary(self, operation: dict) -> str:
        text = operation.get("summary") or operation.get("description") or ""
        return " ".join(str(text).split())[:120]

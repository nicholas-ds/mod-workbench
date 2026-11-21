"""Write the SDK dictionary as Markdown tables from surfaces already read."""

from __future__ import annotations

from dataclasses import dataclass

from workbench.sdk_surface_reader import ClassSurface, FieldSurface, FunctionSurface


@dataclass(frozen=True)
class EndpointSurface:
    method: str
    path: str
    summary: str


class SurfaceMarkdownWriter:
    """Render surfaces as Markdown. Pure: text in, text out."""

    def fields_table(self, fields: tuple[FieldSurface, ...]) -> str:
        rows = [f"| `{f.name}` | `{self._cell(f.type_text)}` | `{self._cell(f.default_text)}` | {self._cell(f.doc)} |"
                for f in fields]
        return "\n".join(["| Field | Type | Default | What it does |", "|---|---|---|---|", *rows])

    def functions_table(self, functions: tuple[FunctionSurface, ...]) -> str:
        rows = [f"| `{'async ' if f.is_async else ''}{f.name}` | `{self._cell(f.signature)}` | {self._cell(f.doc)} |"
                for f in functions]
        return "\n".join(["| Name | Signature | What it does |", "|---|---|---|", *rows])

    def class_section(self, surface: ClassSurface) -> str:
        parts = [f"### `{surface.name}`", surface.doc]
        if surface.fields:
            parts.append(self.fields_table(surface.fields))
        if surface.methods:
            parts.append(self.functions_table(surface.methods))
        return "\n\n".join(part for part in parts if part)

    def endpoints_table(self, endpoints: tuple[EndpointSurface, ...]) -> str:
        rows = [f"| {e.method} | `{e.path}` | {self._cell(e.summary)} |" for e in endpoints]
        return "\n".join(["| Method | Path | What it does |", "|---|---|---|", *rows])

    def _cell(self, text: str) -> str:
        return text.replace("|", "\|").replace("\n", " ")

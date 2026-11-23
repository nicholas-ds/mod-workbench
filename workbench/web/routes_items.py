"""Item file route of one board: serve a file inside its board folder."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from workbench.boards.board_types import BoardError
from workbench.boards.item_files import ItemKindDetector, SafeItemResolver
from workbench.web.item_style import HtmlItemStyler
from workbench.mods.mod_registry import ModRegistry

_SANDBOX_KINDS = frozenset({"html", "svg"})
_SANDBOX_CSP = "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:"


class ItemsRoutes:
    """Item file route of one board: serve a file inside its board folder."""

    def __init__(self, registry: ModRegistry, resolver: SafeItemResolver,
                 kinds: ItemKindDetector, styler: HtmlItemStyler | None = None) -> None:
        self._registry, self._resolver, self._kinds = registry, resolver, kinds
        self._styler = styler
        self.routes = APIRouter()
        self.routes.add_api_route(
            "/api/mods/{name}/boards/{board_id}/items/{item_path:path}",
            self.item, methods=["GET"])

    def item(self, name: str, board_id: str, item_path: str) -> Response:
        cfg = self._registry.require(name)
        entry = self._registry.require_entry(cfg, board_id)
        resolved = self._resolve(entry.board.folder, item_path)
        kind = self._kinds.detect(resolved)
        if kind == "html" and self._styler is not None:
            return self._styled_html(resolved, self._headers(kind))
        return FileResponse(resolved, headers=self._headers(kind))

    def _styled_html(self, path: Path, headers: dict[str, str]) -> Response:
        html = path.read_text(encoding="utf-8")
        return Response(self._styler.apply(html), media_type="text/html", headers=headers)

    def _resolve(self, folder: Path, item_path: str) -> Path:
        try:
            return self._resolver.resolve(folder, item_path)
        except BoardError as exc:
            raise HTTPException(status_code=404, detail=exc.reason) from exc

    def _headers(self, kind: str) -> dict[str, str]:
        headers = {"Cache-Control": "no-cache"}
        if kind in _SANDBOX_KINDS:
            headers["Content-Security-Policy"] = _SANDBOX_CSP
        return headers

"""HTTP route to upload one file into the folder of a named chat."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from workbench.chat_upload_saver import ChatUploadSaver
from workbench.orchestrator_directory import OrchestratorDirectory


class UploadRoutes:
    """POST one raw file into the uploads folder of a named chat."""

    def __init__(self, directory: OrchestratorDirectory,
                 saver: ChatUploadSaver) -> None:
        self._directory = directory
        self._saver = saver
        self.routes = APIRouter()
        self.routes.add_api_route(
            "/api/chat/{name}/upload", self.upload, methods=["POST"])

    async def upload(self, name: str, filename: str,
                     request: Request) -> dict[str, str]:
        folder = self._directory.folder_of(name)
        if folder == "":
            raise HTTPException(status_code=404)
        self._refuse_oversize(request)
        try:
            return {"path": self._saver.save(folder, filename,
                                             await request.body())}
        except ValueError:
            raise HTTPException(status_code=400) from None

    def _refuse_oversize(self, request: Request) -> None:
        length = request.headers.get("content-length")
        if length is None or not length.isdigit() or int(length) > self._saver.max_bytes:
            raise HTTPException(status_code=413)

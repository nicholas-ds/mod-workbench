"""Write docs/sdk-chat/sdk-surfaces.md and opencode-surfaces.md. Run again after an SDK or OpenCode update.

Usage: .venv/Scripts/python scripts/sdk_surfaces.py <opencode-spec.json>
Get the spec with: opencode api --standalone GET /openapi.json > spec.json (OpenCode 2.3.0).
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

from workbench.surfaces.export_grouper import ExportGrouper
from workbench.surfaces.opencode_endpoint_reader import OpencodeEndpointReader
from workbench.surfaces.sdk_dictionary_builder import SdkDictionaryBuilder
from workbench.surfaces.sdk_surface_reader import SdkSourceReader
from workbench.surfaces.surface_markdown_writer import SurfaceMarkdownWriter

OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "sdk-chat"
MODULE_FILES = ("types.py", "client.py", "query.py", "__init__.py", "_internal/sessions.py",
                "_internal/session_mutations.py", "_internal/session_store.py", "_internal/session_import.py")


def package_dir() -> Path:
    spec = importlib.util.find_spec("claude_agent_sdk")
    return Path(next(iter(spec.submodule_search_locations)))


def read_versions(root: Path) -> str:
    sdk = re.search(r'"([\d.]+)"', (root / "_version.py").read_text(encoding="utf-8")).group(1)
    cli = re.search(r'"([\d.]+)"', (root / "_cli_version.py").read_text(encoding="utf-8")).group(1)
    return f"Package `claude-agent-sdk` {sdk}. It bundles Claude Code CLI {cli}."


def main(spec_path: Path) -> None:
    root = package_dir()
    builder = SdkDictionaryBuilder(SdkSourceReader(), SurfaceMarkdownWriter(), ExportGrouper(), OpencodeEndpointReader())
    sources = tuple((root / name).read_text(encoding="utf-8") for name in MODULE_FILES)
    init_source = (root / "__init__.py").read_text(encoding="utf-8")
    (OUT_DIR / "sdk-surfaces.md").write_text(builder.build_claude(read_versions(root), init_source, sources), encoding="utf-8")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    (OUT_DIR / "opencode-surfaces.md").write_text(builder.build_opencode(spec), encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]))

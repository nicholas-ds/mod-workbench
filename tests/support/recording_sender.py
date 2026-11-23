"""Shared fake PaneSender."""

from workbench.panes.pane_registry import OrchestratorPane


class RecordingSender:
    """Fake PaneSender that records the lines it is asked to type."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def send(self, pane: OrchestratorPane, text: str) -> bool:
        self.lines.append(text)
        return True

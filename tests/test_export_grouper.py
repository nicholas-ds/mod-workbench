"""ExportGrouper puts exported names into groups by naming pattern."""

from workbench.export_grouper import ExportGrouper


def test_hook_inputs_group_together() -> None:
    groups = ExportGrouper().group(("StopHookInput", "PreToolUseHookInput"))
    assert list(groups.values()) == [("PreToolUseHookInput", "StopHookInput")]


def test_message_and_block_names_group_apart() -> None:
    groups = ExportGrouper().group(("AssistantMessage", "TextBlock"))
    assert len(groups) == 2


def test_unknown_name_goes_to_other() -> None:
    assert ExportGrouper().group(("Zebra",)) == {"Other": ("Zebra",)}

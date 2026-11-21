"""OpencodeEndpointReader groups spec operations by the first path segment."""

from workbench.opencode_endpoint_reader import OpencodeEndpointReader

SPEC = {"paths": {
    "/session": {"get": {"summary": "List sessions"}, "post": {"description": "Create a session"}},
    "/session/{id}": {"delete": {"summary": "Delete"}},
    "/event": {"get": {"summary": "Event stream"}, "parameters": []},
}}


def test_operations_group_by_first_segment() -> None:
    groups = OpencodeEndpointReader().read(SPEC)
    assert sorted(groups) == ["event", "session"]
    assert [(e.method, e.path) for e in groups["session"]] == [
        ("GET", "/session"), ("POST", "/session"), ("DELETE", "/session/{id}")]


def test_summary_falls_back_to_description() -> None:
    groups = OpencodeEndpointReader().read(SPEC)
    assert groups["session"][1].summary == "Create a session"


def test_non_operation_keys_are_ignored() -> None:
    groups = OpencodeEndpointReader().read(SPEC)
    assert len(groups["event"]) == 1


def test_api_prefix_is_skipped_when_grouping() -> None:
    spec = {"paths": {"/api/session": {"get": {"summary": "List"}}, "/api/event": {"get": {}}}}
    groups = OpencodeEndpointReader().read(spec)
    assert sorted(groups) == ["event", "session"]

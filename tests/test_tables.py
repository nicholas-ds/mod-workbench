from collections.abc import Mapping

from workbench.tables import Table, TableBuilder


def test_new_key_becomes_column() -> None:
    records: list[Mapping[str, object]] = [{"id": "a", "mood": "calm"}]
    table = TableBuilder().build(records)
    assert table.columns == ("id", "mood")
    assert table.rows == ({"id": "a", "mood": "calm"},)


def test_missing_value_is_empty_string() -> None:
    records: list[Mapping[str, object]] = [
        {"id": "a", "mood": "calm"},
        {"id": "b", "size": 2},
    ]
    table = TableBuilder().build(records)
    assert table.columns == ("id", "mood", "size")
    assert table.rows[1] == {"id": "b", "mood": "", "size": 2}


def test_empty_records_give_empty_table() -> None:
    table = TableBuilder().build([])
    assert isinstance(table, Table)
    assert table.columns == ()
    assert table.rows == ()

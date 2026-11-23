"""SdkSourceReader reads classes, fields with attribute docs, methods and exports from source text."""

from workbench.surfaces.sdk_surface_reader import SdkSourceReader

SOURCE = '''
__all__ = ["Thing", "make"]

class Thing:
    """A thing. More words."""

    size: int = 3
    """How big it is."""
    name: str

    async def run(self, count: int) -> str:
        """Run it. Slowly."""

    def _hidden(self) -> None:
        pass


def make(value: str) -> Thing:
    """Make one."""
'''


def test_class_fields_carry_type_default_and_attribute_doc() -> None:
    thing = SdkSourceReader().read(SOURCE).classes[0]
    size = thing.fields[0]
    assert (size.name, size.type_text, size.default_text, size.doc) == ("size", "int", "3", "How big it is.")


def test_field_without_default_or_doc_is_listed() -> None:
    thing = SdkSourceReader().read(SOURCE).classes[0]
    assert (thing.fields[1].name, thing.fields[1].default_text, thing.fields[1].doc) == ("name", "", "")


def test_methods_skip_private_and_keep_async_flag() -> None:
    thing = SdkSourceReader().read(SOURCE).classes[0]
    assert [(m.name, m.is_async) for m in thing.methods] == [("run", True)]


def test_class_doc_is_first_line_only() -> None:
    assert SdkSourceReader().read(SOURCE).classes[0].doc == "A thing. More words."


def test_module_function_has_signature_and_doc() -> None:
    make = SdkSourceReader().read(SOURCE).functions[0]
    assert (make.name, make.signature, make.doc) == ("make", "(value: str) -> Thing", "Make one.")


def test_exports_come_from_dunder_all() -> None:
    assert SdkSourceReader().read_exports(SOURCE) == ("Thing", "make")

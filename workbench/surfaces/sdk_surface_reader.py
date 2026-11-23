"""Read the public surface of a Python package from its source text (no import, no execution).

Used to build the SDK dictionary: every class with its fields and methods, every function,
and the names a package exports. Parsing the source means a broken or changed package
cannot run code here, and the result is the same on every machine.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class FieldSurface:
    name: str
    type_text: str
    default_text: str
    doc: str


@dataclass(frozen=True)
class FunctionSurface:
    name: str
    signature: str
    doc: str
    is_async: bool


@dataclass(frozen=True)
class ClassSurface:
    name: str
    doc: str
    fields: tuple[FieldSurface, ...]
    methods: tuple[FunctionSurface, ...]


@dataclass(frozen=True)
class ModuleSurface:
    classes: tuple[ClassSurface, ...]
    functions: tuple[FunctionSurface, ...]


class SdkSourceReader:
    """Turn the source text of one module into a `ModuleSurface`."""

    def read(self, source: str) -> ModuleSurface:
        tree = ast.parse(source)
        classes = tuple(self._class(node) for node in tree.body if isinstance(node, ast.ClassDef))
        functions = tuple(self._function(node) for node in tree.body
                          if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))
        return ModuleSurface(classes=classes, functions=functions)

    def read_exports(self, source: str) -> tuple[str, ...]:
        tree = ast.parse(source)
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets):
                return tuple(element.value for element in node.value.elts
                             if isinstance(element, ast.Constant))
        return ()

    def _class(self, node: ast.ClassDef) -> ClassSurface:
        methods = tuple(self._function(child) for child in node.body
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and not child.name.startswith("_"))
        return ClassSurface(node.name, self._first_line(ast.get_docstring(node)),
                            self._fields(node), methods)

    def _fields(self, node: ast.ClassDef) -> tuple[FieldSurface, ...]:
        fields: list[FieldSurface] = []
        for index, child in enumerate(node.body):
            if not (isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name)):
                continue
            default = ast.unparse(child.value) if child.value is not None else ""
            fields.append(FieldSurface(child.target.id, ast.unparse(child.annotation),
                                       default, self._attribute_doc(node.body, index)))
        return tuple(fields)

    def _attribute_doc(self, body: list[ast.stmt], index: int) -> str:
        following = body[index + 1] if index + 1 < len(body) else None
        if isinstance(following, ast.Expr) and isinstance(following.value, ast.Constant) \
                and isinstance(following.value.value, str):
            return self._first_line(following.value.value)
        return ""

    def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionSurface:
        returns = f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
        signature = f"({ast.unparse(node.args)}){returns}"
        return FunctionSurface(node.name, signature, self._first_line(ast.get_docstring(node)),
                               isinstance(node, ast.AsyncFunctionDef))

    def _first_line(self, text: str | None) -> str:
        if not text:
            return ""
        return " ".join(text.strip().splitlines()[0].split())

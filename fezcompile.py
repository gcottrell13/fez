import copy
import inspect
import ast

from rw_signal import signal as SIGNALIS, ReadSignal


class Visitor(ast.NodeTransformer):
    def __init__(self, locals: dict, signals_locals: dict[str, type]):
        self.locals = locals
        self.signals_locals = signals_locals
        self.signal_references: set[str] = set()

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load) and node.id in self.signals_locals:
            self.signal_references.add(node.id)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef):
        visitor = Visitor(self.locals.copy(), self.signals_locals.copy())
        new_body = []
        refs = set()
        for item in node.body:
            new_body.append(visitor.visit(item))
            if new := visitor.signal_references.difference(refs):
                refs.update(visitor.signal_references)
        new_node = copy.copy(node)
        new_node.body = new_body

        line_info = {
            "lineno": node.lineno,
            "col_offset": node.col_offset,
            "end_lineno": node.end_lineno,
            "end_col_offset": node.end_col_offset,
        }

        if refs:
            self.signals_locals[node.name] = node
            new_node.decorator_list += [
                ast.Call(
                    func=ast.Attribute(
                        value=ast.Name("signal", ctx=ast.Load(), **line_info),
                        attr="func",
                        ctx=ast.Load(),
                        **line_info,
                    ),
                    args=[
                        ast.Name(id=ref, ctx=ast.Load(), **line_info) for ref in refs
                    ],
                )
            ]

        return new_node

    def visit_Assign(self, node: ast.Assign):
        match node:
            case ast.Assign(
                targets=[ast.Tuple(elts=[ast.Name(id=read), ast.Name()])],
                value=ast.Call(func=ast.Name(id=func_id)),
            ) if (
                self.locals.get(func_id) is SIGNALIS
            ):
                self.signals_locals[read] = ReadSignal
            case ast.Assign(
                value=ast.Call(func=ast.Name(id=func_id)),
            ) if (
                func_id in self.signals_locals
            ):
                self.signal_references.add(func_id)
        return node

    def visit_AnnAssign(self, node: ast.AnnAssign):
        match node:
            case ast.AnnAssign(
                target=ast.Name(target, ctx=ast.Store()),
                annotation=ast.Subscript(
                    value=ast.Name(id="list"),
                    slice=ast.Subscript(value=ast.Name(id="ReadSignal")),
                ),
                value=ast.List(),
            ):
                self.signals_locals[target] = list[ReadSignal]
        return node


def visitor(locals, node: ast.stmt):

    if not isinstance(node, ast.FunctionDef):
        raise TypeError()

    visitor = Visitor(locals, {})
    new_body = []
    for item in node.body:
        new_body.append(visitor.visit(item))
    new_node = copy.copy(node)
    new_node.body = new_body

    new_node.decorator_list = []
    return new_node


def component(fn):
    locals = inspect.currentframe().f_back.f_locals

    source = inspect.getsource(fn)
    tree = ast.parse(source)
    compiled = ast.unparse(visitor(locals, tree.body[0]))
    exec(compiled, locals)
    return locals[fn.__name__]

import copy
import inspect
import ast

from rw_signal import signal as SIGNALIS, ReadSignal


def get_line_info(node: ast.stmt):
    return {
        "lineno": node.lineno,
        "col_offset": node.col_offset,
        "end_lineno": node.end_lineno,
        "end_col_offset": node.end_col_offset,
    }


class Visitor(ast.NodeTransformer):
    def __init__(self, signal_func_name, signals_locals: dict[str, type]):
        self.signal_func_name = signal_func_name
        self.signals_locals = signals_locals
        self.signal_references: set[str] = set()
        self.inner_defined_functions: set[str] = set()

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load) and node.id in self.signals_locals:
            self.signal_references.add(node.id)
        return node

    def visit_Lambda(self, node: ast.Lambda):
        visitor = Visitor(self.signal_func_name, self.signals_locals.copy())
        refs = set()
        new_body = visitor.visit(node.body)
        if visitor.signal_references.difference(refs):
            refs.update(visitor.signal_references)
        new_node = copy.copy(node)
        new_node.body = new_body

        line_info = get_line_info(node)

        if refs:
            # we do not track this lambda as a named signal.
            # if you need a name, use a function definition instead
            new_node = ast.Call(
                func=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(
                            self.signal_func_name, ctx=ast.Load(), **line_info
                        ),
                        attr="func",
                        ctx=ast.Load(),
                        **line_info,
                    ),
                    args=[
                        ast.Name(id=ref, ctx=ast.Load(), **line_info) for ref in refs
                    ],
                    keywords=[
                        ast.keyword(
                            "line_from",
                            value=ast.Constant(
                                f"Line {node.lineno} - {ast.unparse(node)}",
                                **line_info,
                            ),
                            **line_info,
                        ),
                    ],
                ),
                args=[node],
            )
        return new_node

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.inner_defined_functions.add(node.name)

        visitor = Visitor(self.signal_func_name, self.signals_locals.copy())
        new_body = []
        refs = set()
        for item in node.body:
            new_body.append(visitor.visit(item))
            if visitor.signal_references.difference(refs):
                refs.update(visitor.signal_references)
        new_node = copy.copy(node)
        new_node.body = new_body

        line_info = get_line_info(node)
        refs.difference_update(visitor.inner_defined_functions)

        if refs:
            self.signals_locals[node.name] = node
            new_node.decorator_list += [
                ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(
                            self.signal_func_name, ctx=ast.Load(), **line_info
                        ),
                        attr="func",
                        ctx=ast.Load(),
                        **line_info,
                    ),
                    args=[
                        ast.Name(id=ref, ctx=ast.Load(), **line_info) for ref in refs
                    ],
                    keywords=[
                        ast.keyword(
                            arg="line_from",
                            value=ast.Constant(
                                f"Line {node.lineno} - def {node.name}",
                                **line_info,
                            ),
                            **line_info,
                        ),
                    ],
                )
            ]

        return new_node

    def visit_For(self, node: ast.For):
        match node.target, node.iter:
            case ast.Tuple(
                elts=[
                    ast.Name(),
                    ast.Tuple(elts=[ast.Name(id=read_target), ast.Name()]),
                ]
            ), ast.Call(
                func=ast.Name(id="enumerate"), args=[ast.Call(func=ast.Name(id=read))]
            ) if (
                read in self.signals_locals
            ):
                self.signals_locals[read_target] = ReadSignal
            case ast.Tuple(elts=[ast.Name(id=read_target), ast.Name()]), ast.Call(
                func=ast.Name(id=read)
            ) if (read in self.signals_locals):
                self.signals_locals[read_target] = ReadSignal

        return self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        match node:
            case ast.Assign(
                targets=[ast.Tuple(elts=[ast.Name(id=read), ast.Name()])],
                value=ast.Call(func=ast.Name(id=func_id)),
            ) if (
                func_id == self.signal_func_name
            ):
                self.signals_locals[read] = ReadSignal

                new_node = copy.copy(node)
                line_info = get_line_info(node)
                new_node.value = ast.Call(
                    func=node.value.func,
                    args=node.value.args,
                    keywords=[
                        ast.keyword(
                            "line_from",
                            value=ast.Constant(
                                f"Line {node.lineno} - {ast.unparse(node)}",
                                **line_info,
                            ),
                            **line_info,
                        ),
                    ],
                )
                return new_node
            case ast.Assign(
                value=ast.Call(func=ast.Name(id=func_id)),
            ) if (
                func_id in self.signals_locals
            ):
                self.signal_references.add(func_id)
        return self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        match node:
            case ast.Call(func=ast.Name(id=func_id)) if (
                func_id == self.signal_func_name
            ):
                new_node = copy.copy(node)
                line_info = get_line_info(node)
                new_node.keywords = [
                    ast.keyword(
                        "line_from",
                        value=ast.Constant(
                            f"Line {node.lineno} - {ast.unparse(node)}",
                            **line_info,
                        ),
                        **line_info,
                    ),
                ]
                return new_node
        return self.generic_visit(node)


def visitor(signal_func_name, node: ast.stmt):

    if not isinstance(node, ast.FunctionDef):
        raise TypeError()

    visitor = Visitor(signal_func_name, {})
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

    signal_func_name = ""
    for k, v in locals.items():
        if v is SIGNALIS:
            signal_func_name = k

    compiled = ast.unparse(visitor(signal_func_name, tree.body[0]))
    exec(compiled, locals)
    new_func = locals[fn.__name__]
    new_func.source = compiled
    return new_func


class PrecompileComponentTransform(ast.NodeTransformer):
    def __init__(self):
        self.import_component_as = "component"
        self.signal_func_name = "signal"

    def visit_ImportFrom(self, node: ast.ImportFrom):
        match node.module, node.names:
            case "fezcompile", [ast.alias(name="component", asname=asname)] if asname:
                self.import_component_as = asname
            case "fw_signal", [
                ast.alias(name="signal", asname=asname),
                *_rest,
            ] if asname:
                self.signal_func_name = asname
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef):
        for i, deco in enumerate(node.decorator_list):
            match deco:
                case ast.Name(id=id) if id == self.import_component_as:
                    return visitor(self.signal_func_name, node)
        return node


def precompile_module(module_source: str):
    tree = ast.parse(module_source)
    compiled = PrecompileComponentTransform().visit(tree)
    return ast.unparse(compiled)

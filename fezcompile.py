import ast
import inspect
import js


def transform_stmt(stmt: ast.stmt) -> js.Statement:
    match stmt:
        case ast.FunctionDef(
            name=name,
            body=body,
            args=args,
            decorator_list=decorator_list,
        ):
            if args.kwarg or args.vararg or args.kwonlyargs or args.posonlyargs:
                raise NotImplementedError("only positional arguments are implemented")
            if args.defaults or args.kw_defaults:
                raise NotImplementedError("default function values are not implemented")
            return js.FunctionDef(
                name=name,
                args=[js.Identifier(arg.arg) for arg in args.args],
                body=[transform_stmt(stmt) for stmt in body],
            )
        case ast.Return(value=expr):
            return js.Return(value=transform_expr(expr))
        case _:
            return js.SingleLineComment(f"Not implemented: {ast.dump(stmt)}")


def transform_expr(node: ast.expr) -> js.Expr:
    match node:
        case ast.Subscript(value=base, slice=sub):
            return js.Subscript(transform_expr(base), transform_expr(sub))
        case ast.Name(id=name, ctx=ast.Load()):
            return js.LoadName(name)
        case ast.Call(func=func, args=args, keywords=keywords):
            keys = []
            values = []
            for k in keywords:
                keys.append(js.Identifier(k.arg))
                values.append(transform_expr(k.value))
            return js.Call(
                transform_expr(func),
                [transform_expr(arg) for arg in args],
                js.ObjectLiteral(keys, values),
            )
        case ast.Dict(keys=keys, values=values):
            return js.ObjectLiteral(
                [transform_expr(k) for k in keys], [transform_expr(v) for v in values]
            )
        case ast.Constant(value=value):
            return js.Constant(value)
        case _:
            return js.InlineComment(f"Not implemented: {ast.dump(node)}")


def fezcompile(fn):
    source = inspect.getsource(fn)
    tree = ast.parse(source)
    return js.dump(transform_stmt(tree.body[0]), js.Indenter("  "))

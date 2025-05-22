import json


class Indenter:
    def __init__(self, base: str):
        self.base = base

    def __call__(self, content: str):
        return "\n".join(self.base + line for line in content.splitlines())


class AST:
    pass


class Statement(AST):
    pass


class Expr(AST):
    pass


class Assignable(Expr):
    pass


class Assignment(Expr, Statement):
    def __init__(self, lhs: list[Assignable], rhs: list[Expr]):
        self.lhs = lhs
        self.rhs = rhs


class Identifier(AST):
    def __init__(self, name: str):
        self.name = name


class SingleLineComment(Statement):
    def __init__(self, content: str):
        self.content = content


class InlineComment(Expr):
    def __init__(self, content: str):
        self.content = content


class FunctionDef(Expr, Statement):
    def __init__(self, name: str, args: list[Identifier], body: list[Statement]):
        self.args = args
        self.body = body
        self.name = name


class Return(Statement):
    def __init__(self, value: Expr):
        self.value = value


class Subscript(Expr):
    def __init__(self, base: Expr, sub: Expr):
        self.base = base
        self.sub = sub


class LoadName(Expr):
    def __init__(self, name: str):
        self.name = name


class ObjectLiteral(Expr):
    def __init__(self, keys: list[Expr], values: list[Expr]):
        self.keys = keys
        self.values = values


class Call(Expr):
    def __init__(self, func: Expr, args: list[Expr], keywords: ObjectLiteral):
        self.keywords = keywords  # not technically part of js
        self.args = args
        self.func = func


class Constant(Expr):
    def __init__(self, value):
        self.value = value


def dump(tree: AST, i: Indenter) -> str:
    match tree:
        case Assignment(lhs=lhs, rhs=rhs):
            left = ", ".join(dump(item, i) for item in lhs)
            right = ", ".join(dump(item, i) for item in rhs)
            return i(f"{left} = {right}")
        case FunctionDef(name=name, args=args, body=body):
            return f"""
function {name}({", ".join(dump(arg, i) for arg in args)}) {{
{"\n".join(i(dump(item, i)) for item in body)}
}}
"""
        case Identifier(name=name):
            return name
        case SingleLineComment(content=content):
            return i(f"// {content}")
        case InlineComment(content=content):
            return i(f"/* {content} */")
        case Return(value=value):
            return i(f"return {dump(value, i)};")
        case Subscript(base=base, sub=sub):
            return i(f"{dump(base, i)}[{dump(sub, i)}]")
        case LoadName(name=name):
            return name
        case Call(func=func, args=args, keywords=k):
            if k.keys:
                keywords = i(dump(k, i))
            else:
                keywords = ""
            return i(
                f'{dump(func, i)}({keywords}{
            ", ".join(dump(item, i) for item in args)
            })'
            )
        case ObjectLiteral(keys=keys, values=values):
            return f"{{{i(',\n'.join(
                i(f'{dump(key, i)}: {dump(value, i)}')
                for key, value in zip(keys, values, strict=True)
            ))}}}, "
        case Constant(value=value):
            return json.dumps(value)
        case _:
            return i(f"// js dump not implemented: {tree}")

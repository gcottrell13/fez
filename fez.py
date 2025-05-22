import re

from typing import TypedDict

from fezcompile import fezcompile


def RENDER(item):
    if isinstance(item, BaseElement):
        return item.render()
    return str(item)


to_css_re = re.compile(r"[A-Z]?[a-z_]+")


class ElementMeta(type):
    def __new__(mcls, name, bases, attrs, *, tag: str = None):
        new = super().__new__(mcls, name, bases, attrs)
        new.tag = tag
        return new


class BaseElement(metaclass=ElementMeta):
    def _copy(self):
        new = type(self)()
        new.__dict__.update(self.__dict__.copy())
        return new

    def render(self):
        parts = []
        if style := STYLE.render_style(self):
            parts.append(style)
        if parts:
            parts.insert(0, "")
        return f"<{self.tag}{' '.join(parts)}>{CHILDREN.render_children(self)}</{self.tag}>"


class Styles(TypedDict, total=False):
    color: str
    backgroundColor: str


class STYLE(BaseElement):
    def __call__(self, *, style: Styles, **kwargs):
        new = self._copy()
        new.style = style
        return new

    def render_style(self):
        if style := self.__dict__.get("style"):
            styles = ",".join(
                f'{"-".join(to_css_re.findall(key))}: value'
                for key, value in style.items()
            )
            return f'style="{styles}"'
        return ""


class CLASS(BaseElement):
    def __call__(self, *, className: str | list[str], **kwargs):
        new = self._copy()
        new.className = (
            className if isinstance(className, list) else className.split(" ")
        )
        return new


class CHILDREN(BaseElement):
    def __getitem__(self, children):
        new = self._copy()
        new.children = children if isinstance(children, tuple | list) else [children]
        return new

    def render_children(self):
        if isinstance(children := self.__dict__.get("children"), tuple | list):
            return "\n".join(RENDER(child) for child in children)
        return ""


class H1(STYLE, CHILDREN, tag="h1"):
    pass


class H2(STYLE, CHILDREN, tag="h2"):
    pass


class H3(STYLE, CHILDREN, tag="h3"):
    pass


class H4(STYLE, CHILDREN, tag="h4"):
    pass


class H5(STYLE, CHILDREN, tag="h5"):
    pass


class HTML(CHILDREN, tag="html"):
    pass


class BODY(STYLE, CHILDREN, tag="body"):
    pass


class DIV(STYLE, CHILDREN, tag="div"):
    pass


class SPAN(STYLE, CHILDREN, tag="span"):
    pass


h1 = H1()
h2 = H2()
h3 = H3()
h4 = H4()
h5 = H5()
html = HTML()
body = BODY()
div = DIV()
span = SPAN()


def main(arg1):
    return html[h1(style={"backgroundColor": "red"})[div["hi there"]]]


if __name__ == "__main__":
    print(fezcompile(main))

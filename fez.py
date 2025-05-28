import copy
import inspect
import re

from typing import TypedDict, Callable, Unpack

from browser import DOMNode, html
from fezcompile import component
from rw_signal import signal, ReadSignal, SyntheticSignal

to_css_re = re.compile(r"[A-Z]?[a-z_]+")


class ElementMeta(type(DOMNode)):
    def __new__(mcls, name, bases, attrs, *, tag: str = ""):
        new = super().__new__(mcls, name, bases, attrs)
        new.tag = tag.upper()
        return new


class Elem(DOMNode, metaclass=ElementMeta):
    pass


type Renderable = str | int | float | Elem | ReadSignal | Callable[[], Renderable]


class Styles(TypedDict, total=False):
    color: str
    backgroundColor: str


class Kwargs(TypedDict, total=False):
    style: Styles
    cls: list[str] | str
    key: str | int


def copy_self(fn):
    def wrapper(self, *args, **kwargs):
        new = type(self)()
        for k, v in self.__dict__.items():
            setattr(new, k, v)
        return fn(new, *args, **kwargs)

    return wrapper


class Element(Elem):
    def __init__(self):
        self.children: tuple[Renderable, ...] = ()
        self.styles = ""
        self.cls = ""
        self.key = ""

    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        self.__dict__[key] = value

    @copy_self
    def __call__(self, **kwargs: Unpack[Kwargs]):
        self.styles = kwargs.get("style", "")
        cls = kwargs.get("cls", "")
        self.cls = cls if isinstance(cls, str) else " ".join(cls)
        self.key = str(kwargs.get("key", ""))
        return self

    @copy_self
    def __getitem__(self, item: tuple[Renderable, ...] | Renderable):
        if isinstance(item, tuple):
            self.children = item
        else:
            self.children = (item,)
        return self

    def render(self, parent: Elem) -> Elem:
        elem = getattr(html, self.tag)()
        parent.attach(elem)
        for child in self.children:
            if isinstance(child, Element):
                child.render(elem)
            elif isinstance(child, ReadSignal):
                if not isinstance(child, SyntheticSignal):
                    child = SyntheticSignal.new(child, child, line_from=child.line_from)
                value = child()
                if inspect.isgenerator(value):
                    self.render_generator(child, elem, value)
                else:
                    self.render_single(child, elem, value)

        return elem

    def render_single(self, child, elem, value):
        res = elem.attach(value)

        def rerender():
            nonlocal res
            if res != elem:
                elem.remove(res)
                res = elem.attach(child())
            else:
                elem.innerHTML = child()

        child.rerender = rerender

    def render_generator(self, child, elem, value):
        keys = []
        for i, v in enumerate(value):
            if isinstance(v, Element):
                key = v.key or i
                v.render(elem)
                keys.append(str(key))
            else:
                elem.attach(v)
                keys.append(str(i))

        def rerender():
            value = list(child())
            while len(keys) > len(value):
                keys.pop()
            for i, v in enumerate(value):
                if isinstance(v, Element):
                    print("rerender element", keys, i, v.key)
                    if i < len(keys):
                        if str(v.key) != keys[i]:
                            v.render(elem)
                            keys[i] = str(v.key or i)
                            print(f"setting key at {i=} to {keys[i]}")
                        else:
                            print("do nothing")
                    else:
                        v.render(elem)
                        key = v.key or i
                        print(f"adding elem {key=}")
                        keys.append(str(key))
                else:
                    print("attach literal")
                    elem.attach(v)

        child.rerender = rerender


class H1(Element, tag="h1"):
    pass


class H2(Element, tag="h2"):
    pass


class H3(Element, tag="h3"):
    pass


class H4(Element, tag="h4"):
    pass


class H5(Element, tag="h5"):
    pass


class HTML(Element, tag="html"):
    pass


class BODY(Element, tag="body"):
    pass


class DIV(Element, tag="div"):
    pass


class SPAN(Element, tag="span"):
    pass


class BUTTON(Element, tag="button"):
    def __init__(self):
        super().__init__()
        self.on_click = None

    def __call__(self, on_click: Callable, **kwargs):
        new = super().__call__(**kwargs)
        new.on_click = on_click
        return new

    def render(self, parent: Elem):
        ref = super().render(parent)
        if self.on_click:
            ref.bind("click", self.on_click)


h1 = H1()
h2 = H2()
h3 = H3()
h4 = H4()
h5 = H5()
body = BODY()
div = DIV()
span = SPAN()
button = BUTTON()


@component
def main_component():
    read, write = signal(0)

    arr_read, arr_write = signal([])

    def on_click(ev):
        write(read() + 1)
        arr_write().append(signal(0))

    def a():
        for i, (r, w) in enumerate(arr_read()):

            def click(ev):
                w(r() + 1)

            yield div(key=i)[
                button(on_click=click)[lambda: f"hello {read()} there: {r()}"]
            ]

    test: int
    return span[
        h1(style={"backgroundColor": "red"})[a],
        div[button(on_click=on_click)[read]],
    ]

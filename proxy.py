def getfn(name):
    def fn(self, *args, **kwargs):
        value = getattr(self.proxied_item, name)(*args, **kwargs)
        self.on_change()
        return value

    return fn


def init(self, proxied_item, on_change):
    self.proxied_item = proxied_item
    self.on_change = on_change


class Proxy:
    def __init__(self, proxied_item, on_change):
        self.proxied_item = proxied_item
        self.on_change = on_change

    def set_value(self, value):
        self.proxied_item = value
        self.on_change()


ListProxy = type(
    "ListProxy",
    (Proxy,),
    {
        **{name: getfn(name) for name in ["append", "clear", "insert", "__iter__"]},
    },
)


def proxy(proxied_item, on_change) -> Proxy:
    if isinstance(proxied_item, list):
        return ListProxy(proxied_item, on_change)

    return Proxy(proxied_item, on_change)

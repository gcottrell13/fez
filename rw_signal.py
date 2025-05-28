from proxy import proxy, Proxy


class ReadSignal[T]:
    def __init__(self, v: Proxy, line_from: str):
        self.line_from = line_from
        self.v = v
        self.dependents: set[ReadSignal] = set()
        self.depends_on: set[ReadSignal] = set()

        self.dirty = False

    def __call__(self):
        return self.v.proxied_item

    def destroy(self):
        for k in self.depends_on:
            k.remove_dependent(self)

    def add_dependent(self, s):
        self.dependents.add(s)

    def remove_dependent(self, s):
        self.dependents.remove(s)

    def trigger_update(self):
        self.replace_dom()
        for k in self.dependents:
            k.trigger_update()

    def replace_dom(self): ...

    def __str__(self):
        return f'ReadSignal["{self.line_from}", {len(self.dependents)=}]'

    def __repr__(self):
        return str(self)


class WriteSignal[T]:
    def __init__(self, v: Proxy, read_signal: ReadSignal, line_from: str):
        self.line_from = line_from
        self.read_signal = read_signal
        self.v = v

    def __call__(self, *args):
        # type: (self, *args) -> T
        if not args:
            return self.v
        self.v.set_value(args[0])
        return None

    def __str__(self):
        return f"WriteSignal: {self.line_from}"

    def __repr__(self):
        return str(self)


def signal[T](
    initial_value: T,
    line_from: str = None,
) -> tuple[ReadSignal[T], WriteSignal[T]]:
    def on_change():
        read.dirty = True
        read.trigger_update()

    value = proxy(initial_value, on_change)

    read = ReadSignal(value, line_from)
    write = WriteSignal(value, read, line_from)
    return read, write


class SyntheticSignal[T](ReadSignal):
    def __init__(self, fn, line_from):
        super().__init__(None, line_from)
        self.fn = fn
        self.rerender = None

    def __call__(self, *args):
        return self.fn(*args)

    def replace_dom(self):
        if self.rerender:
            self.rerender()

    @staticmethod
    def new(fn, *signals_used: ReadSignal, line_from: str):
        print("new syn signal", fn, line_from)
        syn = SyntheticSignal(fn, line_from)
        for s in signals_used:
            syn.depends_on.add(s)
            s.add_dependent(syn)
        return syn


def signal_func(*signals_used: ReadSignal, line_from):
    def wrapper(fn):
        return SyntheticSignal.new(fn, *signals_used, line_from=line_from)

    return wrapper


signal.func = signal_func

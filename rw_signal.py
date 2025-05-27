class ReadSignal[T]:
    def __call__(self) -> T:
        pass


class WriteSignal[T]:
    def __call__(self, value: T):
        pass


def signal[T](initial_value: T) -> tuple[ReadSignal[T], WriteSignal[T]]:
    return ReadSignal[T](), WriteSignal[T]()


def signal_func(*signals_used: ReadSignal):
    def wrapper(fn):
        def wrapped():
            pass

        return wrapped

    return wrapper


signal.func = signal_func

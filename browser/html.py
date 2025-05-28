from typing import Callable


class DOMNode:
    def clear(self):
        pass

    def attach(self, e):
        pass

    def bind(self, name: str, handler: Callable):
        pass

    def remove(self, child):
        pass

    @property
    def parentElement(self):
        pass

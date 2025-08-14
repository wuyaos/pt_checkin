from abc import ABC, abstractmethod

from ..core.entry import SignInEntry


class Detail(ABC):
    @abstractmethod
    def get_details(self, entry: SignInEntry, config: dict) -> None:
        pass

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class InterventionEnum(str, Enum):
    # NOTE: this will be updated with new intervention types later. For now, this will only support toasts
    toast = "toast"


@dataclass
class Intervention:
    intervention_type: InterventionEnum
    intervention_message: str


class Plugin(ABC):
    @staticmethod
    @abstractmethod
    def get_plugin_name() -> str:
        """
        Name of the plugin (ex. "mindless editing", etc.)
        """
        pass

    @staticmethod
    @abstractmethod
    def detection_detected(action) -> bool:
        """
        Code that takes in logs and returns a boolean to determine whether a Level 3 action has been detected
        """
        pass

    @staticmethod
    @abstractmethod
    def intervention_action() -> Intervention:
        """
        Return an Intervention instance that explains the action to take if the associated Level 3 action has been detected
        """
        pass

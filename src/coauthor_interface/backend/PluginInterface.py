from abc import ABC, abstractmethod
from enum import Enum


class InterventionType(str, Enum):
    # NOTE: this will be updated with new intervention types later. For now, this will only support toasts
    toast = "toast"


class Intervention:
    def __init__(self, intervention_type: InterventionType, intervention_message: str):
        self.intervention_dict = {
            "intervention_type": intervention_type,
            "intervention_message": intervention_message,
        }


class Plugin(ABC):
    @abstractmethod
    def get_plugin_name(self) -> str:
        pass

    @abstractmethod
    def detection_detected(self, logs) -> bool:
        pass

    @abstractmethod
    def intervention_action(self) -> Intervention:
        pass

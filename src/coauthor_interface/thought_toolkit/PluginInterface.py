from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class InterventionEnum(str, Enum):
    # NOTE: this will be updated with new intervention types later. For now, this will only support toasts
    TOAST = "toast"
    NONE = "none"
    ALERT = "alert"
    MODIFY_QUERY = "modify_query"


@dataclass
class Intervention:
    intervention_type: InterventionEnum
    intervention_message: Optional[str] = None

    def __post_init__(self):
        """
        Ensures that an intervention message is provided for all intervention types
        except for 'NONE'. Raises a ValueError if the intervention type is not 'NONE'
        and the intervention message is empty or None.
        """

        if self.intervention_type != InterventionEnum.NONE and not self.intervention_message:
            raise ValueError(
                f"intervention_message is required when intervention_type is {self.intervention_type!r}"
            )


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

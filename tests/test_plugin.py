from coauthor_interface.backend.PluginInterface import (
    Intervention,
    InterventionEnum,
    Plugin,
)
import pytest



# A basic concrete implementation of Plugin for testing
class MockPlugin(Plugin):
    @staticmethod
    def get_plugin_name() -> str:
        return "MockPlugin"

    @staticmethod
    def detection_detected(action) -> bool:
        return action == ["This is true"]
    @staticmethod
    def intervention_action() -> Intervention:
        return Intervention(InterventionEnum.TOAST, "This is a toast message")
    
    @staticmethod
    def interventionless_action() -> Intervention:
        return Intervention(InterventionEnum.NONE)



def test_mock_plugin_name():
    plugin = MockPlugin()
    assert plugin.get_plugin_name() == "MockPlugin"


def test_detection_detected():
    plugin = MockPlugin()
    assert plugin.detection_detected(["This is true"])
    assert not plugin.detection_detected([])


def test_intervention_action():
    plugin = MockPlugin()
    intervention = plugin.intervention_action()
    assert isinstance(intervention, Intervention)
    assert intervention.intervention_type == InterventionEnum.TOAST
    assert intervention.intervention_message == "This is a toast message"


def test_interventionless_action():
    plugin = MockPlugin()
    intervention = plugin.interventionless_action()
    assert isinstance(intervention, Intervention)
    assert intervention.intervention_type == InterventionEnum.NONE
    # when the type is NONE, the message should default to None
    assert intervention.intervention_message is None

def test_missing_message_error_message():
    with pytest.raises(ValueError) as excinfo:
        # no message for a TOAST should blow up
        Intervention(InterventionEnum.TOAST)
    # it should start with our f-string prefix
    assert str(excinfo.value).startswith(
        "intervention_message is required when intervention_type is "
    )
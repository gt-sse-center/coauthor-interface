from src.coauthor_interface.backend.PluginInterface import (
    Plugin,
    Intervention,
    InterventionType,
)


# A basic concrete implementation of Plugin for testing
class MockPlugin(Plugin):
    def get_plugin_name(self) -> str:
        return "MockPlugin"

    def detection_detected(self, logs) -> bool:
        return logs == ["This is true"]

    def intervention_action(self) -> Intervention:
        return Intervention(InterventionType.toast, "This is a toast message")


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
    assert intervention.intervention_dict["intervention_type"] == InterventionType.toast
    assert (
        intervention.intervention_dict["intervention_message"]
        == "This is a toast message"
    )

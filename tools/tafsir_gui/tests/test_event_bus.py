from tools.tafsir_gui.core.events import EventBus, EventType, PipelineEvent


def test_event_bus_dispatch():
    bus = EventBus()
    received = []

    def handler(ev):
        received.append(ev)

    bus.subscribe(handler)
    bus.publish(PipelineEvent(EventType.LOG, "hello"))

    assert received
    assert received[0].message == "hello"

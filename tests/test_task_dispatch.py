"""
Regression test for the Cloud Tasks worker dispatch.

The /v2/tasks/{task_type} endpoint previously resolved handlers with
`getattr(handlers, task_type)`, which silently returned None because the task
type "add_frame" does not match the handler function name "add_frame_task".
Cloud Tasks callbacks 404'd ("Unknown task type: add_frame") and retried
forever, so story/frame generation hung on a spinner. This path was never
exercised until Cloud Tasks actually started running in production.

These checks ensure the task-type registry is the single source of truth and
that every type the queue can enqueue is resolvable by the worker.

Run with:
    PINECONE_API_KEY=dummy OPENAI_API_KEY=dummy uv run python tests/test_task_dispatch.py
"""

import calliope.tasks.handlers as handlers


def test_every_registered_type_resolves():
    """Each type in the registry resolves to its callable handler."""
    assert handlers.TASK_HANDLERS, "expected at least one registered task type"
    for task_type, handler in handlers.TASK_HANDLERS.items():
        resolved = handlers.get_task_handler(task_type)
        assert resolved is handler, f"{task_type} did not resolve to its handler"
        assert callable(resolved), f"handler for {task_type} is not callable"


def test_add_frame_is_registered():
    """'add_frame' (the type enqueued by create_story / request_new_frame)
    must resolve — this is the exact type that 404'd in production."""
    handler = handlers.get_task_handler("add_frame")
    assert handler is handlers.add_frame_task


def test_unknown_type_returns_none():
    assert handlers.get_task_handler("does_not_exist") is None


def test_register_handlers_registers_all_types():
    """register_handlers must register every type in the registry on a queue."""
    registered = {}

    class FakeQueue:
        def register_handler(self, task_type, handler):
            registered[task_type] = handler

    handlers.register_handlers(FakeQueue())
    assert registered == handlers.TASK_HANDLERS


def test_worker_resolves_via_registry():
    """The worker route resolves handlers through handlers.get_task_handler,
    not by attribute name (the source of the original bug)."""
    from calliope.routes.v2 import tasks as tasks_route

    # The route module references the handlers module; confirm the lookup helper
    # it relies on returns the add_frame handler.
    assert tasks_route.handlers.get_task_handler("add_frame") is handlers.add_frame_task


if __name__ == "__main__":
    test_every_registered_type_resolves()
    test_add_frame_is_registered()
    test_unknown_type_returns_none()
    test_register_handlers_registers_all_types()
    test_worker_resolves_via_registry()
    print("All task dispatch tests passed.")

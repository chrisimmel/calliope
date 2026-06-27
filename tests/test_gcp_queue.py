"""
Standalone validation for calliope.tasks.gcp_queue.GCPTaskQueue.

This exercises the GCP Cloud Tasks enqueue path *without* touching real GCP or
Firebase, by stubbing google.cloud.tasks_v2.CloudTasksClient and
calliope.storage.firebase.get_firebase_manager.

It guards against the two latent bugs that previously left the GCP task queue
unreachable in production (the silent ImportError fallback in
calliope.tasks.factory.get_task_queue masked both):

  Bug 1: `from protobuf import timestamp_pb2` -> ModuleNotFoundError at import
         time (correct module is google.protobuf). Caught here implicitly: if
         the module fails to import, this test cannot even load it.

  Bug 2: `datetime.now(datetime.timezone.utc)` in the delay_seconds > 0 branch
         -> AttributeError (datetime has no `timezone` attribute). Exercised
         explicitly by the delay_seconds=30 case below, which must build a valid
         protobuf Timestamp for schedule_time.

Run with:
    PINECONE_API_KEY=dummy OPENAI_API_KEY=dummy uv run python tests/test_gcp_queue.py
"""

import asyncio
from unittest import mock

from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

# Importing the module at all proves Bug 1 is fixed (no `protobuf` top-level
# module exists; the correct import is `from google.protobuf import ...`).
import calliope.tasks.gcp_queue as gcp_queue


def _make_queue(created_tasks):
    """Construct a GCPTaskQueue with the GCP client and Firebase fully stubbed.

    `created_tasks` is a list that captures every task dict handed to
    client.create_task so the test can assert on it (e.g. schedule_time).
    """
    fake_client = mock.MagicMock(name="CloudTasksClient")
    fake_client.queue_path.return_value = "projects/p/locations/l/queues/q"

    def _task_path(project, location, queue, task_id):
        return f"projects/{project}/locations/{location}/queues/{queue}/tasks/{task_id}"

    fake_client.task_path.side_effect = _task_path

    def _create_task(request):
        task = request["task"]
        created_tasks.append(task)
        # Cloud Tasks returns the created task with a fully-qualified name.
        # (`name` is a reserved MagicMock kwarg, so set the attribute directly.)
        response = mock.MagicMock()
        response.name = task["name"]
        return response

    fake_client.create_task.side_effect = _create_task

    # Firebase manager: create_task is awaited inside enqueue.
    fake_firebase = mock.MagicMock(name="FirebaseManager")
    fake_firebase.create_task = mock.AsyncMock(return_value=None)

    with mock.patch.object(
        tasks_v2, "CloudTasksClient", return_value=fake_client
    ), mock.patch.object(gcp_queue, "get_firebase_manager", return_value=fake_firebase):
        queue = gcp_queue.GCPTaskQueue(
            project="test-project",
            location="us-central1",
            queue_name="calliope-tasks",
            service_url="https://example.invalid",
        )
    return queue, fake_firebase


async def _run():
    payload = {"story_id": "abcdef123456", "client_id": "client-1"}

    # --- Case 1: no delay (the path production actually uses today) ---
    created = []
    queue, firebase = _make_queue(created)
    task_id = await queue.enqueue("add_frame", payload, delay_seconds=0)
    assert isinstance(task_id, str) and task_id, f"expected a task id, got {task_id!r}"
    assert "add_frame" in task_id, f"task id should be descriptive: {task_id!r}"
    assert firebase.create_task.await_count == 1, "Firebase task record not created"
    assert (
        "schedule_time" not in created[0]
    ), "no schedule_time should be set when delay_seconds == 0"
    print(f"[ok] delay=0  -> task_id={task_id}")

    # --- Case 2: delayed (exercises the timezone / timestamp_pb2 code path) ---
    created = []
    queue, firebase = _make_queue(created)
    task_id_delayed = await queue.enqueue("add_frame", payload, delay_seconds=30)
    assert isinstance(task_id_delayed, str) and task_id_delayed
    assert "schedule_time" in created[0], "delayed task must carry a schedule_time"
    schedule_time = created[0]["schedule_time"]
    assert isinstance(
        schedule_time, timestamp_pb2.Timestamp
    ), f"schedule_time must be a protobuf Timestamp, got {type(schedule_time)}"
    assert schedule_time.seconds > 0, "schedule_time should be a real epoch second"
    print(
        f"[ok] delay=30 -> task_id={task_id_delayed} "
        f"schedule_time.seconds={schedule_time.seconds}"
    )

    print("\nAll GCPTaskQueue validations passed.")


if __name__ == "__main__":
    asyncio.run(_run())

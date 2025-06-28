"""
Task processing endpoints for Google Cloud Tasks.

These endpoints receive HTTP requests from Google Cloud Tasks and
execute the appropriate task handlers.
"""

from fastapi import APIRouter, Request, HTTPException, Header, Depends
import logging
import json
from typing import Optional, Dict, Any

from calliope.tasks import handlers
from calliope.tasks.factory import configure_task_queue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


# --- Security Helpers ---


def verify_task_request(
    user_agent: Optional[str] = Header(None),
    x_cloudtasks_taskname: Optional[str] = Header(None),
    x_cloudtasks_taskretrycount: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """
    Verify that the request is coming from Google Cloud Tasks

    In production, you should secure this endpoint with more robust
    authentication mechanisms like IAM or a shared secret.

    Args:
        user_agent: User-Agent header from the request
        x_cloudtasks_taskname: Task name header
        x_cloudtasks_taskretrycount: Task retry count header

    Returns:
        Dictionary with task metadata
    """
    # Check for Cloud Tasks user agent
    if user_agent and not user_agent.startswith("Google-Cloud-Tasks"):
        logger.warning(f"Suspicious task request with User-Agent: {user_agent}")
        # In development, we might still allow this
        if not handlers.is_development_environment():
            raise HTTPException(status_code=403, detail="Forbidden")

    # Extract task metadata
    task_metadata = {}
    if x_cloudtasks_taskname:
        task_metadata["task_name"] = x_cloudtasks_taskname
    if x_cloudtasks_taskretrycount:
        try:
            task_metadata["retry_count"] = int(x_cloudtasks_taskretrycount)
        except ValueError:
            task_metadata["retry_count"] = 0

    return task_metadata


# --- Task Endpoints ---


@router.post("/{task_type}")
async def process_task(
    task_type: str,
    request: Request,
    task_metadata: Dict[str, Any] = Depends(verify_task_request),
):
    """
    Process a task of the specified type

    This endpoint is called by Google Cloud Tasks when a task is ready to be executed.
    It verifies the request, loads the payload, and invokes the appropriate handler.

    Args:
        task_type: The type of task to process
        request: The HTTP request object
        task_metadata: Metadata extracted from headers
    """
    # Get the payload from the request
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload in task request")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Log task information
    logger.info(f"Processing task of type '{task_type}' with metadata: {task_metadata}")

    # Check if the task handler exists
    handler_func = getattr(handlers, task_type, None)
    if not handler_func:
        logger.error(f"Unknown task type: {task_type}")
        raise HTTPException(status_code=404, detail=f"Unknown task type: {task_type}")

    # Add task metadata to payload
    payload["_task_metadata"] = task_metadata

    try:
        # Execute the handler
        result = await handler_func(payload)
        logger.info(f"Task '{task_type}' completed successfully")

        # Return the result
        return {"status": "success", "task_type": task_type, "result": result}
    except Exception as e:
        logger.exception(f"Error processing task '{task_type}': {str(e)}")

        # Determine if this is a retryable error
        # You could implement specific error types for different retry behaviors
        is_retryable = not isinstance(e, ValueError)

        # For retryable errors in production, Cloud Tasks will retry based on the queue config
        # In development, we might want to raise immediately to see the error
        if is_retryable:
            # Set status code to trigger a retry in Cloud Tasks
            # 429 Too Many Requests or 503 Service Unavailable are typically used
            status_code = 503
            detail = f"Retryable error processing task: {str(e)}"
        else:
            # Non-retryable error
            status_code = 400
            detail = f"Non-retryable error processing task: {str(e)}"

        raise HTTPException(status_code=status_code, detail=detail)


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Get the status of a task

    Args:
        task_id: The ID of the task to check
    """
    # Configure the task queue
    task_queue = configure_task_queue()

    # Get the task status
    status = await task_queue.get_task_status(task_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return status

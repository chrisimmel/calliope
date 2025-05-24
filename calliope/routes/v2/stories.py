from fastapi import APIRouter, HTTPException, Request # Removed Request for now, add if needed
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone # For date_created

# Import create_cuid from the existing utils
from calliope.utils.id import create_cuid 
from calliope.tables import Story 

# --- Pydantic Models (largely the same, ensuring consistency) ---

class Snippet(BaseModel):
    data_type: str
    content: str    
    metadata: Dict[str, Any] = {}

class CreateStoryRequest(BaseModel):
    client_id: Optional[str] = None # Maps to created_for_sparrow_id
    title: Optional[str] = None     # Can be set initially, or later by async processing
    strategy: Optional[str] = None  # Maps to strategy_name
    snippets: List[Snippet] = [] 

class AddSnippetsRequest(BaseModel):
    snippets: List[Snippet]

class CreateStoryResponse(BaseModel):
    story_id: str # This will be the cuid
    message: str

# --- Router Setup ---
router = APIRouter(prefix="/v2/stories", tags=["stories_v2"])

# --- Endpoint Implementations ---

@router.post("/", response_model=CreateStoryResponse)
async def create_story(request_data: CreateStoryRequest):
    try:
        story = Story.create_new(
            strategy_name=request_data.strategy,
            created_for_sparrow_id=request_data.client_id,
            title=request_data.title,
        )
        new_story_cuid = story.cuid
        await put_story(story)
    except Exception as e:
        print(f"Error creating story in database: {e}") # Basic logging
        raise HTTPException(status_code=500, detail=f"Failed to create story in database: {str(e)}")

    message_parts = [f"Story {new_story_cuid} created."]
    
    if request_data.snippets:
        # TODO: Implement asynchronous snippet processing.
        # 1. Define a task function (e.g., process_initial_snippets_task).
        # 2. This task will take story_cuid and the list of snippets.
        # 3. Inside the task:
        #    - Fetch the story by story_cuid.
        #    - For each snippet:
        #        - Potentially save snippet data (e.g., if it's an image/audio file).
        #        - Prepare data for strategy input.
        #    - Invoke the appropriate story strategy (similar to v1's handle_frames_request)
        #      to generate the first frame(s) based on these snippets.
        #    - Update the story (e.g., title, slug if generated) and save new StoryFrame records.
        #    - Send notifications if the WebSocket system is ready.
        #
        # Example of adding to a conceptual background_tasks (FastAPI's BackgroundTasks):
        # from fastapi import BackgroundTasks
        # async def create_story(request_data: CreateStoryRequest, background_tasks: BackgroundTasks):
        # ...
        # background_tasks.add_task(your_async_processing_function, new_story_cuid, request_data.snippets)

        print(f"Story {new_story_cuid}: {len(request_data.snippets)} initial snippets received and will be queued for asynchronous processing.")
        message_parts.append("Initial snippets will be processed asynchronously.")
    else:
        print(f"Story {new_story_cuid} created without initial snippets.")

    return CreateStoryResponse(story_id=new_story_cuid, message=" ".join(message_parts))


@router.post("/{story_id}/snippets/")
async def add_snippets(story_id: str, request_data: AddSnippetsRequest):
    # Placeholder for adding snippets to an existing story
    # TODO: Check if story_id exists using cuid
    story = await Story.objects().where(Story.cuid == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail=f"Story with id {story_id} not found")

    # TODO: Add snippets to a task queue for asynchronous processing
    print(f"Received {len(request_data.snippets)} snippets for story {story_id}. Queued for processing.")
    return {"message": "Snippets received and queued for processing."}


@router.get("/{story_id}/updates")
async def get_story_updates(story_id: str):
    # Placeholder for WebSocket/SSE endpoint
    # TODO: Implement WebSocket or SSE logic
    pass


@router.get("/{story_id}/")
async def get_story_state(story_id: str):
    # Placeholder for retrieving story state
    # TODO: Fetch and return current story state from the database
    try:
        story = await Story.objects().where(Story.cuid == story_id).first()
        if not story:
            raise HTTPException(status_code=404, detail=f"Story with id {story_id} not found")
        return story.to_dict() # Or a Pydantic model for the response
    except Exception as e:
        # Log the exception e
        print(f"Error retrieving story: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve story: {str(e)}")


@router.get("/")
async def list_stories(client_id: Optional[str] = None):
    # Placeholder for listing stories
    # TODO: Fetch and return list of stories, optionally filtered by client_id
    query = Story.select()
    if client_id:
        query = query.where(Story.created_for_sparrow_id == client_id)
    
    stories = await query.order_by(Story.date_created, ascending=False)
    return [story.to_dict() for story in stories] # Or a Pydantic model for the list response

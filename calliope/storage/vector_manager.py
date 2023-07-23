import os
from typing import cast, List, Optional, Sequence

from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Pinecone
from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
import pinecone

from calliope.models import KeysModel
from calliope.tables.story import Story, StoryFrame
from calliope.utils.google import get_cloud_environment


"""
sentence_transformer_model = None

def get_sentence_transformer_model() -> SentenceTransformer:
    global sentence_transformer_model
    if sentence_transformer_model:
        return sentence_transformer_model

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device != "cuda":
        print(
            f"You are using {device}. This is much slower than using "
            "a CUDA-enabled GPU."
        )

    # all-MiniLM-L6-v2 yields a 384-dimensional vector.
    sentence_transformer_model = SentenceTransformer("all-MiniLM-L6-v2", device=device)

    return sentence_transformer_model
"""

# The maximum size of a chunk of text to be vectorized.
# Determined by the SentenceTransformers model.
chunk_size_limit = 256
max_chunk_overlap = 20


async def _get_story_frames(
    story_cuid: str, include_indexed_for_search: bool = False
) -> Sequence[StoryFrame]:
    story: Optional[Story] = (
        await Story.objects().where(Story.cuid == story_cuid).first().run()
    )
    if not story:
        raise Exception(f"Unknown story: {story_cuid}")

    frames = await story.get_frames(
        include_images=False, include_indexed_for_search=include_indexed_for_search
    )
    if frames:
        print(f"Need to index {len(frames)} frames of story {story.title}.")
    else:
        print(f"No frames are unindexed for story {story.title}.")

    return frames


async def _get_frame_documents(
    frames: Sequence[StoryFrame], story_cuid: Optional[str] = None
) -> List[Document]:
    frame_texts = [frame.text or "" for frame in frames]
    env = get_cloud_environment()
    frame_metadatas = [
        {
            "story_cuid": story_cuid if story_cuid else frame.story.cuid,
            "frame_number": frame.number,
            "frame_id": str(frame.id),
            "env": env,
        }
        for frame in frames
    ]

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size_limit,
        chunk_overlap=max_chunk_overlap,
        length_function=len,
    )

    frame_documents = text_splitter.create_documents(frame_texts, frame_metadatas)
    print(f"Generated {len(frame_documents)} documents.")

    return frame_documents


async def _send_story_to_pinecone(
    story_cuid: str, keys: KeysModel, include_indexed_for_search: bool = False
) -> Pinecone:
    frames = await _get_story_frames(
        story_cuid, include_indexed_for_search=include_indexed_for_search
    )
    documents = await _get_frame_documents(frames, story_cuid)
    model_name = "all-MiniLM-L6-v2"
    embeddings = SentenceTransformerEmbeddings(model_name=model_name)
    ids = [document.metadata["frame_id"] for document in documents]

    pinecone.init(
        api_key=keys.pinecone_api_key, environment=os.environ.get("PINECONE_ENVIRONMENT")
    )
    index_name = os.environ.get("SEMANTIC_SEARCH_INDEX")

    pinecone_vector_store = Pinecone.from_texts(
        [document.page_content for document in documents],
        embeddings,
        index_name=index_name,
        metadatas=[document.metadata for document in documents],
        ids=ids,
    )
    for frame in frames:
        if not frame.indexed_for_search:
            frame.indexed_for_search = True
            await frame.save().run()

    return pinecone_vector_store


async def _get_frames(
    max_frames: int = 0, include_indexed_for_search: bool = True
) -> Sequence[StoryFrame]:
    """
    Gets the requested frames.

    Args:
        max_frames: the maximum number of frames to include.
        If negative, takes the last N frames.
        If zero (the default), takes all.
    """
    qs = StoryFrame.objects(StoryFrame.story)

    if not include_indexed_for_search:
        qs = qs.where(StoryFrame.indexed_for_search.eq(False))

    if max_frames > 0:
        # First n frames.
        qs = qs.order_by(StoryFrame.number).limit(max_frames)
    elif max_frames < 0:
        # Last n frames. These are reversed, so need to reverse again after
        # retrieved.
        qs = qs.order_by(StoryFrame.number, ascending=False).limit(-max_frames)
    else:
        # All frames.
        qs = qs.order_by(StoryFrame.number)

    frames = await qs.output(load_json=True).run()

    if max_frames < 0:
        # Rows are sorted in reverse frame order, so reverse them.
        frames.reverse()

    return frames


async def index_unindexed_frames(
    keys: Optional[KeysModel] = None, max_frames: int = 1000
) -> int:
    """
    Send max_frames unindexed story frames to the semantic search index.
    Designed to be run as a regularly scheduled batch process.
    Does almost no work if there is nothing to index.
    """
    if not keys or not keys.pinecone_api_key:
        pinecone_api_key = os.environ.get("PINECONE_API_KEY")
        keys = KeysModel(pinecone_api_key=pinecone_api_key)

    frames = await _get_frames(max_frames=max_frames, include_indexed_for_search=False)

    if not frames:
        print("No frames are unindexed.")
        return 0

    num_frames = len(frames)
    print(f"Indexing {num_frames} frames...")

    documents = await _get_frame_documents(frames)
    model_name = "all-MiniLM-L6-v2"
    embeddings = SentenceTransformerEmbeddings(model_name=model_name)
    ids = [document.metadata["frame_id"] for document in documents]

    pinecone.init(
        api_key=keys.pinecone_api_key, environment=os.environ.get("PINECONE_ENVIRONMENT")
    )
    index_name = os.environ.get("SEMANTIC_SEARCH_INDEX")

    pinecone_vector_store = Pinecone.from_texts(
        [document.page_content for document in documents],
        embeddings,
        index_name=index_name,
        metadatas=[document.metadata for document in documents],
        ids=ids,
    )
    print(f"Distance strategy is {pinecone_vector_store.distance_strategy}")

    for frame in frames:
        if not frame.indexed_for_search:
            frame.indexed_for_search = True
            await frame.save().run()

    return num_frames


async def send_all_stories_to_pinecone(keys: Optional[KeysModel] = None) -> None:
    if not keys or not keys.pinecone_api_key:
        pinecone_api_key = os.environ.get("PINECONE_API_KEY")
        keys = KeysModel(pinecone_api_key=pinecone_api_key)

    stories = cast(
        Sequence[Story],
        await Story.objects().order_by(Story.date_updated, ascending=False),
    )

    for story in stories:
        print(f"Sending story {story.cuid} to Pinecone ({story.title})...")
        await _send_story_to_pinecone(story.cuid, keys)


def semantic_search(
    query: str, pinecone_api_key: Optional[str] = None, max_results: int = 20
) -> Sequence[Document]:
    if not pinecone_api_key:
        pinecone_api_key = os.environ.get("PINECONE_API_KEY")

    pinecone.init(
        api_key=pinecone_api_key, environment=os.environ.get("PINECONE_ENVIRONMENT")
    )
    index_name = os.environ.get("SEMANTIC_SEARCH_INDEX")

    model_name = "all-MiniLM-L6-v2"
    embeddings = SentenceTransformerEmbeddings(model_name=model_name)
    docsearch = Pinecone.from_existing_index(index_name, embeddings)

    # For now, all cloud environments share the same (free) Pinecone index,
    # so we need to discriminate among them by filtering in the query.
    cloud_env = get_cloud_environment()
    filter = {"env": {"$eq": cloud_env}}
    documents_and_scores = docsearch.similarity_search_with_score(
        query, k=max_results, filter=filter
    )

    return documents_and_scores


"""
from calliope.storage.vector_manager import send_all_stories_to_pinecone

story_id = "clk9a26hp00016ont4tjubyew"

import asyncio
from calliope.models.keys import KeysModel 

keys = KeysModel(pinecone_api_key="3cec2c81-5836-4dc0-8fe5-077a408d05f9")

vs = None

async def mains():
    global vs
    vs = await send_all_stories_to_pinecone(keys)

loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(mains())
finally:
    loop.close()

"""

"""
import asyncio
from calliope.models.keys import KeysModel 
from calliope.storage.vector_manager import index_unindexed_frames

keys = KeysModel(pinecone_api_key="3cec2c81-5836-4dc0-8fe5-077a408d05f9")

loop = asyncio.get_event_loop()
try:
    loop.run_until_complete(index_unindexed_frames(keys))
finally:
    loop.close()

"""

import argparse
import asyncio
from calliope.storage.vector_manager import index_frames, semantic_search


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="index_stories")
    parser.add_argument(
        "--max_frames",
        required=False,
        default=1000,
        help="The maximum number of frames to index.",
    )

    parser.add_argument(
        "--force",
        required=False,
        default="false",
        help=(
            "If true, clear the indexed flag for all frames and "
            "begin reindexing from scratch."
        ),
    )

    parser.add_argument(
        "--ping",
        required=False,
        default="true",
        help=("If true, also ping Pinecone by performing a semantic search."),
    )
    args = parser.parse_args()

    max_frames = int(args.max_frames)
    force = args.force == "true"
    ping = args.ping == "true"

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(index_frames(max_frames=max_frames, force_reindex=force))
    finally:
        loop.close()

    if ping:
        # Perform a semantic search just to keep Pinecone active.
        # (Free indexes are deleted after a week of inactivity.)
        semantic_search("listen to my heartbeat")

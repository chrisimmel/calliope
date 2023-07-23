import argparse
import asyncio
from calliope.storage.vector_manager import index_unindexed_frames


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="index_stories")
    parser.add_argument(
        "--max_frames",
        required=False,
        default=1000,
        help="The maximum number of frames to index.",
    )
    args = parser.parse_args()

    max_frames = args.max_frames

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(index_unindexed_frames(max_frames=max_frames))
    finally:
        loop.close()

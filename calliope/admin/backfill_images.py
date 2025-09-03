"""
Admin commands for managing image backfill operations.

Usage examples:
- python -m calliope.admin.backfill_images scan --limit 100
- python -m calliope.admin.backfill_images process --max-items 20
- python -m calliope.admin.backfill_images status
"""

import asyncio
import os
import sys

# Add the parent directory to the path so we can import calliope modules
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from calliope.models import KeysModel
from calliope.utils.image_backfill import (
    ImageBackfillQueue,
    scan_and_queue_legacy_frames,
)
from calliope.workers.image_backfill_worker import process_backfill_queue


async def show_queue_status():
    """Show the current status of the backfill queue."""
    try:
        from calliope.storage.firebase import get_firebase_manager

        firebase_manager = get_firebase_manager()
        collection_ref = firebase_manager.db.collection(
            ImageBackfillQueue.COLLECTION_NAME
        )

        # Get all documents
        docs = collection_ref.stream()
        queue_items = []
        for doc in docs:
            item_data = doc.to_dict()
            item_data["id"] = doc.id
            queue_items.append(item_data)

        if not queue_items:
            print("✅ Backfill queue is empty")
            return

        status_counts = {}
        for item_data in queue_items:
            status = item_data.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        print("📊 Backfill Queue Status:")
        for status, count in status_counts.items():
            print(f"   {status}: {count}")

        print(f"   Total items: {len(queue_items)}")

        # Show some recent pending items
        pending_items = [item for item in queue_items if item.get("status") == "pending"]

        if pending_items:
            print("\n🔍 Recent pending items:")
            for item_data in pending_items[:5]:
                story_cuid = item_data.get("story_cuid", "unknown")
                frame_number = item_data.get("frame_number", "unknown")
                retry_count = item_data.get("retry_count", 0)
                print(f"   {story_cuid} frame {frame_number} (retries: {retry_count})")

    except Exception as e:
        print(f"❌ Failed to get queue status: {e}")


async def clear_failed_items():
    """Clear permanently failed items from the queue."""
    try:
        from calliope.storage.firebase import get_firebase_manager

        firebase_manager = get_firebase_manager()
        collection_ref = firebase_manager.db.collection(
            ImageBackfillQueue.COLLECTION_NAME
        )

        # Get failed items
        query = collection_ref.where("status", "==", "failed")
        failed_docs = query.stream()

        failed_items = [doc.id for doc in failed_docs]

        if not failed_items:
            print("✅ No failed items to clear")
            return

        print(f"🗑️  Clearing {len(failed_items)} failed items...")
        for item_id in failed_items:
            doc_ref = collection_ref.document(item_id)
            doc_ref.delete()

        print(f"✅ Cleared {len(failed_items)} failed items")

    except Exception as e:
        print(f"❌ Failed to clear failed items: {e}")


async def main():
    """Main entry point for admin commands."""
    import argparse

    parser = argparse.ArgumentParser(description="Image backfill admin commands")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Scan command
    scan_parser = subparsers.add_parser(
        "scan", help="Scan for legacy frames without images"
    )
    scan_parser.add_argument(
        "--limit", type=int, default=50, help="Maximum frames to scan"
    )

    # Process command
    process_parser = subparsers.add_parser("process", help="Process backfill queue")
    process_parser.add_argument(
        "--max-items", type=int, default=10, help="Maximum items to process"
    )
    process_parser.add_argument(
        "--timeout", type=int, default=60, help="Timeout per item"
    )

    # Status command
    subparsers.add_parser("status", help="Show queue status")

    # Clear command
    subparsers.add_parser("clear-failed", help="Clear failed items from queue")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Test Firebase connection by getting the manager
    try:
        from calliope.storage.firebase import get_firebase_manager

        get_firebase_manager()
        print("✅ Firebase connection established")
    except Exception as e:
        print(f"❌ Could not connect to Firebase: {e}")
        sys.exit(1)

    try:
        if args.command == "status":
            await show_queue_status()

        elif args.command == "clear-failed":
            await clear_failed_items()

        elif args.command == "scan":
            keys = KeysModel.from_env()
            if not keys.openai_api_key:
                print("❌ OPENAI_API_KEY is required for scanning")
                sys.exit(1)

            print(f"🔍 Scanning for legacy frames (limit: {args.limit})...")
            queued_count = await scan_and_queue_legacy_frames(args.limit)
            print(f"✅ Queued {queued_count} legacy frames for backfill")

        elif args.command == "process":
            print(f"⚙️  Processing backfill queue (max items: {args.max_items})...")
            processed_count = await process_backfill_queue(args.max_items, args.timeout)
            print(f"✅ Processed {processed_count} items")

    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
    except Exception as e:
        print(f"❌ Command failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

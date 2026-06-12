"""
run_pipeline.py

Entry point for running the full automation pipeline:
  Legal Content Source -> AI Processing -> Summary -> Key Info ->
  Audio Generation -> Knowledge Centre Card (stored in SQLite)

Usage:
    python run_pipeline.py            # process topics that changed / are new
    python run_pipeline.py --force    # force regenerate everything
"""
import sys
import argparse

from backend.config import TOPICS
from backend.database import init_db, upsert_topic_card
from backend.pipeline import process_topic
from backend.audio_generator import generate_audio


def main():
    parser = argparse.ArgumentParser(description="Run LegalX AI knowledge generation pipeline")
    parser.add_argument("--force", action="store_true", help="Force regenerate all cards and audio")
    parser.add_argument("--topic", type=str, default=None, help="Only process a single topic_id")
    args = parser.parse_args()

    init_db()

    topic_ids = [args.topic] if args.topic else list(TOPICS.keys())

    for topic_id in topic_ids:
        if topic_id not in TOPICS:
            print(f"[SKIP] Unknown topic_id: {topic_id}")
            continue

        print(f"\n=== Processing: {TOPICS[topic_id]['name']} ({topic_id}) ===")
        try:
            from backend.source_fetcher import fetch_topic_source
            fetch_result = fetch_topic_source(topic_id)
            print(f"  -> Source fetch: {fetch_result['status']}"
                  + (f" ({fetch_result['source_url']})" if fetch_result['source_url'] else ""))

            result = process_topic(topic_id, force=args.force)
            card = result["card"]
            print(f"  -> Short description: {card['short_description']}")
            print(f"  -> Summary length: {len(card['summary'].split())} words")
            print(f"  -> Key rights: {len(card['key_rights'])} items")
            print(f"  -> Provisions: {len(card['important_provisions'])} items")
            print(f"  -> Penalties: {len(card['penalties'])} items")
            print(f"  -> Who benefits: {len(card['who_benefits'])} items")

            # Audio generation
            audio_path = generate_audio(topic_id, card["summary"], force=result["needs_audio"])
            print(f"  -> Audio: {audio_path}")

            upsert_topic_card(
                topic_id=topic_id,
                name=TOPICS[topic_id]["name"],
                card=card,
                audio_path=audio_path,
                source_hash=result["source_hash"],
            )
            print(f"  -> Stored in database. (regenerated: {result['needs_audio']})")

        except Exception as e:
            print(f"  -> ERROR: {e}", file=sys.stderr)

    print("\nPipeline run complete.")


if __name__ == "__main__":
    main()
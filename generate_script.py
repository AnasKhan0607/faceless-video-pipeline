#!/usr/bin/env python3
"""
Script Generator for TikTok Pipeline
=====================================
Generates dialogue scripts for the video pipeline.

Usage: 
  python generate_script.py --topic "recursion" --output scripts/ep002.json
  python generate_script.py --topic "what is docker" --characters peter,trump
"""

import argparse
import json
from pathlib import Path

# Script templates for different character combos
TEMPLATES = {
    "peter_stewie": {
        "characters": ["peter", "stewie"],
        "style": "Peter explains simply, Stewie is condescending but impressed",
    },
    "peter_trump": {
        "characters": ["peter", "trump"],
        "style": "Peter explains, Trump makes it about himself",
    },
}

def generate_script_prompt(topic: str, characters: list) -> str:
    """Generate a prompt for Claude/GPT to create a script."""
    char_str = " and ".join(characters)
    
    return f"""Generate a TikTok script where {char_str} explain "{topic}" in a funny, educational way.

Requirements:
- 8-12 lines of dialogue total
- Each line should be 1-2 sentences max
- Keep it under 60 seconds when spoken
- Make it entertaining but actually teach something
- End with a punchline or callback

Output as JSON:
{{
  "episode": "ep_TOPIC",
  "title": "TITLE",
  "characters": {json.dumps(characters)},
  "dialogue": [
    {{
      "id": 1,
      "character": "{characters[0]}",
      "line": "...",
      "pause_after_ms": 400
    }},
    ...
  ]
}}

Use pause_after_ms of 300-500 between lines for natural pacing.
"""


def create_example_script(topic: str, episode_id: str, characters: list) -> dict:
    """Create a template script structure."""
    return {
        "episode": episode_id,
        "title": topic.title(),
        "characters": characters,
        "dialogue": [
            {
                "id": 1,
                "character": characters[0],
                "line": f"So let me tell you about {topic}...",
                "pause_after_ms": 400
            },
            {
                "id": 2,
                "character": characters[1] if len(characters) > 1 else characters[0],
                "line": "This should be interesting.",
                "pause_after_ms": 300
            },
            # Add more lines here...
        ],
        "_note": "This is a template. Fill in the dialogue or use AI to generate it.",
        "_prompt": generate_script_prompt(topic, characters)
    }


def main():
    parser = argparse.ArgumentParser(description="Generate script for TikTok pipeline")
    parser.add_argument("--topic", required=True, help="Topic to explain")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--characters", default="peter,stewie", 
                        help="Comma-separated character names")
    parser.add_argument("--episode", help="Episode ID (default: auto-generated)")
    args = parser.parse_args()
    
    characters = [c.strip().lower() for c in args.characters.split(",")]
    
    # Generate episode ID from topic if not provided
    episode_id = args.episode or "ep_" + args.topic.lower().replace(" ", "_")[:20]
    
    # Create template script
    script = create_example_script(args.topic, episode_id, characters)
    
    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(script, indent=2))
    
    print(f"✅ Template created: {output_path}")
    print(f"\n📝 AI Prompt to generate full script:\n")
    print(script["_prompt"])
    print(f"\nEdit {output_path} with the generated dialogue, then run:")
    print(f"  python pipeline.py --script {args.output}")


if __name__ == "__main__":
    main()

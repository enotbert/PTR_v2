"""Export FastAPI OpenAPI schema to a JSON file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.main import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export backend OpenAPI schema as JSON")
    parser.add_argument(
        "--output",
        default="openapi.json",
        help="Output path for generated OpenAPI JSON (default: openapi.json)",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    schema = create_app().openapi()
    output_path.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

DEFAULT_SAMPLE_PATH = Path("sample_input.txt")
DEFAULT_INTRO = "Prepared for contributors, internal stakeholders, and partner teams."


@dataclass
class Section:
    name: str
    bullets: list[str] = field(default_factory=list)


@dataclass
class NewsletterDraft:
    title: str
    intro: str
    sections: list[Section]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a simple Markdown newsletter from text input."
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Path to a plain-text input file.",
    )
    parser.add_argument(
        "--text",
        help="Raw input text in the same format as the sample file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the generated Markdown file.",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Use the bundled sample input file.",
    )
    return parser.parse_args()


def load_input_text(args: argparse.Namespace) -> str:
    if args.text:
        return args.text

    if args.input:
        return read_text_file(args.input)

    if args.sample or DEFAULT_SAMPLE_PATH.exists():
        return read_text_file(DEFAULT_SAMPLE_PATH)

    raise ValueError("Provide --input, --text, or --sample to generate a newsletter.")


def read_text_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    return path.read_text(encoding="utf-8")


def parse_newsletter(raw_text: str) -> NewsletterDraft:
    title = "Maintainer Weekly Brief"
    intro = DEFAULT_INTRO
    sections: list[Section] = []
    current_section: Section | None = None

    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        lowered = stripped.lower()
        if lowered.startswith("title:"):
            value = stripped.split(":", 1)[1].strip()
            if value:
                title = value
            continue

        if lowered.startswith("intro:"):
            value = stripped.split(":", 1)[1].strip()
            if value:
                intro = value
            continue

        if stripped.startswith("[") and stripped.endswith("]"):
            section_name = stripped[1:-1].strip()
            if not section_name:
                continue
            current_section = Section(name=section_name)
            sections.append(current_section)
            continue

        if stripped.startswith("- "):
            if current_section is None:
                current_section = Section(name="Updates")
                sections.append(current_section)
            current_section.bullets.append(stripped[2:].strip())
            continue

        if current_section is None and intro == DEFAULT_INTRO:
            intro = stripped
            continue

        if current_section is None:
            current_section = Section(name="Updates")
            sections.append(current_section)

        current_section.bullets.append(stripped)

    if not sections:
        raise ValueError(
            "No sections were found. Add section headers like [AI] and bullet lines like '- Update'."
        )

    return NewsletterDraft(title=title, intro=intro, sections=sections)


def render_markdown(newsletter: NewsletterDraft) -> str:
    lines = [
        f"# {newsletter.title}",
        f"_Generated on {date.today().isoformat()}_",
        "",
        newsletter.intro,
        "",
    ]

    for section in newsletter.sections:
        lines.append(f"## {section.name}")
        for bullet in section.bullets:
            lines.append(f"- {bullet}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    try:
        args = parse_args()
        raw_text = load_input_text(args)
        newsletter = parse_newsletter(raw_text)
        markdown = render_markdown(newsletter)

        if args.output:
            args.output.write_text(markdown, encoding="utf-8")
            print(f"Newsletter written to {args.output}")
            return 0

        print(markdown)
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

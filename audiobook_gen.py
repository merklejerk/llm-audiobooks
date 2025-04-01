#!/usr/bin/env python3

import argparse
import os
import json
import re
from pathlib import Path
import openai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure OpenAI API from environment variables
openai.api_key = os.environ.get("OPENAI_API_KEY")
LLM_MODEL = os.environ.get("OPENAI_LLM_MODEL", "gpt-4")
TTS_MODEL = os.environ.get("OPENAI_TTS_MODEL", "tts-1")
TTS_VOICE = os.environ.get("OPENAI_TTS_VOICE", "nova")

def load_progress_checkpoint(book_id):
    """Load the progress checkpoint for a specific book from disk."""
    progress_file = Path(f"progress/{book_id}.json")
    if progress_file.exists():
        with open(progress_file, "r") as f:
            return json.load(f)
    return r"""This is the start of the story. We need to write chapter 1."""

def save_progress_checkpoint(book_id, progress):
    """Save the progress checkpoint to disk."""
    progress_dir = Path("progress")
    progress_dir.mkdir(exist_ok=True)
    
    with open(progress_dir / f"{book_id}.json", "w") as f:
        json.dump(progress, f, indent=2)

def load_spec(spec_file):
    """Load the book specification from file."""
    with open(spec_file, "r") as f:
        return f.read()

def extract_sections(response):
    """Extract all tagged sections from the response.
    Returns a dict mapping tag names (lowercase) to their content.
    A tag is defined as: [tag] then content until the next [tag] or the end of the string.
    """
    sections = {}
    pattern = r"(?i)\[(\w+)\]\s*(.*?)(?=\n*\[\w+\]|$)"
    for match in re.finditer(pattern, response, re.DOTALL):
        tag = match.group(1).strip().lower()
        content = match.group(2).strip()
        sections[tag] = content
    return sections

def extract_chapter_content(sections):
    """Extract chapter content from tagged sections."""
    return sections.get("chapter")

def extract_progress_checkpoint(sections):
    """Extract progress checkpoint from tagged sections."""
    return sections.get("progress") or None

def generate_chapter(book_id, spec, progress_checkpoint):
    """Generate the next chapter using OpenAI API."""
    prompt = f"""
BOOK SPECIFICATION:
{spec}

LAST PROGRESS CHECKPOINT:
{progress_checkpoint}
"""
    response = openai.responses.create(
        model=LLM_MODEL,
        instructions=r"""
You are an expert storyteller AI that creates detailed, engaging book chapters. You will be tasked to write successive chapters of a book.
For each prompt, you will be given a book specification and a progress checkpoint from the last chapter you wrote.

You should always do the following:
1. Write the next chapter of the book based on the specification and the last progress checkpoint. Strive for continuity and coherence with the previous chapters.
2. Begin the chapter section with the tag `[chapter]`. Do not use a closing tag; the start of any new tag (e.g. [progress]) marks its end.
3. After the chapter, prefix the progress checkpoint with `[progress]`. The progress checkpoint should include:
    - A line stating: "I just wrote Chapter X", where "X" is the chapter number.
    - An estimated number of chapters remaining.
    - How we got to this point in the story from the previous chapter.
    - a summary of the chapter, including any significant events and character developments. Name characters directly.
    - An indication of where we are in the greater story, character arcs, and unresolved plot points.
    - A suggestion for where to go in the next chapter and beyond.
""",
        input=prompt,
        max_output_tokens=4000,
        temperature=0.7
    )
    
    # Concatenate all text parts from the response output using comprehension and join
    full_text = "".join(item.text for msg in response.output if msg.type == 'message' for item in msg.content if item.type == 'output_text')
    return full_text

def generate_audio(book_id, chapter_number, chapter_content):
    """Generate an audio file from the chapter content."""
    chapters_dir = Path("chapters")
    chapters_dir.mkdir(exist_ok=True)
    
    audio_file_path = chapters_dir / f"{book_id}_chapter_{chapter_number}.mp3"
    
    with openai.audio.speech.with_streaming_response.create(
        model=TTS_MODEL,
        voice=TTS_VOICE,
        input=chapter_content,
        instructions="You are a dramatic audiobook narrator.",
        response_format="wav",
    ) as response:
        response.stream_to_file(str(audio_file_path))
    return audio_file_path

def save_chapter_text(book_id, chapter_number, chapter_content):
    """Save the chapter text to disk."""
    chapters_dir = Path("chapters")
    chapters_dir.mkdir(exist_ok=True)
    
    text_file_path = chapters_dir / f"{book_id}_chapter_{chapter_number}.md"
    
    with open(text_file_path, "w") as f:
        f.write(chapter_content)
    
    return text_file_path

def extract_book_id_from_spec_file(spec_file_path):
    """Extract book ID from the specification file path.
    Uses the part of the filename before the first period as the book ID."""
    path = Path(spec_file_path)
    filename = path.name  # Get full filename
    return filename.split('.')[0]  # Split by period and take first part

def main():
    parser = argparse.ArgumentParser(description="Generate audiobooks using OpenAI APIs")
    parser.add_argument("spec_file", help="Path to the specification file")
    args = parser.parse_args()
    
    # Extract book ID from spec file path
    book_id = extract_book_id_from_spec_file(args.spec_file)
    print(f"Using book ID: {book_id}")
    
    # Step 1: Load book specification
    spec = load_spec(args.spec_file)
    
    # Step 2: Load progress checkpoint
    progress_checkpoint = load_progress_checkpoint(book_id)
    
    # Step 3 & 4: Generate next chapter using LLM
    response = generate_chapter(book_id, spec, progress_checkpoint)
    
    # Extract chapter content and progress checkpoint
    sections = extract_sections(response)
    chapter_content = extract_chapter_content(sections)
    new_progress_checkpoint = extract_progress_checkpoint(sections)
    
    if not chapter_content or not new_progress_checkpoint:
        print("Error: Could not extract chapter content or progress checkpoint from response.")
        print(sections)
        return
    
    # Step 5: Save progress checkpoint
    save_progress_checkpoint(book_id, new_progress_checkpoint)
    
    # Step 6: Print chapter content
    print("\n=== New Chapter ===\n")
    print(chapter_content)
    # Added progress printing after chapter content
    print("\n--- Progress checkpoint ---")
    print(f"Progress: {new_progress_checkpoint}")
    print("\n==================\n")
    
    # Determine chapter number based on existing files
    chapter_count = len(list(Path("chapters").glob(f"{book_id}_chapter_*.md")))
    chapter_number = chapter_count + 1
    
    # Step 7: Generate audio
    audio_file = generate_audio(book_id, chapter_number, chapter_content)
    
    # Step 8: Save chapter text
    text_file = save_chapter_text(book_id, chapter_number, chapter_content)
    
    print(f"Chapter saved to: {text_file}")
    print(f"Audio saved to: {audio_file}")
    print(f"Progress: {new_progress_checkpoint}")

if __name__ == "__main__":
    main()

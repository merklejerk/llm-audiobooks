#!/usr/bin/env python3

import argparse
import os
import json
import re
from pathlib import Path
import openai
from dotenv import load_dotenv
import ffmpeg

# Load environment variables from .env file for configuration purposes
load_dotenv()

# Configure OpenAI API using environment variables
openai.api_key = os.environ.get("OPENAI_API_KEY")
LLM_MODEL = os.environ.get("OPENAI_LLM_MODEL", "gpt-4o-mini")
TTS_MODEL = os.environ.get("OPENAI_TTS_MODEL", "gpt-40-mini-tts")
TTS_VOICE = os.environ.get("OPENAI_TTS_VOICE", "nova")

def load_progress(book_id):
    """Load the checkpoint for a specific book from disk."""
    # Check if a progress file exists for the given book
    progress_file = Path(f"progress/{book_id}.json")
    if progress_file.exists():
        with open(progress_file, "r") as f:
            return json.load(f)
    # No previous progress file found; return default progress checkpoint
    return {"last_chapter": "N/A", "checkpoint": "This is the start of the story. We need to write chapter 1."}

def save_progress(book_id, checkpoint):
    """Save the checkpoint to disk."""
    progress_dir = Path("progress")
    progress_dir.mkdir(exist_ok=True)
    # Write the updated progress to a JSON file
    with open(progress_dir / f"{book_id}.json", "w") as f:
        json.dump(checkpoint, f, indent=2)

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
    """Extract chapter content based on the tag."""
    return sections.get("chapter")

def extract_progress_checkpoint(sections):
    """Extract checkpoint summary if available."""
    return sections.get("checkpoint") or None

def generate_chapter(book_id, spec, progress):
    """Generate the next chapter using the OpenAI API."""
    previous_chapter = progress.get("last_chapter", "N/A")
    progress_text = progress.get("checkpoint", "")
    # Assemble the prompt with book specification, previous chapter, and checkpoint details.
    prompt = f"""
[book specification]
{spec}

[previous chapter]
{previous_chapter}

[checkpoint]
{progress_text}
"""
    print("Generating chapter...")
    # Call the OpenAI API to generate the next chapter text.
    response = openai.responses.create(
        model=LLM_MODEL,
        instructions=r"""
You are an expert storyteller AI that creates detailed, engaging book chapters. You will be tasked to write successive chapters of a book.
For each prompt, you will be given a book specification, the contents of the last chapter you wrote, and a checkpoint summary.
If the story is complete, do NOT output a [checkpoint] section.
You should always do the following:
1. Write the next chapter of the book based on the specification and the last checkpoint. Strive for continuity and coherence with the previous chapters.
2. Begin the chapter section with the tag `[chapter]`. Do not use a closing tag; the start of any new tag (e.g. `[checkpoint]`) marks its end.
3. After the chapter, if the story is not complete, prefix the checkpoint summary with `[checkpoint]` including:
    - A line stating: "I just wrote Chapter X", where "X" is the chapter number.
    - An estimated number of chapters remaining.
    - How we got to this point in the story from the previous chapter.
    - a summary of chapter events, highlighting any significant events and character developments. Use proper names where applicable.
    - A growing profile of every significant character mentioned in this chapter, as well as their character arcs.
    - A description of the setting, both the immediate environment and the larger world.
    - A growing list of key plot points, and where we are in their progress.
    - Brief suggestions for where to go in the next chapter and beyond.
""",
        input=prompt,
        max_output_tokens=4000,
        temperature=0.7
    )
    
    # Process and concatenate text output received from OpenAI API
    full_text = "".join(item.text for msg in response.output if msg.type == 'message' for item in msg.content if item.type == 'output_text')
    return full_text

def generate_audio(book_id, chapter_number, chapter_content):
    """Generate an audio file from the chapter content."""
    chapters_dir = Path("chapters")
    chapters_dir.mkdir(exist_ok=True)
    # Define path for the generated audio file.
    audio_file_path = chapters_dir / f"{book_id}_chapter_{chapter_number}.wav"
    
    print("Generating audio...")
    # Call OpenAI TTS API to convert chapter text to speech.
    resp = openai.audio.speech.create(
        model=TTS_MODEL,
        voice=TTS_VOICE,
        input=chapter_content,
        instructions="You are narrating an audiobook. Be clear and engaging. Read dialogue dramatically.",
        response_format="wav",
    )
    resp.write_to_file(str(audio_file_path))
    return audio_file_path

def save_chapter_text(book_id, chapter_number, chapter_content):
    """Save the chapter text to disk."""
    chapters_dir = Path("chapters")
    chapters_dir.mkdir(exist_ok=True)
    # Define path for the chapter text file.
    text_file_path = chapters_dir / f"{book_id}_chapter_{chapter_number}.md"
    
    with open(text_file_path, "w") as f:
        f.write(chapter_content)
    
    return text_file_path

def extract_book_id_from_spec_file(spec_file_path):
    """Extract book ID from the specification file path.
    Uses the part of the filename before the first period as the book ID.
    """
    path = Path(spec_file_path)
    filename = path.name  # Get filename from path.
    return filename.split('.')[0]  # Split by period and take first part as ID.

# New helper function to concatenate audio files using ffmpeg-python
def concat_audio_files(book_id, output_file):
    """
    Concatenate all chapter audio files into a single file, with silence filtering.
    
    Args:
        book_id: The identifier for the book
        output_file: Path to save the concatenated audio
        silence_threshold: The threshold (in dB) below which audio is considered silence (default: -50dB)
        silence_duration: Minimum duration of silence to remove (in seconds) (default: 1s)
    """
    chapters_dir = Path("chapters")
    # List and sort audio files based on chapter number.
    files = sorted(chapters_dir.glob(f"{book_id}_chapter_*.wav"), key=lambda f: int(re.search(r"chapter_(\d+)\.wav", f.name).group(1)))
    if not files:
        print("No chapter audio files found to concatenate.")
        return
    
    # Create ffmpeg inputs for each audio file with silence filtering
    inputs = [
        ffmpeg.input(str(audio_path), err_detect='ignore_err') for audio_path in files
    ]
    
    # Concatenate all filtered audio streams into one output file
    joined = ffmpeg.concat(*inputs, v=0, a=1)\
            .filter('silenceremove', 
                detection='rms',
                start_periods=1,
                stop_periods=-1,
                start_threshold='-30dB',
                stop_threshold='-30dB',
                stop_duration=1,
            ).output(output_file)\
            .overwrite_output()
    
    # Run the command
    ffmpeg.run(joined)
    print(f"Concatenated audio file saved to: {output_file}")

# New helper function to process a chapter
def process_chapter(book_id, spec, last_progress):
    # Generate chapter and extract sections from the response.
    response = generate_chapter(book_id, spec, last_progress)
    sections = extract_sections(response)
    chapter_content = extract_chapter_content(sections)
    checkpoint = extract_progress_checkpoint(sections)

    if not chapter_content:
        # If no chapter content could be extracted, log an error.
        print("Error: Could not extract chapter content from response.")
        print(sections)
        raise ValueError("Chapter content is missing.")

    # Set progress and handle final chapter scenario.
    if not checkpoint:
        print("Final chapter reached. Story is complete.")
        progress = {"last_chapter": chapter_content, "checkpoint": ""}
    else:
        progress = {"last_chapter": chapter_content, "checkpoint": checkpoint}
        print("\n--- checkpoint ---")
        print(f"Checkpoint: {checkpoint}")

    save_progress(book_id, progress)

    # Display generated chapter content
    print("\n=== New Chapter ===\n")
    print(chapter_content)
    print("\n==================\n")

    # Determine chapter number by counting existing chapter files.
    chapter_count = len(list(Path("chapters").glob(f"{book_id}_chapter_*.md")))
    chapter_number = chapter_count + 1
    # Generate audio and text files
    audio_file = generate_audio(book_id, chapter_number, chapter_content)
    text_file = save_chapter_text(book_id, chapter_number, chapter_content)
    print(f"Chapter saved to: {text_file}")
    print(f"Audio saved to: {audio_file}")

    return None if not checkpoint else progress

def main():
    # Parse command-line arguments for the specification file, number of chapters, and audio concatenation option.
    parser = argparse.ArgumentParser(description="Generate audiobooks using OpenAI APIs")
    parser.add_argument("spec_file", help="Path to the specification file")
    parser.add_argument("--num-chapters", "-n", type=int, default=1, help="Number of successive chapters to generate")
    parser.add_argument("--concat-audio", "-c", type=str, help="Output file to concatenate all generated chapter audio files")
    args = parser.parse_args()

    # Extract book ID from the specification filename and load corresponding spec and progress.
    book_id = extract_book_id_from_spec_file(args.spec_file)
    print(f"Using book ID: {book_id}")
    spec = load_spec(args.spec_file)
    progress = load_progress(book_id)

    # Loop to generate the specified number of chapters.
    for _ in range(args.num_chapters):
        result = process_chapter(book_id, spec, progress)
        if result is None:
            break
        progress = result

    # If concatenation flag is set, combine generated chapter audio files.
    if args.concat_audio:
        concat_audio_files(book_id, args.concat_audio)

if __name__ == "__main__":
    main()

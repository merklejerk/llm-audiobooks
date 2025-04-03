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
TTS_MODEL = os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
TTS_VOICE = os.environ.get("OPENAI_TTS_VOICE", "nova")

def load_progress(book_id):
    """Load the checkpoint for a specific book from disk."""
    # Check if a progress file exists for the given book
    progress_file = Path(f"progress/{book_id}.json")
    if progress_file.exists():
        with open(progress_file, "r") as f:
            progress = json.load(f)
            # Ensure chapter_number exists in older progress files
            if "chapter_number" not in progress:
                # Count existing chapter files to determine last chapter number
                chapters_dir = Path("chapters")
                if chapters_dir.exists():
                    text_files = list(chapters_dir.glob(f"{book_id}_chapter_*.md"))
                    progress["chapter_number"] = len(text_files)
                else:
                    progress["chapter_number"] = 0
            return progress
     # No previous progress file found; return default progress checkpoint
    return {
        "last_chapter": "N/A", 
        "checkpoint": "This is the start of the story.",
        "chapter_number": 0,
        "summaries": ""
    }

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

def generate_chapter(book_id, spec, progress):
    """Generate the next chapter using the OpenAI API."""
    # previous_chapter = progress.get("last_chapter", "N/A")
    checkpoint_text = progress.get("checkpoint", "")
    summaries_text = progress.get("summaries", "")
    next_chpater_number = progress.get("chapter_number", 0) + 1 
    prompt = f"""
[book specification]
{spec}

[summaries]
{summaries_text or "N/A"}

[last checkpoint]
{checkpoint_text}

**Please write chapter {next_chpater_number}.**
"""
    print(f"Generating chapter {next_chpater_number}...")
    # Call the OpenAI API to generate the next chapter text.
    response = openai.responses.create(
        model=LLM_MODEL,
        instructions=r"""
You are an expert storyteller AI that creates detailed, engaging book chapters. You will be tasked to write successive chapters of a book.

For each prompt, you will be given:
1. A book specification, tagged with `[specification]`
2. The combined summaries from all past chapters, tagged `[summaries]`.
4. The checkpoint data from the last chapter you wrote, tagged with `[last checkpoint]`.

As your response, you should generate the following sections:
1. Always generate a `[chapter]` section:
    - Here you should write the next chapter of the book based on the specification and the last checkpoint. Strive for continuity and coherence with the previous chapters.
    - When the entire story (not just the chapter) has ended, say exactly: `<THE END>`
2. If the story is NOT complete, generate a `[summary]` section:
    - Write a detailed but concise summary of the chapter you just wrote, including key events, character developments (with names), and settings.
    - Describe any characters that were introduced, including their appearance, personality, and current character arc and status.
2. If the story is NOT complete, generate a `[checkpoint]` section, which should include:
    - The estimated number of chapters remaining to complete the story.
    - Any plot points that are unresolved.
    - Brief suggestions for where to go in the next chapter and beyond. If the next chapter should be the final chapter, remark on that.

Do not forget to include section tags in your response.
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
def concat_audio_files(book_id, output_file, speed=1.0):
    # Concatenate all chapter audio files into a single file, with silence filtering.
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
            ).filter('atempo', speed)\
            .output(output_file)\
            .overwrite_output()
    
    # Run the command
    ffmpeg.run(joined)
    print(f"Concatenated audio file saved to: {output_file}")

# New helper function to process a chapter
def new_chapter(book_id, spec, last_progress, skip_audio=False):
    # Generate chapter and extract sections from the response.
    response = generate_chapter(book_id, spec, last_progress)
    sections = extract_sections(response)
    chapter_content = sections.get("chapter", "")
    checkpoint = sections.get("checkpoint") or sections.get("last checkpoint")
    summary_content = sections.get("summary") or sections.get("summaries", "")
    if not chapter_content:
        print("Error: Could not extract chapter content from response.")
        raise ValueError("Chapter content is missing.")
    chapter_number = last_progress.get("chapter_number", 0) + 1
    new_summaries = (last_progress.get("summaries", "") + f"\n### Chapter {chapter_number} Summary:\n{summary_content}").strip()
    if "<the end>" in response.lower() or not checkpoint:
        print("Story is complete.")
        chapter_content = chapter_content.replace("<the end>", "")
        progress = {
            "last_chapter": chapter_content, 
            "checkpoint": "DONE",
            "chapter_number": chapter_number,
            "summaries": new_summaries
        }
        checkpoint = None
    else:
        progress = {
            "last_chapter": chapter_content, 
            "checkpoint": checkpoint,
            "chapter_number": chapter_number,
            "summaries": new_summaries
        }
        print("\n--- Summary ---")
        print(summary_content)
        print("\n--- checkpoint ---")
        print(checkpoint)
    save_progress(book_id, progress)
    # Display generated chapter content
    print("\n=== New Chapter ===\n")
    print(chapter_content)
    print("\n==================\n")
    print(f"Chapter saved to: {save_chapter_text(book_id, chapter_number, chapter_content)}")
    if not skip_audio:
        audio_path = generate_audio(book_id, chapter_number, chapter_content)
        print(f"Audio saved to: {audio_path}")
    else:
        print("Audio generation skipped.")
    return None if not checkpoint else progress

def regen_missing_audio(book_id):
    """Generate audio for all chapters that are missing audio files."""
    chapters_dir = Path("chapters")
    chapter_files = sorted(chapters_dir.glob(f"{book_id}_chapter_*.md"), key=lambda f: int(re.search(r"chapter_(\d+)\.md", f.name).group(1)))
    for text_file in chapter_files:
        chapter_number = int(re.search(r"chapter_(\d+)\.md", text_file.name).group(1))
        audio_file = chapters_dir / f"{book_id}_chapter_{chapter_number}.wav"
        if not audio_file.exists():
            print(f"Audio missing for chapter {chapter_number}. Generating audio...")
            with open(text_file, "r") as f:
                chapter_content = f.read()
            generate_audio(book_id, chapter_number, chapter_content)
            print(f"Audio generated for chapter {chapter_number}")
    print("Completed regenerating missing audio files.")

def main():
    # Parse command-line arguments for the specification file, number of chapters, and audio concatenation option.
    parser = argparse.ArgumentParser(description="Generate audiobooks using OpenAI APIs")
    parser.add_argument("spec_file", help="Path to the specification file")
    parser.add_argument("--num-chapters", "-n", type=int, default=1, help="Number of successive chapters to generate")
    parser.add_argument("--concat-audio", "-c", type=str, help="Output file to concatenate all generated chapter audio files")
    parser.add_argument("--regen-audio", "-a", action="store_true", help="Generate audio for all chapters missing audio files")
    parser.add_argument("--skip-audio", "-A", action="store_true", help="Skip generating audio files")  # new argument
    parser.add_argument("--speed", "-s", type=float, default=1.0, help="Audio speed multiplier for concatenated audio (default: 1.0)")
    args = parser.parse_args()

    # Extract book ID from the specification filename and load corresponding spec and progress.
    book_id = extract_book_id_from_spec_file(args.spec_file)
    print(f"Using book ID: {book_id}")
    spec = load_spec(args.spec_file)
    progress = load_progress(book_id)

    # If --regen-audio flag is set, generate missing audio first.
    if args.regen_audio:
        regen_missing_audio(book_id)

    if progress["checkpoint"] == "DONE":
        print("Story is already complete. No further chapters will be generated.")
    else:
        # Loop to generate the specified number of chapters.
        for _ in range(args.num_chapters):
            result = new_chapter(book_id, spec, progress, skip_audio=args.skip_audio)
            if result is None:
                break
            progress = result

    # If concatenation flag is set, combine generated chapter audio files.
    if args.concat_audio:
        concat_audio_files(book_id, args.concat_audio, speed=args.speed)

if __name__ == "__main__":
    main()

# LLM Audiobook Generator

> ⚠️ &nbsp;&nbsp; This project was mostly vibe coded.<br /> 🍿 &nbsp;&nbsp; For entertainment purposes only.


A CLI tool that generates audiobooks using OpenAI APIs.

## Installation

This is a python project (`pyproject.toml`), developed with [`poetry`](https://python-poetry.org/), but probably works fine with [`uv`](https://github.com/astral-sh/uv) and possibly others.

```bash
poetry install
```

## Configuration

Create a `.env` file in the project root directory with the following variables (modify the values accordingly):

```
OPENAI_API_KEY=your_openai_api_key
OPENAI_LLM_MODEL=gpt-4o-mini
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=nova
```

- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENAI_LLM_MODEL`: The OpenAI model to use for text generation (default: gpt-4)
- `OPENAI_TTS_MODEL`: The OpenAI model to use for text-to-speech (default: tts-1)
- `OPENAI_TTS_VOICE`: The voice to use for text-to-speech (default: nova)

## Usage

```bash
poetry run python audiobook_gen.py <spec_file> [--num-chapters N] [--concat-audio output_file]
```

### Parameters

- `spec_file`: Path to the specification file that describes the story, style, etc.

The book ID is inferred from the spec filename (the name before the first period). For instance, a spec file named `quantum_detective.txt` will use `quantum_detective` as the book ID.

### Optional Arguments

- `--num-chapters` or `-n`: Number of successive chapters to generate (default: 1).
- `--concat-audio` or `-c`: Specifies an output file to concatenate all generated chapter audio files.

### Spec File Format

The spec file is a markdown file containing a detailed description of the book, including things like:
- Story outline
- Main characters
- Setting
- Style and tone
- Target audience

## Output

- Chapter content is saved to `chapters/<book_id>_chapter_<number>.md`
- Audio files are saved to `chapters/<book_id>_chapter_<number>.wav`
- Progress markers are saved to `progress/<book_id>.json`

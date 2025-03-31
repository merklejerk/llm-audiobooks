# Audiobook Generator

A CLI tool that generates audiobooks using OpenAI APIs.

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root directory with the following variables:

```
OPENAI_API_KEY=your_openai_api_key
OPENAI_LLM_MODEL=gpt-4
OPENAI_TTS_MODEL=tts-1
OPENAI_TTS_VOICE=nova
```

- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENAI_LLM_MODEL`: The OpenAI model to use for text generation (default: gpt-4)
- `OPENAI_TTS_MODEL`: The OpenAI model to use for text-to-speech (default: tts-1)
- `OPENAI_TTS_VOICE`: The voice to use for text-to-speech (default: nova)

## Usage

```bash
python audiobook_gen.py <spec_file>
```

### Parameters

- `spec_file`: Path to the specification file that describes the story, style, etc.

The book ID is automatically inferred from the name of the spec file (without extension).
For example, a spec file named `quantum_detective.txt` will use `quantum_detective` as the book ID.

### Spec File Format

The spec file should contain a detailed description of the book, including:
- Story outline
- Main characters
- Setting
- Style and tone
- Target audience

## Output

- Chapter content is saved to `chapters/<book_id>_chapter_<number>.txt`
- Audio files are saved to `chapters/<book_id>_chapter_<number>.mp3`
- Progress markers are saved to `progress/<book_id>.json`

# LLM Audiobook Generator

> ⚠️ &nbsp;&nbsp; This project was mostly vibe coded.<br /> 🍿 &nbsp;&nbsp; For entertainment purposes only.

A CLI tool that generates audiobooks using OpenAI APIs.

## 🚀 &nbsp; Installation

This is a python project developed with [`poetry`](https://python-poetry.org/), I haven't tested it with [`uv`](https://github.com/astral-sh/uv), etc.

First, install basic deps:

```bash
poetry install
```

Then you will need to manually install `llama-cpp-python`, which seems to be particular for every machine if you want to take advantage of TTS acceleration. For example:
```bash
CMAKE_ARGS='-DGGML_VULKAN=on' poetry run pip install --no-cache llama-cpp-python
```

## ⚙️ &nbsp; Configuration

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

## 🛠️ &nbsp; Usage

```bash
poetry run python audiobook_gen.py <spec_file> [--num-chapters N] [--concat-audio output_file]
```

This command generates the next chapter(s) of an audiobook based on the provided specification file. The tool automatically picks up where it left off by using progress saved from previous runs. It uses OpenAI's APIs to create text content for the chapters and convert them into audio files. Optionally, all audio files can be concatenated into a single file.

### Parameters

- `spec_file`: Path to the specification file that describes the story, style, etc.

The book ID is inferred from the spec filename (the name before the first period). For instance, a spec file named `quantum_detective.spec.md` will use `quantum_detective` as the book ID.

### Optional Arguments

- `--num-chapters` or `-n`: Number of successive chapters to generate (default: 1). Each chapter's text and audio will be created sequentially, continuing from the last saved progress.
- `--concat-audio` or `-c`: Specifies an output file to concatenate all generated chapter audio files into a single audio file.

### Spec File Format

The spec file is a markdown file containing a detailed description of the book, including things like:
- Story outline
- Main characters
- Setting
- Style and tone
- Target audience

## 📤 &nbsp; Output

- Chapter content is saved to `chapters/<book_id>_chapter_<number>.md`
- Audio files are saved to `chapters/<book_id>_chapter_<number>.wav`
- Progress markers are saved to `progress/<book_id>.json`

## 🐛 &nbsp; Issues

OpenAI's Text-To-Speech APIs seem to occasionally glitch out and repeat itself or introduce long silences in the produced output. Not sure if there's a more reliable way to use them or if we're better off just switching to a less convincing but more reliable TTS like Google's. For the moment, we apply an ffmpeg filter to trim out silences in the concatenated output, but this is far from ideal.


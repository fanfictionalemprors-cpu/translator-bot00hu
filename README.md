# Fast Hindi EPUB Translator 📚⚡

An ultra-fast, asynchronous Python CLI tool to translate full EPUB web novels and books into **Hindi (हिन्दी)** while retaining HTML formatting, styles, images, and chapter structure.

## Features
- **Token / API Key Support:** Option to add your API key/token directly in code or via CLI (`-t`).
- **Free Engine Fallback:** Works 100% free out of the box if no token is provided.
- **Async Speed Boost:** Multi-threaded async request processing for fast translation.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### 1. Free Mode (No Token Needed)
```bash
python fast_epub_translator.py -i "book.epub" -o "book_hindi.epub" -l hi
```

### 2. Using API Token / Key via CLI
```bash
python fast_epub_translator.py -i "book.epub" -o "book_hindi.epub" -t "YOUR_API_TOKEN_HERE"
```

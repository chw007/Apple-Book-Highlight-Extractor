# Apple Books Highlight Extractor

A Python tool for extracting and exporting notes/highlights from Apple Books. Supports filtering by book title and exports results in Markdown format.

## Features

- Automatically locates and connects to Apple Books database
- Supports exporting notes/highlights from all books
- Supports filtering and exporting notes/highlights from specific books by title
- Preserves note context and creation time
- Distinguishes between underlines and highlights
- Supports fuzzy book title matching (case-insensitive)
- Exports to structured Markdown files

## System Requirements

- macOS operating system
- Python 3.7+
- Apple Books application

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the program:
```bash
python main.py
```

2. Follow the prompts:
   - Enter a book title to export notes from a specific book
   - Press Enter directly to export notes from all books

3. The program will automatically:
   - Search and connect to the Apple Books database
   - Extract notes from specified book(s)
   - Save results to a Markdown file on the desktop

## Output Format

The exported Markdown file follows this format:

```markdown
## Book Title

> Highlight/Note content

Context: Surrounding content (if available)

Note: Additional notes (if available)

- Chapter: Chapter information
- Date: Creation time
```

## File Description

- `main.py`: Main program file
- `requirements.txt`: List of dependencies

## Main Classes and Methods

### BookHighlightExtractor

Main extractor class with the following methods:

- `__init__()`: Initialize extractor
- `get_highlights(book_title)`: Get notes/highlights
- `export_to_markdown(output_path, book_title)`: Export to Markdown file
- `get_book_title(asset_id)`: Get book title

### Highlight

Data class for storing note/highlight information:

- `text`: Note/highlight content
- `created_at`: Creation time
- `book_title`: Book title
- `chapter`: Chapter information (optional)
- `note`: Additional notes (optional)

## Important Notes

1. Ensure sufficient permissions to access Apple Books database
2. Program automatically searches common database locations
3. Uses default path if database isn't found
4. Book title matching is case-insensitive and supports partial matches

## Common Issues

1. Can't find database?
   - Ensure Apple Books is installed
   - Check permission settings
   - Review system information output

2. No notes found?
   - Verify book contains notes/highlights
   - Check book title accuracy
   - Try searching with shorter book title

3. Where's the output file?
   - Default save location is desktop
   - File naming: `book_highlights_[title].md`
   - All books export: `book_highlights_all.md`

## Contributing

Issues and Pull Requests are welcome!

## License

[MIT License](LICENSE)
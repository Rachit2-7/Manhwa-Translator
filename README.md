# Manhwa Translation Engine

A web app that translates raw Korean manhwa pages into English. You upload a page, the app finds the text in each speech bubble, translates it, and places the English text over the original. You can edit any line before downloading the result.

It uses the Google Gemini API (free tier) to read and translate the page.

## How it works

1. The browser uploads a page image to the FastAPI backend.
2. If the page is a tall webtoon strip, the backend splits it into equal-height tiles.
3. Each tile is sent to Gemini with a prompt asking for JSON: a bounding box, the Korean text, the English translation and a type (speech, thought, narration, sign, sound effect).
4. The backend validates the JSON, retries once if it is malformed, and merges the tiles into one list of regions. Box positions are returned as fractions of the full page.
5. The browser covers each original bubble with its background colour and draws the English text, shrinking the font to fit.

A command-line version does the same thing and renders the page with Pillow.

## Features

- Upload one or many pages
- Translation style options: natural, literal (keeps honorifics), casual
- Optional glossary for consistent character names
- Optional sound-effect translation
- Edit or disable any translated line, and compare with the original
- Download translated pages as PNG
- Unit tests that run without network access


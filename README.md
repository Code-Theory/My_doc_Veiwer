# Stillpage

Stillpage is a local PDF reader in a Python desktop window. It uses the WebView2 runtime already present on Windows, PDF.js for rendering, and React for the reading interface. There is no Rust, Electron, account, cloud service, or telemetry.

## Open the app

Double-click `Start Stillpage.bat` in this folder. The installed Python environment is in `.venv`. To start from PowerShell instead:

```powershell
cd D:\Stillpage
.\.venv\Scripts\python.exe app.py
```

The window is a desktop app, not a public website. The Python process serves the built interface over an ephemeral address bound to `127.0.0.1` only; this allows the PDF.js worker to run. It stops when the app closes. Your selected PDF stays on your device. The native file picker grants access to the selected file, which is made available to the viewer through a random, temporary local URL.

## Setup on another machine

Install Python 3.12, Node.js and Microsoft Edge WebView2 Runtime, then from this folder run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

After cloning, run `npm ci` and `npm run build` from the project folder before starting the app. The generated `dist` folder is not included in Git. Node is only needed when building the interface.

## Controls

- Ctrl+O: open a PDF
- Ctrl+B: toggle the navigation sidebar
- Ctrl+Shift+B: toggle the study sidebar
- Ctrl+D: bookmark the current page
- Ctrl+F: search the current document
- Ctrl++ / Ctrl+-: zoom
- Ctrl + mouse wheel: zoom at the pointer; supported Windows touchpads can also pinch to zoom
- Ctrl+0: fit width
- F11: toggle focus mode; Esc exits it
- Page Up / Page Down: previous / next page
- Enter a page number in the bottom bar to jump
- Select text on one page, then choose Highlight or Underline and a color. The Marks tab lets you revisit or delete saved marks. Click a mark on the page to open its note in the study sidebar. Pages without embedded text are recognized locally in English; hover over a page and choose Recognize page text to run OCR on a mixed page. OCR can take time and recognition depends on image quality. OCR text is kept in memory during the session and is re-created when reopened.
- In the study sidebar, edit a page note or choose a mark under “Marks on this page” to edit its attached note. Notes autosave locally and support Markdown preview.
- Add, edit, revisit and delete bookmarks from the study sidebar. Each bookmark may have a title and a short note.

## Structure

```
app.py                  Python desktop window and local server
storage.py              SQLite history and settings service
data/stillpage.sqlite3  Local reading history and settings
requirements.txt        Python desktop dependency
Start Stillpage.bat     Desktop launcher
src/components/         PDF pages, thumbnails, outline and search
src/services/pdf.ts     PDF.js loading and rendering
src/stores/reader.ts    Transient reader state
src/App.tsx             Shell, opening and navigation
src/styles.css          Themes and layout
dist/                   Built interface used by the desktop app
```

## Current limitations

The Pages tab loads thumbnails near the sidebar viewport. Outline displays the table of contents provided by the PDF. Search extracts text incrementally, returns matching pages with snippets, and keeps extracted text in memory for the current document. It does not highlight matches on the page, and search currently uses embedded PDF text rather than OCR results. Reading history, last page and zoom are stored per file, while theme and sidebar visibility are global. Use the back arrow to return to recent documents. The X beside a recent entry hides it without deleting the PDF or its notes and marks; opening it again restores the entry. History identifies files by their path; if a file is moved or renamed, select it again as a new entry. The exact scroll offset within a page is not restored. Highlights and underlines are saved separately from the PDF using PDF page coordinates. Selection must start and end on the same page; marks are tied to the stored file path, so reselecting a moved file creates a separate history entry. Annotation placement may vary with unusual PDF text layers and has not yet been validated across all PDF layouts. Page notes, annotation notes, and bookmarks are stored in the local database. Notes save shortly after typing and when the editor loses focus; wait briefly for autosave before closing the app. Clicking marks depends on the PDF text layer. Command palette and flashcards are not implemented yet. Focus mode hides the interface without changing the OS window to fullscreen. Password-protected PDFs do not yet have a password prompt. PDF bytes remain in memory while open; canvases and text layers are rendered only near the viewport. Mixed-size pages can shift slightly as they are first measured. Very large documents need further profiling.


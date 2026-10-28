"""Stillpage desktop host. Serves the interface and user-selected PDFs locally."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from secrets import token_urlsafe
from threading import Lock, Thread
import shutil
import webview
from storage import Storage

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"

class ReaderAPI:
    def __init__(self, storage):
        self._storage = storage
        self._window = None
        self._files = {}
        self._lock = Lock()

    def choose_file(self):
        paths = self._window.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=False, file_types=('PDF files (*.pdf)',))
        return self._open(Path(paths[0])) if paths else None

    def open_recent(self, document_id):
        row = self._storage.document(int(document_id))
        if not row:
            return {'error': 'This document is no longer in your history.'}
        return self._open(Path(row['path']))

    def _open(self, path):
        try:
            path = path.resolve(strict=True)
            if not path.is_file() or path.suffix.lower() != '.pdf':
                return {'error': 'Please choose a PDF file.'}
            with path.open('rb') as source:
                source.read(1)
            row = self._storage.touch(path)
            token = token_urlsafe(32)
            with self._lock:
                self._files.clear()
                self._files[token] = path
            return {'id': row['id'], 'name': row['name'], 'page': row['page'], 'zoom': row['zoom'], 'fitWidth': bool(row['fit_width']), 'url': '/document/' + token}
        except OSError:
            return {'error': 'This file could not be opened. It may have been moved or deleted.'}

    def recent(self):
        return self._storage.recent()

    def library(self):
        return self._storage.library()

    def set_pinned(self, document_id, pinned):
        return self._storage.set_pinned(document_id, pinned)

    def set_page_count(self, document_id, count):
        return self._storage.set_page_count(document_id, count)

    def create_collection(self, name):
        return self._storage.create_collection(name)

    def rename_collection(self, collection_id, name):
        return self._storage.rename_collection(collection_id, name)

    def delete_collection(self, collection_id):
        return self._storage.delete_collection(collection_id)

    def set_collection_document(self, collection_id, document_id, included):
        return self._storage.set_collection_document(collection_id, document_id, included)

    def hide_recent(self, document_id):
        return self._storage.hide_recent(document_id)

    def preferences(self):
        return self._storage.settings()

    def save_preferences(self, theme, sidebar, study_sidebar=False):
        self._storage.save_settings(theme, sidebar, study_sidebar)

    def study_data(self, document_id):
        return self._storage.study_data(document_id)

    def save_note(self, document_id, page, annotation_id, body):
        self._storage.save_note(document_id, page, annotation_id, body)

    def add_bookmark(self, document_id, page):
        return self._storage.add_bookmark(document_id, page)

    def update_bookmark(self, document_id, bookmark_id, title, note):
        return self._storage.update_bookmark(document_id, bookmark_id, title, note)

    def delete_bookmark(self, document_id, bookmark_id):
        return self._storage.delete_bookmark(document_id, bookmark_id)

    def annotations(self, document_id):
        return self._storage.annotations(document_id)

    def add_annotation(self, document_id, page, kind, color, text, rects):
        return self._storage.add_annotation(document_id, page, kind, color, text, rects)

    def delete_annotation(self, document_id, annotation_id):
        return self._storage.delete_annotation(document_id, annotation_id)

    def save_session(self, document_id, page, zoom, fit_width):
        self._storage.save_session(document_id, page, zoom, fit_width)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, api, **kwargs):
        self.api = api
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path.startswith('/document/'):
            token = self.path.removeprefix('/document/')
            with self.api._lock:
                path = self.api._files.get(token)
            if not path:
                self.send_error(404)
                return
            try:
                with path.open('rb') as source:
                    size = path.stat().st_size
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/pdf')
                    self.send_header('Content-Length', str(size))
                    self.send_header('Cache-Control', 'no-store')
                    self.end_headers()
                    shutil.copyfileobj(source, self.wfile)
            except (OSError, ConnectionError):
                pass
            return
        super().do_GET()

    def log_message(self, format, *args):
        pass

def main():
    if not (DIST / 'index.html').is_file():
        raise SystemExit('Interface not built. Run npm install and npm run build first.')
    api = ReaderAPI(Storage(ROOT / 'data' / 'stillpage.sqlite3'))
    handler = partial(Handler, directory=str(DIST), api=api)
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        api._window = webview.create_window('Stillpage', f'http://127.0.0.1:{server.server_port}/', js_api=api, text_select=True, width=1280, height=820, min_size=(720, 500))
        webview.start(gui='edgechromium')
    finally:
        server.shutdown()
        server.server_close()

if __name__ == '__main__':
    main()

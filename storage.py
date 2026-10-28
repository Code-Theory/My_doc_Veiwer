"""Small SQLite persistence layer for reading history and preferences."""
import json
import math
from contextlib import contextmanager
import sqlite3
from pathlib import Path

class Storage:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS migrations (version INTEGER PRIMARY KEY)")
            if not db.execute("SELECT 1 FROM migrations WHERE version=1").fetchone():
                db.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, name TEXT NOT NULL, last_opened TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, page INTEGER NOT NULL DEFAULT 1, zoom REAL NOT NULL DEFAULT 1, fit_width INTEGER NOT NULL DEFAULT 1)")
                db.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
                db.execute("INSERT INTO migrations VALUES (1)")
            if not db.execute("SELECT 1 FROM migrations WHERE version=2").fetchone():
                db.execute("CREATE TABLE annotations (id INTEGER PRIMARY KEY, document_id INTEGER NOT NULL REFERENCES documents(id), page INTEGER NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('highlight','underline')), color TEXT NOT NULL, text TEXT NOT NULL, rects TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
                db.execute("CREATE INDEX annotations_document_page ON annotations(document_id, page)")
                db.execute("INSERT INTO migrations VALUES (2)")
            if not db.execute("SELECT 1 FROM migrations WHERE version=3").fetchone():
                db.execute("CREATE TABLE page_notes (document_id INTEGER NOT NULL REFERENCES documents(id), page INTEGER NOT NULL, body TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(document_id,page))")
                db.execute("CREATE TABLE annotation_notes (annotation_id INTEGER PRIMARY KEY REFERENCES annotations(id) ON DELETE CASCADE, body TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
                db.execute("CREATE TABLE bookmarks (id INTEGER PRIMARY KEY, document_id INTEGER NOT NULL REFERENCES documents(id), page INTEGER NOT NULL, title TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '', UNIQUE(document_id,page))")
                db.execute("INSERT INTO migrations VALUES (3)")
            if not db.execute("SELECT 1 FROM migrations WHERE version=4").fetchone():
                db.execute("ALTER TABLE documents ADD COLUMN hidden INTEGER NOT NULL DEFAULT 0")
                db.execute("INSERT INTO migrations VALUES (4)")
            if not db.execute("SELECT 1 FROM migrations WHERE version=5").fetchone():
                db.execute("ALTER TABLE documents ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0")
                db.execute("ALTER TABLE documents ADD COLUMN file_size INTEGER")
                db.execute("ALTER TABLE documents ADD COLUMN page_count INTEGER")
                db.execute("CREATE TABLE collections (id INTEGER PRIMARY KEY, name TEXT NOT NULL COLLATE NOCASE UNIQUE, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
                db.execute("CREATE TABLE collection_documents (collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE, document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE, PRIMARY KEY(collection_id,document_id))")
                db.execute("CREATE INDEX collection_documents_document ON collection_documents(document_id)")
                db.execute("INSERT INTO migrations VALUES (5)")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def touch(self, path: Path):
        with self.connect() as db:
            db.execute("INSERT INTO documents(path,name,last_opened,file_size) VALUES(?,?,CURRENT_TIMESTAMP,?) ON CONFLICT(path) DO UPDATE SET name=excluded.name,last_opened=CURRENT_TIMESTAMP,hidden=0,file_size=excluded.file_size", (str(path), path.name, path.stat().st_size))
            return dict(db.execute("SELECT * FROM documents WHERE path=?", (str(path),)).fetchone())

    def document(self, document_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
            return dict(row) if row else None

    def recent(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT id,name,path,last_opened,page FROM documents WHERE hidden=0 ORDER BY last_opened DESC, id DESC LIMIT 12")]

    def hide_recent(self, document_id):
        with self.connect() as db:
            return db.execute('UPDATE documents SET hidden=1 WHERE id=?', (int(document_id),)).rowcount > 0

    def save_session(self, document_id, page, zoom, fit_width):
        page = max(1, int(page))
        zoom = max(.4, min(3., float(zoom)))
        with self.connect() as db:
            db.execute("UPDATE documents SET page=?, zoom=?, fit_width=? WHERE id=?", (page, zoom, int(bool(fit_width)), int(document_id)))

    def settings(self):
        with self.connect() as db:
            return {row['key']: json.loads(row['value']) for row in db.execute("SELECT key,value FROM settings")}

    def save_settings(self, theme, sidebar, study_sidebar=False):
        if theme not in ('light','dark') or not isinstance(sidebar, bool) or not isinstance(study_sidebar, bool):
            raise ValueError('Invalid preferences')
        with self.connect() as db:
            db.executemany("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", [('theme', json.dumps(theme)), ('sidebar', json.dumps(sidebar)), ('study_sidebar', json.dumps(study_sidebar))])

    def annotations(self, document_id):
        with self.connect() as db:
            rows = db.execute("SELECT id,document_id,page,kind,color,text,rects FROM annotations WHERE document_id=? ORDER BY page,id", (int(document_id),)).fetchall()
            return [{**dict(row), 'rects': json.loads(row['rects'])} for row in rows]

    def add_annotation(self, document_id, page, kind, color, text, rects):
        document_id, page = int(document_id), int(page)
        if page < 1 or kind not in ('highlight', 'underline') or color not in ('yellow','green','blue','pink','purple'):
            raise ValueError('Invalid annotation')
        if not isinstance(text, str) or not text.strip() or len(text) > 20000:
            raise ValueError('Invalid selected text')
        if not isinstance(rects, list) or not 1 <= len(rects) <= 500:
            raise ValueError('Invalid annotation rectangles')
        for rect in rects:
            if not isinstance(rect, list) or len(rect) != 4 or not all(isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n) and abs(n) < 1000000 for n in rect):
                raise ValueError('Invalid annotation coordinates')
        with self.connect() as db:
            if not db.execute('SELECT 1 FROM documents WHERE id=?', (document_id,)).fetchone():
                raise ValueError('Unknown document')
            cur = db.execute('INSERT INTO annotations(document_id,page,kind,color,text,rects) VALUES(?,?,?,?,?,?)', (document_id,page,kind,color,text,json.dumps(rects)))
            return {'id': cur.lastrowid, 'document_id': document_id, 'page': page, 'kind': kind, 'color': color, 'text': text, 'rects': rects}

    def delete_annotation(self, document_id, annotation_id):
        with self.connect() as db:
            return db.execute('DELETE FROM annotations WHERE id=? AND document_id=?', (int(annotation_id),int(document_id))).rowcount > 0

    def study_data(self, document_id):
        document_id = int(document_id)
        with self.connect() as db:
            return {
                'page_notes': [dict(r) for r in db.execute('SELECT page,body FROM page_notes WHERE document_id=?', (document_id,))],
                'annotation_notes': [dict(r) for r in db.execute('SELECT n.annotation_id,n.body FROM annotation_notes n JOIN annotations a ON a.id=n.annotation_id WHERE a.document_id=?', (document_id,))],
                'bookmarks': [dict(r) for r in db.execute('SELECT id,page,title,note FROM bookmarks WHERE document_id=? ORDER BY page', (document_id,))],
            }

    def save_note(self, document_id, page, annotation_id, body):
        document_id, page = int(document_id), int(page)
        if page < 1 or not isinstance(body, str) or len(body) > 100000:
            raise ValueError('Invalid note')
        with self.connect() as db:
            if not db.execute('SELECT 1 FROM documents WHERE id=?', (document_id,)).fetchone():
                raise ValueError('Unknown document')
            if annotation_id is None:
                if body:
                    db.execute('INSERT INTO page_notes(document_id,page,body) VALUES(?,?,?) ON CONFLICT(document_id,page) DO UPDATE SET body=excluded.body,updated_at=CURRENT_TIMESTAMP', (document_id,page,body))
                else:
                    db.execute('DELETE FROM page_notes WHERE document_id=? AND page=?', (document_id,page))
            else:
                annotation_id = int(annotation_id)
                if not db.execute('SELECT 1 FROM annotations WHERE id=? AND document_id=? AND page=?', (annotation_id,document_id,page)).fetchone():
                    raise ValueError('Unknown annotation')
                if body:
                    db.execute('INSERT INTO annotation_notes(annotation_id,body) VALUES(?,?) ON CONFLICT(annotation_id) DO UPDATE SET body=excluded.body,updated_at=CURRENT_TIMESTAMP', (annotation_id,body))
                else:
                    db.execute('DELETE FROM annotation_notes WHERE annotation_id=?', (annotation_id,))

    def add_bookmark(self, document_id, page):
        document_id, page = int(document_id), int(page)
        if page < 1: raise ValueError('Invalid page')
        with self.connect() as db:
            db.execute('INSERT INTO bookmarks(document_id,page) VALUES(?,?) ON CONFLICT(document_id,page) DO NOTHING', (document_id,page))
            return dict(db.execute('SELECT id,page,title,note FROM bookmarks WHERE document_id=? AND page=?', (document_id,page)).fetchone())

    def update_bookmark(self, document_id, bookmark_id, title, note):
        if not isinstance(title, str) or not isinstance(note, str) or len(title)>300 or len(note)>10000: raise ValueError('Invalid bookmark')
        with self.connect() as db:
            return db.execute('UPDATE bookmarks SET title=?,note=? WHERE id=? AND document_id=?', (title,note,int(bookmark_id),int(document_id))).rowcount > 0

    def delete_bookmark(self, document_id, bookmark_id):
        with self.connect() as db:
            return db.execute('DELETE FROM bookmarks WHERE id=? AND document_id=?', (int(bookmark_id),int(document_id))).rowcount > 0

    def library(self):
        with self.connect() as db:
            documents = [dict(row) for row in db.execute('SELECT id,name,path,last_opened,page,page_count,file_size,pinned,hidden FROM documents ORDER BY last_opened DESC,id DESC')]
            collections = [dict(row) for row in db.execute('SELECT id,name FROM collections ORDER BY name COLLATE NOCASE')]
            links = [dict(row) for row in db.execute('SELECT collection_id,document_id FROM collection_documents')]
            return {'documents': documents, 'collections': collections, 'links': links}

    def set_pinned(self, document_id, pinned):
        if not isinstance(pinned, bool): raise ValueError('Invalid pin state')
        with self.connect() as db:
            return db.execute('UPDATE documents SET pinned=? WHERE id=?', (int(pinned), int(document_id))).rowcount > 0

    def set_page_count(self, document_id, page_count):
        count=int(page_count)
        if count < 1 or count > 1000000: raise ValueError('Invalid page count')
        with self.connect() as db:
            return db.execute('UPDATE documents SET page_count=? WHERE id=?', (count,int(document_id))).rowcount > 0

    @staticmethod
    def _collection_name(name):
        if not isinstance(name,str): raise ValueError('Invalid collection name')
        name=name.strip()
        if not name or len(name)>100: raise ValueError('Collection name must be between 1 and 100 characters')
        return name

    def create_collection(self, name):
        name=self._collection_name(name)
        with self.connect() as db:
            try:
                cur=db.execute('INSERT INTO collections(name) VALUES(?)', (name,))
            except sqlite3.IntegrityError as error:
                raise ValueError('A collection with that name already exists') from error
            return {'id':cur.lastrowid, 'name':name}

    def rename_collection(self, collection_id, name):
        name=self._collection_name(name)
        with self.connect() as db:
            try:
                return db.execute('UPDATE collections SET name=? WHERE id=?', (name,int(collection_id))).rowcount > 0
            except sqlite3.IntegrityError as error:
                raise ValueError('A collection with that name already exists') from error

    def delete_collection(self, collection_id):
        with self.connect() as db:
            return db.execute('DELETE FROM collections WHERE id=?', (int(collection_id),)).rowcount > 0

    def set_collection_document(self, collection_id, document_id, included):
        if not isinstance(included,bool): raise ValueError('Invalid membership')
        with self.connect() as db:
            if included:
                db.execute('INSERT INTO collection_documents(collection_id,document_id) VALUES(?,?) ON CONFLICT(collection_id,document_id) DO NOTHING', (int(collection_id),int(document_id)))
            else:
                db.execute('DELETE FROM collection_documents WHERE collection_id=? AND document_id=?', (int(collection_id),int(document_id)))

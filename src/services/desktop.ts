export type RecentDocument = { id: number; name: string; path: string; page: number };
export type OpenDocument = { id: number; name: string; page: number; zoom: number; fitWidth: boolean; url: string };
export type Annotation = { id: number; document_id: number; page: number; kind: 'highlight' | 'underline'; color: MarkColor; text: string; rects: number[][] };
export type MarkColor = 'yellow' | 'green' | 'blue' | 'pink' | 'purple';
export type Bookmark = { id: number; page: number; title: string; note: string };
export type StudyData = { page_notes: {page:number; body:string}[]; annotation_notes: {annotation_id:number; body:string}[]; bookmarks: Bookmark[] };
type Result = OpenDocument | { error: string } | null;
type Api = { hide_recent: (id: number) => Promise<boolean>; study_data: (id:number) => Promise<StudyData>; save_note: (id:number, page:number, annotationId:number | null, body:string) => Promise<void>; add_bookmark: (id:number, page:number) => Promise<Bookmark>; update_bookmark: (id:number, bookmarkId:number, title:string, note:string) => Promise<boolean>; delete_bookmark: (id:number, bookmarkId:number) => Promise<boolean>; annotations: (id: number) => Promise<Annotation[]>; add_annotation: (id: number, page: number, kind: Annotation['kind'], color: MarkColor, text: string, rects: number[][]) => Promise<Annotation>; delete_annotation: (id: number, annotationId: number) => Promise<boolean>; choose_file: () => Promise<Result>; open_recent: (id: number) => Promise<Result>; recent: () => Promise<RecentDocument[]>; preferences: () => Promise<{ theme?: 'light' | 'dark'; sidebar?: boolean; study_sidebar?: boolean }>; save_preferences: (theme: string, sidebar: boolean, studySidebar: boolean) => Promise<void>; save_session: (id: number, page: number, zoom: number, fit: boolean) => Promise<void> };
declare global { interface Window { pywebview?: { api: Api } } }
export const desktop = () => window.pywebview?.api;

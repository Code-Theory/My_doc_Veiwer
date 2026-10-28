import { memo, useEffect, useRef, useState } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { ChevronDown, ChevronRight, FileText, ListTree, Search, Highlighter, Trash2 } from 'lucide-react';
import { drawPage, type DocumentProxy } from '../services/pdf';
import type { Annotation } from '../services/desktop';

type Tab = 'pages' | 'outline' | 'search' | 'marks';
type OutlineEntry = { title: string; dest: string | unknown[] | null; items: OutlineEntry[] };
type Hit = { page: number; snippet: string };
type Props = { doc: DocumentProxy; page: number; tab: Tab; setTab: (tab: Tab) => void; jump: (page: number) => void; searchRequest: number; annotations: Annotation[]; removeMark: (id: number) => void };

const Thumbnail = memo(function Thumbnail({doc, number, active, jump}: {doc: DocumentProxy; number: number; active: boolean; jump: (n: number) => void}) {
 const root = useRef<HTMLButtonElement>(null); const canvas = useRef<HTMLCanvasElement>(null); const [near, setNear] = useState(false);
 useEffect(() => { const el = root.current; if (!el) return; const observer = new IntersectionObserver(([e]) => setNear(e.isIntersecting), {root: el.closest('.nav-scroll'), rootMargin: '300px'}); observer.observe(el); return () => observer.disconnect(); }, []);
 useEffect(() => { if (!near || !canvas.current) return; let cancelled = false; let task: {cancel: () => void} | undefined; const target = canvas.current;
   (async () => { try { const page = await doc.getPage(number); if (cancelled) return; const result = await drawPage(page, target, 112); task = result.task; await result.task.promise; } catch (e) { if (!cancelled) console.error('Thumbnail rendering failed', e); } })();
   return () => { cancelled = true; task?.cancel(); target.width = 0; target.height = 0; };
 }, [doc, near, number]);
 return <button ref={root} className={`thumbnail ${active ? 'selected' : ''}`} onClick={() => jump(number)} aria-label={`Go to page ${number}`} aria-current={active ? 'page' : undefined}><div className="thumbnail-paper">{near && <canvas ref={canvas}/>}</div><span>{number}</span></button>;
});

function ThumbnailList({doc,page,jump}: {doc:DocumentProxy;page:number;jump:(page:number)=>void}) {
 const scroll=useRef<HTMLDivElement>(null);
 const virtualizer=useVirtualizer({count:doc.numPages,getScrollElement:()=>scroll.current,estimateSize:()=>198,overscan:2});
 return <div ref={scroll} className="nav-scroll thumbnails" aria-label="Page thumbnails"><div className="virtual-thumbnails" style={{height:virtualizer.getTotalSize()}}>{virtualizer.getVirtualItems().map(item => <div key={item.key} className="virtual-thumbnail" style={{transform:`translateY(${item.start}px)`}}><Thumbnail doc={doc} number={item.index+1} active={page===item.index+1} jump={jump}/></div>)}</div></div>;
}

function OutlineRow({doc, item, jump}: {doc: DocumentProxy; item: OutlineEntry; jump: (page: number) => void}) {
 const [expanded, setExpanded] = useState(true); const [failed, setFailed] = useState(false);
 const go = async () => { try { const dest = typeof item.dest === 'string' ? await doc.getDestination(item.dest) : item.dest; if (!dest || !dest.length) {setFailed(true); return;} const ref = dest[0]; const index = typeof ref === 'number' ? ref : await doc.getPageIndex(ref); jump(index + 1); } catch { setFailed(true); } };
 return <li><div className="outline-row">{item.items.length ? <button className="outline-toggle" aria-label={`${expanded ? 'Collapse' : 'Expand'} ${item.title}`} aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>{expanded ? <ChevronDown size={14}/> : <ChevronRight size={14}/>}</button> : <span className="outline-indent"/>}<button className="outline-title" onClick={() => void go()} title={failed ? 'This outline destination is unavailable' : item.title}>{item.title || 'Untitled'}{failed && <span className="outline-unavailable"> — unavailable</span>}</button></div>{expanded && item.items.length > 0 && <ul className="outline-children">{item.items.map((child, i) => <OutlineRow key={i} doc={doc} item={child} jump={jump}/>)}</ul>}</li>;
}

export default function Navigation({doc, page, tab, setTab, jump, searchRequest, annotations, removeMark}: Props) {
 const [outline, setOutline] = useState<OutlineEntry[] | null>(null); const [query, setQuery] = useState(''); const [hits, setHits] = useState<Hit[]>([]); const [progress, setProgress] = useState(0); const [searching, setSearching] = useState(false); const [searchError, setSearchError] = useState(false); const input = useRef<HTMLInputElement>(null); const cache = useRef(new Map<number,string>());
 useEffect(() => { let cancelled = false; setOutline(null); setQuery(''); setHits([]); setProgress(0); cache.current.clear(); doc.getOutline().then(result => { if (!cancelled) setOutline((result || []) as OutlineEntry[]); }).catch(() => { if (!cancelled) setOutline([]); }); return () => {cancelled = true;}; }, [doc]);
 useEffect(() => { if (searchRequest) input.current?.focus(); }, [searchRequest, tab]);
 useEffect(() => { const needle = query.trim().toLocaleLowerCase(); setHits([]); setProgress(0); setSearchError(false); if (!needle || tab !== 'search') { setSearching(false); return; } let cancelled = false; setSearching(true); const timer = window.setTimeout(() => { void (async () => { const results: Hit[] = []; try { for (let n=1; n<=doc.numPages; n++) { if (cancelled) return; let text = cache.current.get(n); if (text === undefined) { const p = await doc.getPage(n); const content = await p.getTextContent(); text = content.items.map(item => 'str' in item ? item.str : '').join(' ').replace(/\s+/g, ' ').trim(); if (cancelled) return; cache.current.set(n, text); } const pos = text.toLocaleLowerCase().indexOf(needle); if (pos >= 0) { const start = Math.max(0, pos-45), end = Math.min(text.length, pos+needle.length+75); results.push({page:n, snippet: `${start ? '…' : ''}${text.slice(start,end)}${end < text.length ? '…' : ''}`}); } if (n % 8 === 0 || n === doc.numPages) { if (cancelled) return; setHits([...results]); setProgress(n); } await new Promise<void>(resolve => window.setTimeout(resolve, 0)); } } catch (e) { if (!cancelled) { console.error('Search failed', e); setSearchError(true); } } finally { if (!cancelled) setSearching(false); } })(); }, 250); return () => {cancelled = true; window.clearTimeout(timer);}; }, [doc, query, tab]);
 return <><div className="nav-tabs" role="tablist" aria-label="Document navigation"><button role="tab" aria-selected={tab==='pages'} onClick={() => setTab('pages')}><FileText size={15}/> Pages</button><button role="tab" aria-selected={tab==='outline'} onClick={() => setTab('outline')}><ListTree size={15}/> Outline</button><button role="tab" aria-selected={tab==='search'} onClick={() => setTab('search')}><Search size={15}/> Search</button><button role="tab" aria-selected={tab==='marks'} onClick={() => setTab('marks')}><Highlighter size={15}/> Marks</button></div>
 {tab === 'marks' && <div className="nav-scroll marks-list">{annotations.length ? annotations.map(mark => <div className="mark-entry" key={mark.id}><button className="mark-source" onClick={() => jump(mark.page)}><span className={`mark-indicator ${mark.color}`}/><span>PAGE {mark.page} · {mark.kind.toUpperCase()}</span><p>{mark.text}</p></button><button className="icon small mark-delete" title="Delete mark" aria-label={`Delete ${mark.kind} on page ${mark.page}`} onClick={() => removeMark(mark.id)}><Trash2 size={14}/></button></div>) : <p className="nav-message">Select text in the document to add a highlight or underline.</p>}</div>}
 {tab === 'pages' && <ThumbnailList doc={doc} page={page} jump={jump}/>}
 {tab === 'outline' && <div className="nav-scroll outline">{outline === null ? <p className="nav-message">Loading outline…</p> : outline.length ? <ul>{outline.map((item,i) => <OutlineRow key={i} doc={doc} item={item} jump={jump}/>)}</ul> : <p className="nav-message">This document has no outline.</p>}</div>}
 {tab === 'search' && <><div className="search-box"><Search size={15}/><input ref={input} value={query} onChange={e => setQuery(e.target.value)} placeholder="Search document" aria-label="Search document"/></div><div className="search-status" role="status">{searchError ? 'Search could not finish.' : query.trim() ? `${hits.length} ${hits.length === 1 ? 'page' : 'pages'} found${searching ? ` · searching ${progress}/${doc.numPages}` : ''}` : 'Find text in this document'}</div><div className="nav-scroll search-results">{hits.map(hit => <button key={hit.page} onClick={() => jump(hit.page)}><span>PAGE {hit.page}</span><p>{hit.snippet}</p></button>)}{query.trim() && !searching && !searchError && hits.length === 0 && <p className="nav-message">No matching text found.</p>}</div></>}
 </>;
}

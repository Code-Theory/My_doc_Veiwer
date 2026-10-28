import type { DocumentProxy } from './pdf';

type Word = { text:string; x:number; y:number; width:number; height:number };
const cache = new WeakMap<DocumentProxy, Map<number,Word[]>>();
const pending = new WeakMap<DocumentProxy, Map<number,Promise<Word[]>>>();
let worker: Awaited<ReturnType<typeof import('tesseract.js').createWorker>> | null = null;
let idle: ReturnType<typeof setTimeout> | undefined;
let queue: Promise<unknown> = Promise.resolve();
export function cachedWords(doc:DocumentProxy,page:number) { return cache.get(doc)?.get(page); }
export function recognizePage(doc:DocumentProxy,page:number,canvas:HTMLCanvasElement):Promise<Word[]> {
 let pendingPages=pending.get(doc); if(!pendingPages){pendingPages=new Map();pending.set(doc,pendingPages);} const existing=pendingPages.get(page); if(existing) return existing;
 const width=canvas.width,height=canvas.height;
 const image = new Promise<Blob>((resolve,reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('Could not prepare page for OCR')), 'image/png'));
 const task=queue.then(async () => { if(idle) clearTimeout(idle); const blob=await image; if(!worker) {const {createWorker} = await import('tesseract.js'); const root=new URL('ocr/',location.href).href.replace(/\/$/,''); worker=await createWorker('eng',1,{workerPath:`${root}/worker.min.js`,corePath:root,langPath:root,workerBlobURL:false,cacheMethod:'none'}); } const result=await worker.recognize(blob,{}, {blocks:true}); const words:Word[]=[]; for(const block of result.data.blocks ?? []) for(const paragraph of block.paragraphs) for(const line of paragraph.lines) for(const word of line.words) { const b=word.bbox; if(word.text.trim() && b.x1>b.x0 && b.y1>b.y0) words.push({text:word.text,x:b.x0/width,y:b.y0/height,width:(b.x1-b.x0)/width,height:(b.y1-b.y0)/height}); } let pages=cache.get(doc); if(!pages){pages=new Map();cache.set(doc,pages);} pages.set(page,words); return words; });
 queue=task.catch(()=>{}).finally(() => { if(idle) clearTimeout(idle); idle=setTimeout(() => {const old=worker;worker=null;if(old) void old.terminate();},30000); });
 pendingPages.set(page,task); void task.finally(() => {pendingPages?.delete(page);}).catch(()=>{});
 return task;
}
export function drawOcrText(container:HTMLElement, words:Word[], width:number, height:number) {
 container.replaceChildren(); const measure=document.createElement('canvas').getContext('2d');
 for(const word of words) { const span=document.createElement('span'); const fontSize=Math.max(1,word.height*height); span.textContent=word.text+' '; span.style.left=`${word.x*100}%`;span.style.top=`${word.y*100}%`;span.style.fontSize=`${fontSize}px`;span.style.fontFamily='sans-serif';span.style.lineHeight='1'; if(measure){measure.font=`${fontSize}px sans-serif`;const measured=measure.measureText(word.text).width; if(measured>0)span.style.transform=`scaleX(${word.width*width/measured})`;} container.append(span); }
}

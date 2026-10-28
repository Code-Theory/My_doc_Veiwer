import * as pdfjs from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import type { PDFDocumentProxy, PDFPageProxy, RenderTask } from 'pdfjs-dist';
pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;
export type DocumentProxy = PDFDocumentProxy;
export type PageProxy = PDFPageProxy;
export type PageRenderTask = RenderTask;
export async function loadPdf(data: Uint8Array) {
  return pdfjs.getDocument({ data, isEvalSupported: false }).promise;
}
export async function pageSize(doc: DocumentProxy, number: number) {
  const page = await doc.getPage(number);
  const viewport = page.getViewport({ scale: 1 });
  return { width: viewport.width, height: viewport.height };
}
export async function drawPage(page: PageProxy, canvas: HTMLCanvasElement, width: number) {
  const base = page.getViewport({ scale: 1 });
  const viewport = page.getViewport({ scale: width / base.width });
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.floor(viewport.width * ratio);
  canvas.height = Math.floor(viewport.height * ratio);
  canvas.style.width = `${viewport.width}px`;
  canvas.style.height = `${viewport.height}px`;
  const context = canvas.getContext('2d');
  if (!context) throw new Error('Canvas unavailable');
  const task = page.render({ canvasContext: context, viewport, transform: ratio === 1 ? undefined : [ratio, 0, 0, ratio, 0, 0] });
  return { task, viewport };
}
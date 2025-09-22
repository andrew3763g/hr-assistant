const log = (m) => (document.getElementById('log').textContent += m + "\n");

const sessionId = window.CONFIG.SESSION_ID;
let rec, chunkIdx = 0, uploading = 0;

async function uploadChunk(blob) {
  const qs = new URLSearchParams({ session_id: sessionId, kind: 'video', index: String(chunkIdx) });
  const fd = new FormData(); fd.append('file', blob, `chunk_${chunkIdx}.webm`);
  uploading++;
  try {
    const res = await fetch(`/api/interviews/upload/chunk?${qs}`, { method: 'POST', body: fd });
    if (!res.ok) throw new Error(await res.text());
    const j = await res.json();
    chunkIdx = j.next_index ?? (chunkIdx + 1);
    log(`uploaded chunk ${chunkIdx}`);
  } finally { uploading--; }
}

document.getElementById('btnStart').onclick = async () => {
  const stream = window.__mediaStream;
  rec = new MediaRecorder(stream, { mimeType: 'video/webm;codecs=vp9,opus' });
  rec.ondataavailable = (e) => e.data.size && uploadChunk(e.data);
  rec.start(window.CONFIG.MEDIA_TIMESLICE_MS);
  log('recording started');
};

document.getElementById('btnNext').onclick = () => log('NEXT QUESTION (placeholder)');

document.getElementById('btnStop').onclick = async () => {
  rec && rec.state !== 'inactive' && rec.stop();
  log('stopping...');
  while (uploading) await new Promise(r => setTimeout(r, 200));
  const res = await fetch(`/api/interviews/upload/finalize?session_id=${sessionId}`, { method: 'POST' });
  const j = await res.json();
  log(`finalized: ${JSON.stringify(j)}`);
};

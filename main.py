<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Diriyah AI</title>
  <style>
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;background:#f7f3ee;margin:0}
    header{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;background:#e8dccf}
    .brand{font-weight:700;font-size:20px}
    .btn{display:inline-block;padding:10px 14px;border-radius:8px;text-decoration:none;color:#fff;background:#1a73e8}
    .btn.secondary{background:#444}
    .wrap{max-width:920px;margin:16px auto;padding:0 12px}
    #chat{height:60vh;background:#fff;border-radius:12px;border:1px solid #e2d7c9;padding:12px;overflow:auto}
    .row{display:flex;gap:8px;margin-top:10px}
    input,button{font-size:16px}
    input{flex:1;padding:10px;border-radius:10px;border:1px solid #cebda9}
    button{padding:10px 14px;border-radius:10px;border:none;background:#2d5a33;color:#fff}
    .note{color:#6b5f52;font-size:13px;margin-top:8px}
    .pill{padding:6px 10px;border-radius:999px;background:#1a73e8;color:#fff;margin-right:8px;font-size:13px}
  </style>
</head>
<body>
  <header>
    <div class="brand">Diriyah AI</div>
    <div>
      <a class="btn" href="/drive/login">Connect Google Drive</a>
      <a class="btn secondary" href="/drive/list" target="_blank">List My Files (demo)</a>
    </div>
  </header>

  <div class="wrap">
    <div id="badges"></div>
    <div id="chat"></div>

    <div class="row">
      <input id="q" placeholder="Ask about drawings, revisions, schedules…" />
      <button id="send">Send</button>
    </div>
    <div class="note">Tip: I’ll answer fast and include links when I reference files.</div>
  </div>

<script>
const chat = document.getElementById('chat');
const q = document.getElementById('q');
const send = document.getElementById('send');

function add(msg, who){ 
  const div = document.createElement('div');
  div.style.margin = '8px 0';
  div.innerHTML = `<span class="pill" style="background:${who==='you'?'#2d5a33':'#6b5f52'}">${who}</span> ${msg}`;
  chat.appendChild(div); chat.scrollTop = chat.scrollHeight;
}

send.addEventListener('click', async () => {
  const text = q.value.trim();
  if(!text) return;
  add(text, 'you');
  q.value = ''; q.focus();
  const res = await fetch('/ask', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({message:text})});
  const data = await res.json();
  add(data.answer || (data.error?'⚠️ '+data.error:'(no answer)'), 'AI');
});

q.addEventListener('keydown', (e)=>{ if(e.key==='Enter') send.click(); });

// small badge if we came back from Drive connect
const params = new URLSearchParams(location.search);
if (params.get('drive') === 'connected') {
  document.getElementById('badges').innerHTML = '<span class="pill">Google Drive connected</span>';
}
</script>
</body>
</html>

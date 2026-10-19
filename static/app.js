"use strict";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const state = {
  tab: "practice",
  recorder: null,
  chunks: [],
  recording: false,
  startedAt: 0,
  timer: null,
  audioUrl: null,
  result: null,
  selected: null,
};

/* ---------- American voice (browser text-to-speech) ---------- */
let usVoice = null;
function pickVoice() {
  const voices = speechSynthesis.getVoices().filter((v) => v.lang === "en-US" || v.lang === "en_US");
  const preferred = ["Samantha", "Google US English", "Microsoft Aria", "Microsoft Jenny", "Alex", "Ava", "Allison"];
  usVoice = preferred.map((n) => voices.find((v) => v.name.includes(n))).find(Boolean) || voices[0] || null;
}
if ("speechSynthesis" in window) {
  pickVoice();
  speechSynthesis.onvoiceschanged = pickVoice;
}
function speak(text, rate = 0.9) {
  if (!("speechSynthesis" in window)) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "en-US";
  if (usVoice) u.voice = usVoice;
  u.rate = rate;
  speechSynthesis.speak(u);
}

/* ---------- IPA toggle (off by default; plain respelling is the main display) ---------- */
function setIpa(on) {
  document.body.classList.toggle("show-ipa", on);
  $("toggle-ipa").checked = on;
  try { localStorage.setItem("showIpa", on ? "1" : "0"); } catch { /* storage unavailable */ }
}
$("toggle-ipa").addEventListener("change", (e) => setIpa(e.target.checked));
try { setIpa(localStorage.getItem("showIpa") === "1"); } catch { setIpa(false); }

const soundTile = (say, example) =>
  say ? `<span class="e">${esc(say)}</span>${example ? `<span class="ex">as in ${esc(example)}</span>` : ""}` : `<span class="e">+</span>`;

/* ---------- Tabs ---------- */
document.querySelectorAll(".tab").forEach((btn) =>
  btn.addEventListener("click", () => setTab(btn.dataset.tab))
);
function setTab(tab) {
  state.tab = tab;
  document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  $("record-panel").hidden = tab === "lookup";
  $("lookup-panel").hidden = tab !== "lookup";
  $("practice-controls").hidden = tab !== "practice";
  $("free-controls").hidden = tab !== "free";
  $("results").hidden = tab === "lookup" || !state.result || state.result.mode !== (tab === "practice" ? "target" : "free");
}

/* ---------- Model status ---------- */
async function pollStatus() {
  try {
    const s = await (await fetch("/api/status")).json();
    const el = $("model-status");
    if (s.phoneme_model && s.whisper_model) {
      el.textContent = "Models ready";
      el.className = "status ready";
      return;
    }
    el.textContent = "Loading speech models… (first run downloads ~1.7 GB)";
  } catch { /* server restarting */ }
  setTimeout(pollStatus, 2000);
}
pollStatus();

/* ---------- Practice sentences ---------- */
async function loadSentences() {
  const groups = await (await fetch("/api/sentences")).json();
  const chips = $("focus-chips");
  groups.forEach((g, gi) => {
    const b = document.createElement("button");
    b.className = "chip";
    b.textContent = g.focus;
    b.addEventListener("click", () => {
      const idx = (Number(b.dataset.next) || 0) % g.sentences.length;
      b.dataset.next = idx + 1;
      chips.querySelectorAll(".chip").forEach((c) => c.classList.toggle("active", c === b));
      setTarget(g.sentences[idx]);
    });
    chips.appendChild(b);
    if (gi === 0) { b.dataset.next = 1; b.classList.add("active"); setTarget(g.sentences[0]); }
  });
}
let ipaTimer = null;
function setTarget(text) {
  $("target").value = text;
  updateTargetIpa();
}
function updateTargetIpa() {
  clearTimeout(ipaTimer);
  ipaTimer = setTimeout(async () => {
    const text = $("target").value.trim();
    if (!text) { $("target-ipa").textContent = ""; return; }
    try {
      const r = await fetch("/api/pronounce?text=" + encodeURIComponent(text));
      if (!r.ok) return;
      const d = await r.json();
      $("target-ipa").innerHTML = `Say it like: <strong>${esc(d.respelling)}</strong><span class="ipa-only"> &nbsp;·&nbsp; <span class="ipa">/${esc(d.ipa)}/</span></span>`;
    } catch { /* ignore */ }
  }, 250);
}
$("target").addEventListener("input", updateTargetIpa);
$("btn-listen-target").addEventListener("click", () => speak($("target").value, 0.85));

/* ---------- Recording ---------- */
$("btn-record").addEventListener("click", () => (state.recording ? stopRecording() : startRecording()));

async function startRecording() {
  hideError();
  if (state.tab === "practice" && !$("target").value.trim()) {
    return showError("Type or choose a sentence to practice first.");
  }
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });
  } catch (e) {
    return showError("Microphone access was blocked. Allow microphone access for this page and try again.");
  }
  const mime = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"].find((m) => MediaRecorder.isTypeSupported(m));
  state.recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
  state.chunks = [];
  state.recorder.ondataavailable = (e) => e.data.size && state.chunks.push(e.data);
  state.recorder.onstop = () => {
    stream.getTracks().forEach((t) => t.stop());
    const blob = new Blob(state.chunks, { type: state.recorder.mimeType || "audio/webm" });
    submitRecording(blob);
  };
  state.recorder.start();
  state.recording = true;
  state.startedAt = Date.now();
  $("btn-record").classList.add("recording");
  $("rec-state").textContent = "Recording… press to stop";
  state.timer = setInterval(() => {
    const s = Math.floor((Date.now() - state.startedAt) / 1000);
    $("rec-timer").textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
    if (s >= 60) stopRecording();
  }, 250);
}

function stopRecording() {
  if (!state.recording) return;
  state.recording = false;
  clearInterval(state.timer);
  $("btn-record").classList.remove("recording");
  state.recorder.stop();
}

async function submitRecording(blob) {
  if (state.audioUrl) URL.revokeObjectURL(state.audioUrl);
  state.audioUrl = URL.createObjectURL(blob);
  const pb = $("playback");
  pb.src = state.audioUrl;
  pb.hidden = false;

  const btn = $("btn-record");
  btn.classList.add("busy");
  btn.disabled = true;
  $("rec-state").textContent = "Analyzing your pronunciation…";

  const form = new FormData();
  form.append("audio", blob, "recording");
  form.append("target", state.tab === "practice" ? $("target").value : "");
  try {
    const r = await fetch("/api/analyze", { method: "POST", body: form });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || "Analysis failed.");
    state.result = d;
    renderResults(d);
  } catch (e) {
    showError(e.message);
  } finally {
    btn.classList.remove("busy");
    btn.disabled = false;
    $("rec-state").textContent = "Press to record again";
  }
}

function showError(msg) { $("error").textContent = msg; $("error").hidden = false; }
function hideError() { $("error").hidden = true; }

/* ---------- Results ---------- */
function verdictFor(score) {
  if (score >= 90) return "Excellent — that sounded very American.";
  if (score >= 75) return "Good — a few sounds to polish.";
  if (score >= 55) return "Getting there — some clear sound errors.";
  return "Let's work on this one — several sounds were off.";
}

function renderResults(d) {
  $("results").hidden = false;
  const ring = $("score-ring");
  ring.style.setProperty("--p", d.overall);
  ring.style.setProperty("--c", d.overall >= 85 ? "var(--good)" : d.overall >= 60 ? "var(--fair)" : "var(--poor)");
  $("score").textContent = d.overall;
  $("verdict").textContent = verdictFor(d.overall);
  $("transcript").textContent = d.transcript ? `“${d.transcript}”` : "(nothing recognized)";
  $("expected-respelling").textContent = d.expected_respelling;
  $("heard-respelling").textContent = d.heard_respelling;
  $("expected-ipa").textContent = "/" + d.expected_ipa + "/";
  $("heard-ipa").textContent = "/" + d.heard_ipa + "/";

  const chips = $("word-chips");
  chips.innerHTML = "";
  d.words.forEach((w, i) => {
    const b = document.createElement("button");
    b.className = `w ${w.status}`;
    b.innerHTML = `${esc(w.word)}<small>${w.known ? esc(w.respelling) : "?"}</small>`;
    b.title = w.score == null ? "Not in dictionary" : `${w.score}%`;
    b.addEventListener("click", () => selectWord(i));
    chips.appendChild(b);
  });

  const pats = d.patterns || [];
  $("patterns-box").hidden = pats.length === 0;
  $("patterns").innerHTML = pats
    .map((p) => `<li><span class="pl">${esc(p.label)}<span class="ipa-only ipa pc"><br>${esc(p.label_ipa)}</span></span><span>${esc(p.tip)}<br><span class="pc">${p.count}× in this recording</span></span></li>`)
    .join("");

  const worst = d.words.reduce((best, w, i) => (w.score != null && (best < 0 || w.score < d.words[best].score) ? i : best), -1);
  if (worst >= 0 && d.words[worst].score < 85) selectWord(worst);
  else $("word-detail").hidden = true;
}

function playSegment(start, end) {
  const pb = $("playback");
  const off = state.result.audio_offset || 0;
  pb.currentTime = Math.max(0, start + off - 0.08);
  pb.play();
  clearTimeout(state.segTimer);
  state.segTimer = setTimeout(() => pb.pause(), (end - start + 0.16) * 1000);
}

function selectWord(i) {
  state.selected = i;
  const w = state.result.words[i];
  document.querySelectorAll("#word-chips .w").forEach((el, k) => el.classList.toggle("selected", k === i));
  const box = $("word-detail");
  box.hidden = false;

  if (!w.known) {
    box.innerHTML = `<div class="wd-word">${esc(w.word)}</div><p class="hint">This word isn't in the pronunciation dictionary, so it wasn't scored.</p>
      <button class="mini" data-say="${esc(w.word)}">🔊 Hear it</button>`;
    bindSay(box);
    return;
  }

  const phones = (w.phones || [])
    .map((p) => {
      const yours = p.status === "ok" ? "✓" : p.status === "missing" ? "missing" : `you: ${p.heard_say}`;
      const ipa = `<span class="h ipa ipa-only">/${esc(p.expected || "+")}/ → /${esc(p.heard || "—")}/</span>`;
      return `<div class="ph ${p.status}">${soundTile(p.expected_say, p.expected_example)}<span class="h">${esc(yours)}</span>${ipa}</div>`;
    })
    .join("");
  const issues = w.issues.length
    ? `<ul class="issues">${w.issues.map((x) => `<li class="${x.severity}">${esc(x.tip)}</li>`).join("")}</ul>`
    : `<p class="ok-msg">✓ Nicely pronounced.</p>`;
  const understood = w.understood === false ? `<p class="hint">⚠ A listener didn't recognize this word in your recording.</p>` : "";

  box.innerHTML = `
    <div class="wd-head">
      <span class="wd-word">${esc(w.word)} <span class="lg ${w.status}" style="font-size:14px;vertical-align:middle">${w.score}%</span></span>
      <span class="wd-buttons">
        <button class="mini" data-say="${esc(w.word)}">🔊 Correct</button>
        <button class="mini" data-say="${esc(w.word)}" data-rate="0.55">🐢 Slowly</button>
        ${w.start != null ? `<button class="mini" id="btn-mine">▶ Yours</button>` : ""}
      </span>
    </div>
    <dl class="pron-grid">
      <dt>Say it like</dt><dd class="respell-big">${esc(w.respelling)}</dd>
      <dt>You said</dt><dd>${esc(w.heard_respelling)}</dd>
      <dt class="ipa-only">IPA (correct)</dt><dd class="big ipa ipa-only">${esc(w.ipa)}</dd>
      <dt class="ipa-only">IPA (yours)</dt><dd class="ipa ipa-only">${esc(w.heard_ipa)}</dd>
      <dt class="ipa-only">ARPAbet</dt><dd class="ipa-only" style="font-size:14px;font-family:ui-monospace,monospace">${esc(w.arpabet)}</dd>
      ${w.variants && w.variants.length ? `<dt class="ipa-only">Also accepted</dt><dd class="ipa ipa-only">${w.variants.map(esc).join(", ")}</dd>` : ""}
    </dl>
    <div class="label">Sound by sound (the sound to make, and what you said)</div>
    <div class="phones">${phones}</div>
    ${understood}
    ${issues}
    ${w.notes.length ? `<ul class="notes">${w.notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul>` : ""}
  `;
  bindSay(box);
  const mine = $("btn-mine");
  if (mine) mine.addEventListener("click", () => playSegment(w.start, w.end));
}

function bindSay(root) {
  root.querySelectorAll("[data-say]").forEach((b) =>
    b.addEventListener("click", () => speak(b.dataset.say, Number(b.dataset.rate) || 0.85))
  );
}

/* ---------- Lookup ---------- */
$("lookup-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = $("lookup-input").value.trim();
  const out = $("lookup-results");
  if (!text) return;
  const r = await fetch("/api/pronounce?text=" + encodeURIComponent(text));
  const d = await r.json();
  if (!r.ok) { out.innerHTML = `<div class="error">${esc(d.detail)}</div>`; return; }
  const sentence = d.words.length > 1
    ? `<div class="lookup-sentence"><div class="respell-big">${esc(d.respelling)}</div><div class="ipa ipa-only">/${esc(d.ipa)}/</div>
       <button class="mini" data-say="${esc(text)}">🔊 Hear sentence</button></div>`
    : "";
  out.innerHTML = sentence + d.words.map((w) => w.known ? `
    <div class="lookup-card">
      <div class="wd-head"><span class="wd-word">${esc(w.word)}</span>
        <span class="wd-buttons"><button class="mini" data-say="${esc(w.word)}">🔊 Hear</button><button class="mini" data-say="${esc(w.word)}" data-rate="0.55">🐢 Slowly</button></span></div>
      <dl class="pron-grid">
        <dt>Say it like</dt><dd><span class="respell-big">${esc(w.respelling)}</span> <span class="hint">(${w.syllables} syllable${w.syllables > 1 ? "s" : ""}${w.syllables > 1 ? ", CAPS = say louder and longer" : ""})</span></dd>
        <dt class="ipa-only">American IPA</dt><dd class="big ipa ipa-only">${esc(w.ipa)}</dd>
        <dt class="ipa-only">ARPAbet</dt><dd class="ipa-only" style="font-size:14px;font-family:ui-monospace,monospace">${esc(w.arpabet)}</dd>
        ${w.variants.length ? `<dt class="ipa-only">Also accepted</dt><dd class="ipa ipa-only">${w.variants.map(esc).join(", ")}</dd>` : ""}
      </dl>
      ${w.notes.length ? `<ul class="notes">${w.notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul>` : ""}
    </div>` : `<div class="lookup-card"><span class="wd-word">${esc(w.word)}</span> <span class="hint">— not in the dictionary</span></div>`).join("");
  bindSay(out);
});

/* ---------- Keyboard: space toggles recording ---------- */
document.addEventListener("keydown", (e) => {
  if (e.code === "Space" && !["TEXTAREA", "INPUT", "BUTTON"].includes(document.activeElement.tagName) && state.tab !== "lookup") {
    e.preventDefault();
    state.recording ? stopRecording() : startRecording();
  }
});

loadSentences();
setTab("practice");

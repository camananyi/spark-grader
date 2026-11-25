(() => {
  const cfg = window.SPARK_CONFIG || {};
  const sheetReady = /^https?:\/\//.test(cfg.sheetUrl || "");
  const $ = (id) => document.getElementById(id);
  const GRADE_TIMEOUT_MS = 30000;

  // ---------- Remembering who is signed in (this browser only) ----------
  const store = {
    get() { try { return JSON.parse(localStorage.getItem("spark-student") || "null"); } catch (e) { return null; } },
    set(v) { try { localStorage.setItem("spark-student", JSON.stringify(v)); } catch (e) {} },
    clear() { try { localStorage.removeItem("spark-student"); } catch (e) {} },
  };
  let student = store.get();
  let current = null; // { slug, title, filename, source, results }

  async function callSheet(payload) {
    // text/plain keeps this a "simple" request, which Google Apps Script accepts from any website
    const res = await fetch(cfg.sheetUrl, { method: "POST", body: JSON.stringify(payload) });
    const text = await res.text();
    try { return JSON.parse(text); } catch (e) { throw new Error("The grading sheet sent back something unexpected."); }
  }

  // ---------- Step 1: sign in ----------
  function showSignedIn() {
    const on = !!student;
    $("signin-form").classList.toggle("hidden", on);
    $("signed-in").classList.toggle("hidden", !on);
    if (on) {
      $("hello").textContent = `Hi ${(student.name || "there").split(" ")[0]}!`;
      $("hello-email").textContent = student.email;
    }
    updateSubmitButton();
  }

  $("signin-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = $("email").value.trim().toLowerCase();
    const code = $("code").value.trim();
    const msg = $("signin-msg");
    msg.className = "msg";
    if (!email || !code) { msg.className = "msg error"; msg.textContent = "Type your email and your SPARK code."; return; }
    if (!sheetReady) {
      student = { email, code, name: "" };
      store.set(student); showSignedIn(); return;
    }
    $("signin-btn").disabled = true;
    msg.textContent = "Checking…";
    try {
      const reply = await callSheet({ source: "web", action: "signin", email, code });
      if (!reply.ok) throw new Error(reply.error || "That email and code don't match. Check both and try again.");
      student = { email, code, name: reply.name || "" };
      store.set(student);
      msg.textContent = "";
      showSignedIn();
    } catch (err) {
      msg.className = "msg error";
      msg.textContent = err.message.includes("Failed to fetch")
        ? "Couldn't reach SPARK. Check your internet connection and try again."
        : err.message;
    } finally {
      $("signin-btn").disabled = false;
    }
  });

  $("signout-btn").addEventListener("click", () => {
    student = null; store.clear(); showSignedIn();
  });

  // ---------- The Python grader, running in a background worker ----------
  let worker = null, nextId = 1, warm = false;
  const pending = new Map();

  function startWorker() {
    warm = false;
    worker = new Worker("worker.js", { type: "module" });
    worker.onmessage = (e) => {
      const p = pending.get(e.data.id);
      if (p) { pending.delete(e.data.id); p.resolve(e.data); }
    };
    worker.onerror = (e) => {
      for (const p of pending.values()) p.resolve({ ok: false, error: e.message || "worker error" });
      pending.clear();
    };
    ask({ type: "warmup" }).then((r) => { warm = r.ok; });
  }

  function ask(msg, timeoutMs) {
    const id = nextId++;
    return new Promise((resolve) => {
      pending.set(id, { resolve });
      worker.postMessage({ ...msg, id, pyodideUrl: cfg.pyodideUrl });
      if (timeoutMs) setTimeout(() => {
        if (!pending.has(id)) return;
        pending.delete(id);
        // A program stuck forever: throw this Python away and start a fresh one
        worker.terminate(); startWorker();
        resolve({ ok: false, timeout: true });
      }, timeoutMs);
    });
  }

  // ---------- Step 2: choose a file ----------
  let assignments = [];
  const assignmentsLoaded = fetch("checks/index.json", { cache: "no-cache" })
    .then((r) => r.json()).then((list) => { assignments = list; })
    .catch(() => { assignments = []; });

  function slugFor(filename) {
    // Downloads often become "week2_pennies (1).py"; treat that as the same file
    const base = filename.replace(/\s*\(\d+\)(?=\.py$)/i, "").replace(/\.py$/i, "").toLowerCase();
    return assignments.find((a) => a.slug === base);
  }

  function setStatus(text) {
    $("status").classList.toggle("hidden", !text);
    $("status-text").textContent = text || "";
  }

  async function handleFile(file) {
    $("file-msg").textContent = "";
    if (!file) return;
    await assignmentsLoaded;
    if (!/\.py$/i.test(file.name)) {
      $("file-msg").textContent = `"${file.name}" isn't a Python file. Choose the .py file you wrote.`;
      return;
    }
    const a = slugFor(file.name);
    if (!a) {
      const names = assignments.map((x) => x.slug + ".py").join(", ");
      $("file-msg").textContent = `There's no assignment called "${file.name}". Rename your file to match the assignment exactly: ${names}.`;
      return;
    }
    const source = await file.text();
    if (source.length > 100000) { $("file-msg").textContent = "That file is too big to be an assignment."; return; }

    $("results-card").classList.add("hidden");
    setStatus(warm ? "Checking your file…" : "Getting the grader ready. The first time takes about 15 seconds…");
    let checks;
    try {
      checks = await (await fetch(`checks/${a.slug}.py`, { cache: "no-cache" })).text();
    } catch (e) {
      setStatus(""); $("file-msg").textContent = "Couldn't load the checks. Check your internet connection and try again."; return;
    }
    const first = warm ? 0 : 90000; // allow time to download Python the first time
    const reply = await ask({ type: "grade", filename: a.slug + ".py", source, checks }, GRADE_TIMEOUT_MS + first);
    setStatus("");
    if (reply.ok) warm = true;
    if (!reply.ok) {
      if (reply.error) console.error("SPARK grader error:", reply.error);
      $("file-msg").textContent = reply.timeout
        ? "Your program never finished. Look for a loop that never ends, then try again."
        : "Something went wrong while checking. Reload the page and try again.";
      return;
    }
    current = { slug: a.slug, title: a.title, filename: file.name, source, results: reply.results };
    showResults();
  }

  const drop = $("drop"), picker = $("file");
  drop.addEventListener("click", () => picker.click());
  drop.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); picker.click(); } });
  picker.addEventListener("change", () => { handleFile(picker.files[0]); picker.value = ""; });
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); handleFile(e.dataTransfer.files[0]); });

  // ---------- Step 3: results and submitting ----------
  function showResults() {
    const list = $("results");
    list.innerHTML = "";
    let passed = 0;
    for (const r of current.results) {
      if (r.passed === true) passed++;
      const li = document.createElement("li");
      li.className = r.passed === true ? "pass" : r.passed === false ? "fail" : "wait";
      const face = document.createElement("div");
      face.className = "face";
      face.textContent = r.passed === true ? ":)" : r.passed === false ? ":(" : ":|";
      face.setAttribute("aria-label", r.passed === true ? "passed" : r.passed === false ? "needs fixing" : "not checked yet");
      const body = document.createElement("div");
      const desc = document.createElement("div"); desc.className = "desc"; desc.textContent = r.description;
      body.appendChild(desc);
      if (r.note) { const n = document.createElement("div"); n.className = "note"; n.textContent = r.note; body.appendChild(n); }
      if (r.help) { const h = document.createElement("div"); h.className = "help"; h.textContent = r.help; body.appendChild(h); }
      li.append(face, body);
      list.appendChild(li);
    }
    const total = current.results.length;
    $("results-title").textContent = current.title;
    $("results-count").textContent = passed === total ? `All ${total} checks passed!` : `${passed} of ${total} checks passed`;
    $("results-file").textContent = `File: ${current.filename}`;
    $("done").classList.add("hidden");
    $("submit-msg").textContent = "";
    $("results-card").classList.remove("hidden");
    updateSubmitButton();
    $("results-card").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function updateSubmitButton() {
    if (!current) return;
    const allPassed = current.results.every((r) => r.passed === true);
    const btn = $("submit-btn"), hint = $("submit-hint");
    btn.textContent = allPassed ? "Submit to SPARK" : "Submit anyway";
    btn.disabled = !sheetReady || !student;
    hint.textContent = !sheetReady ? "Submitting is off in practice mode."
      : !student ? "Sign in (step 1) to submit."
      : allPassed ? "" : "You can fix the :( first, or submit now and resubmit later.";
  }

  $("submit-btn").addEventListener("click", async () => {
    if (!current || !student) return;
    const btn = $("submit-btn");
    btn.disabled = true;
    $("submit-msg").textContent = "";
    try {
      const reply = await callSheet({
        source: "web", action: "submit", email: student.email, code: student.code,
        filename: current.filename, code_text: current.source,
        submissions: [{
          assignment: current.slug,
          checks: current.results.map((r) => ({
            name: r.name, description: r.description, passed: r.passed === true,
            note: [r.note, r.help].filter(Boolean).join(" "),
          })),
        }],
      });
      if (!reply.ok) throw new Error(reply.error || "The submission didn't go through.");
      const time = new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
      const done = $("done");
      done.textContent = `Submitted at ${time}! Your mentor will review it. You can submit again any time before the deadline; your latest submission is the one that counts.`;
      done.classList.remove("hidden");
    } catch (err) {
      $("submit-msg").textContent = err.message.includes("Failed to fetch")
        ? "Couldn't reach SPARK. Check your internet connection and try again."
        : err.message;
    } finally {
      btn.disabled = false;
    }
  });

  $("again-btn").addEventListener("click", () => {
    current = null;
    $("results-card").classList.add("hidden");
    $("drop").scrollIntoView({ behavior: "smooth", block: "center" });
    $("drop").focus();
  });

  // ---------- Start ----------
  if (!sheetReady) $("practice").classList.remove("hidden");
  showSignedIn();
  startWorker();
})();

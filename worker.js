// Runs Python (Pyodide) in the background so a stuck student program never freezes the page.
// Loaded as a module worker, which this version of Pyodide requires.
let ready = null;

async function start(pyodideUrl) {
  const { loadPyodide } = await import(pyodideUrl + "pyodide.mjs");
  const py = await loadPyodide({ indexURL: pyodideUrl });
  const harness = await (await fetch("grader/spark_grader.py", { cache: "no-cache" })).text();
  py.FS.mkdirTree("/spark");
  py.FS.writeFile("/spark/spark_grader.py", harness);
  py.runPython("import sys; sys.path.insert(0, '/spark'); import spark_grader");
  return py;
}

self.onmessage = async (event) => {
  const msg = event.data;
  try {
    if (!ready) ready = start(msg.pyodideUrl);
    const py = await ready;
    if (msg.type === "warmup") {
      self.postMessage({ id: msg.id, ok: true });
      return;
    }
    py.globals.set("_spark_filename", msg.filename);
    py.globals.set("_spark_source", msg.source);
    py.globals.set("_spark_checks", msg.checks);
    const json = py.runPython(
      "import json, spark_grader\n" +
      "json.dumps(spark_grader.grade(_spark_filename, _spark_source, _spark_checks))"
    );
    self.postMessage({ id: msg.id, ok: true, results: JSON.parse(json) });
  } catch (err) {
    self.postMessage({ id: msg.id, ok: false, error: String(err && err.message || err) });
  }
};

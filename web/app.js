(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var NS = "http://www.w3.org/2000/svg";
  var token = new URLSearchParams(location.search).get("token") || "";
  var chosen = null;
  var source = null;
  var timers = [];

  function el(tag, attrs, text) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (text != null) n.textContent = text;
    return n;
  }
  function svg(tag, attrs) {
    var n = document.createElementNS(NS, tag);
    Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    return n;
  }
  function notice(msg) {
    var n = $("notice");
    n.textContent = msg || "";
    n.hidden = !msg;
  }
  function headers() { return token ? { "X-Demo-Token": token } : {}; }
  function later(fn, ms) { timers.push(setTimeout(fn, ms)); }

  // ---- samples
  fetch("/api/samples").then(function (r) { return r.json(); }).then(function (list) {
    var box = $("sample-buttons");
    list.forEach(function (s) {
      var b = el("button", { type: "button", "class": "chip" }, s.id.replace("ws", "#") + " " + s.title);
      b.addEventListener("click", function () { start(null, s.id); });
      box.appendChild(b);
    });
  }).catch(function () {});

  // ---- file choice
  $("file").addEventListener("change", function (e) {
    chosen = e.target.files && e.target.files[0] || null;
    $("go").disabled = !chosen;
    $("file-name").hidden = !chosen;
    if (chosen) $("file-name").textContent = chosen.name + " (" + (chosen.size / 1048576).toFixed(1) + " MB)";
    notice("");
  });
  $("upload-form").addEventListener("submit", function (e) {
    e.preventDefault();
    if (chosen) start(chosen, null);
  });
  $("again").addEventListener("click", function () {
    reset();
    $("upload").hidden = false;
    $("upload").scrollIntoView({ behavior: "smooth" });
  });

  // Shrink very large phone photos in the browser; fall back to the original on any failure.
  function shrink(file) {
    if (file.size < 6 * 1048576 || !window.createImageBitmap) return Promise.resolve(file);
    return createImageBitmap(file, { imageOrientation: "from-image" }).then(function (bmp) {
      var s = Math.min(1, 2200 / Math.max(bmp.width, bmp.height));
      var c = document.createElement("canvas");
      c.width = Math.round(bmp.width * s); c.height = Math.round(bmp.height * s);
      c.getContext("2d").drawImage(bmp, 0, 0, c.width, c.height);
      return new Promise(function (res) {
        c.toBlob(function (b) { res(b || file); }, "image/jpeg", 0.88);
      });
    }).catch(function () { return file; });
  }

  function reset() {
    if (source) { source.close(); source = null; }
    timers.forEach(clearTimeout); timers = [];
    $("live").hidden = true; $("results").hidden = true;
    $("trace").innerHTML = ""; $("overlay").innerHTML = "";
    $("spinner").classList.remove("off");
    state.rects = {}; state.W = state.H = 0;
  }

  var state = { rects: {}, W: 0, H: 0 };

  function start(file, sample) {
    notice("");
    reset();
    $("go").disabled = true;
    var req;
    if (sample) {
      req = fetch("/api/run?sample=" + encodeURIComponent(sample), { method: "POST", headers: headers() });
    } else {
      req = shrink(file).then(function (blob) {
        var fd = new FormData();
        fd.append("file", blob, file.name || "worksheet.jpg");
        return fetch("/api/run", { method: "POST", body: fd, headers: headers() });
      });
    }
    req.then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!r.ok) throw new Error(j.detail || ("The server answered " + r.status + "."));
        return j;
      });
    }).then(function (j) {
      $("go").disabled = !chosen;
      watch(j.job);
    }).catch(function (err) {
      $("go").disabled = !chosen;
      notice(err.message || "Could not start the run.");
    });
  }

  function watch(job) {
    $("upload").hidden = true;
    $("live").hidden = false;
    $("live-title").textContent = "2. The agent at work";
    var photo = $("photo");
    photo.onload = function () { setViewBox(photo.naturalWidth, photo.naturalHeight); };
    photo.src = "/api/jobs/" + job + "/image";
    $("live").scrollIntoView({ behavior: "smooth" });

    var finished = false;
    source = new EventSource("/api/jobs/" + job + "/events");
    source.addEventListener("step", function (e) { onStep(JSON.parse(e.data)); });
    source.addEventListener("done", function (e) {
      finished = true; source.close();
      $("spinner").classList.add("off");
      $("live-title").textContent = "2. The agent's work";
      showResults(JSON.parse(e.data));
    });
    source.addEventListener("error", function (e) {
      if (e && e.data) {
        finished = true; source.close();
        $("spinner").classList.add("off");
        fail(JSON.parse(e.data).message);
      } else if (!finished) {
        source.close();
        $("spinner").classList.add("off");
        fail("The connection dropped before the run finished.");
      }
    });
  }

  function fail(msg) {
    $("upload").hidden = false;
    notice(msg);
    $("live").scrollIntoView({ behavior: "smooth" });
  }

  function setViewBox(w, h) {
    if (!w || !h) return;
    state.W = w; state.H = h;
    $("overlay").setAttribute("viewBox", "0 0 " + w + " " + h);
  }

  // ---- live trace + overlay
  function badgeFor(model) {
    var cls = "badge";
    if (/spark-open/.test(model)) return el("span", { "class": "badge open" }, "muse-spark-open");
    if (/spark/.test(model)) cls += " spark";
    else if (/sam/.test(model)) cls += " sam";
    else if (/image/.test(model)) cls += " img";
    return el("span", { "class": cls }, model || "code");
  }

  function onStep(s) {
    var li = el("li");
    li.appendChild(badgeFor(s.model));
    li.appendChild(el("span", null, s.action || ""));
    li.appendChild(el("span", { "class": "t" }, (s.t != null ? Number(s.t).toFixed(1) : "") + "s"));
    var list = $("trace");
    list.appendChild(li);
    list.scrollTop = list.scrollHeight;

    if (s.kind === "boxes") drawBoxes(s);
    else if (s.kind === "verdict" && s.verdict) paintVerdict(s.verdict);
  }

  function key(b) { return b.join(","); }
  function strokeFor(W) { return Math.max(1.5, W / 450); }

  function addRect(b, attrs) {
    var r = svg("rect", Object.assign({
      x: b[0], y: b[1], width: Math.max(1, b[2] - b[0]), height: Math.max(1, b[3] - b[1]), rx: 3
    }, attrs));
    $("overlay").appendChild(r);
    return r;
  }

  function drawBoxes(s) {
    if (s.size && s.size.length === 2) setViewBox(s.size[0], s.size[1]);
    var W = state.W || (s.size && s.size[0]) || 1000, sw = strokeFor(W);
    var nums = s.numbers || [], probs = s.problems || [];
    var step = Math.min(30, 1200 / Math.max(1, nums.length));
    nums.forEach(function (b, i) {
      later(function () {
        var r = addRect(b, { fill: "none", stroke: "#8a97a0", "stroke-opacity": ".55", "stroke-width": sw });
        r.setAttribute("class", "num");
      }, i * step);
    });
    later(function () {
      probs.forEach(function (b) {
        if (state.rects[key(b)]) return;  // a verdict already painted this box
        state.rects[key(b)] = addRect(b, {
          fill: "rgba(47,111,208,.06)", stroke: "#2f6fd0", "stroke-width": sw * 1.6, "stroke-opacity": ".9"
        });
      });
    }, nums.length * step + 150);
  }

  function paintVerdict(v) {
    if (!v.box) return;
    var ok = !!v.is_correct && !v.error;
    var color = v.error ? "#b7791f" : (ok ? "#1e8a4c" : "#c8412f");
    var W = state.W || 1000, sw = strokeFor(W);
    var r = state.rects[key(v.box)];
    if (!r) r = state.rects[key(v.box)] = addRect(v.box, {});
    r.setAttribute("fill", color); r.setAttribute("fill-opacity", ".18");
    r.setAttribute("stroke", color); r.setAttribute("stroke-width", sw * 2); r.setAttribute("stroke-opacity", "1");
    var fs = Math.max(14, W / 38), cx = v.box[0], cy = v.box[1];
    var g = svg("g", {});
    g.appendChild(svg("circle", { cx: cx + fs * .2, cy: cy + fs * .2, r: fs * .7, fill: color }));
    var t = svg("text", { x: cx + fs * .2, y: cy + fs * .2 + fs * .33, "text-anchor": "middle",
      "font-size": fs, "font-weight": "700", fill: "#fff", "font-family": "system-ui, sans-serif" });
    t.textContent = ok ? "✓" : (v.error ? "?" : "✗");
    g.appendChild(t);
    $("overlay").appendChild(g);
  }

  // ---- results
  function pdfHref(u) {
    if (!u) return "";
    var i = String(u).indexOf("practice/");
    if (/^https?:/.test(u) && i < 0) return u;
    return i >= 0 ? "/files/" + String(u).slice(i) : u;
  }

  function showResults(r) {
    r = r || {};
    var sc = r.score || {}, hdr = r.header || {};
    $("score-num").textContent = (sc.correct != null ? sc.correct : "?") + "/" + (sc.total != null ? sc.total : "?");
    $("sheet-title").textContent = [hdr.title, hdr.subject, hdr.level].filter(Boolean).join(" · ");
    var bits = [];
    if (sc.wrong) bits.push(sc.wrong + " to review");
    if (sc.errors) bits.push(sc.errors + " could not be graded");
    if (r.seconds != null) bits.push(Number(r.seconds).toFixed(0) + " s");
    if (r.usd != null) bits.push("$" + Number(r.usd).toFixed(3) + " of model time");
    $("run-meta").textContent = bits.join(" · ");

    var p = r.pattern || {};
    $("pattern").hidden = !(p.pattern || p.explanation);
    $("pattern-name").textContent = p.pattern || "";
    $("pattern-expl").textContent = p.explanation || "";

    var sum = typeof r.summary === "string" ? r.summary : "";
    $("summary-wrap").hidden = !sum;
    $("summary").textContent = sum;

    var ev = $("evidence");
    ev.innerHTML = "";
    (r.verdicts || []).forEach(function (v) {
      var cls = v.error ? "err" : (v.is_correct ? "ok" : "bad");
      var card = el("div", { "class": "ev " + cls });
      var head = el("div", { "class": "head" });
      head.appendChild(el("strong", null, "Problem " + v.index));
      head.appendChild(el("span", { "class": "verdict" }, v.error ? "not graded" : (v.is_correct ? "correct" : "check")));
      card.appendChild(head);
      function field(label, val, extra) {
        var f = el("div", { "class": "f" + (extra ? " " + extra : "") });
        f.appendChild(el("small", null, label));
        f.appendChild(el("span", null, val || "—"));
        card.appendChild(f);
      }
      field("Agent read", v.problem_text, "read");
      field("Written answer", v.written_answer);
      field("Correct answer", v.correct_answer);
      var why = v.error ? "The agent could not grade this one: " + v.error
        : [v.mistake, v.explanation].filter(Boolean).join(". ");
      if (why) card.appendChild(el("div", { "class": "why" }, why));
      ev.appendChild(card);
    });

    var pr = r.practice || {}, items = Array.isArray(pr.problems) ? pr.problems : [];
    $("practice-card").hidden = !items.length && !pr.pdf_url;
    $("checked").hidden = !(pr.checked || (items.length && items.every(function (i) { return i && i.checked; })));
    var ol = $("practice");
    ol.innerHTML = "";
    items.forEach(function (it) {
      var li = el("li");
      li.appendChild(el("span", null, (it && it.prompt) || String(it)));
      if (it && it.answer != null && it.answer !== "") li.appendChild(el("div", { "class": "ans" }, "Answer: " + it.answer));
      ol.appendChild(li);
    });
    var fx = $("keys-fixed");
    fx.hidden = !pr.keys_fixed;
    if (pr.keys_fixed) fx.textContent = "The agent caught " + pr.keys_fixed + " wrong answer key(s) in its own draft and fixed them.";
    var pv = $("sheet-preview");
    pv.hidden = !pr.png_url;
    if (pr.png_url) pv.src = pdfHref(pr.png_url);
    var a = $("pdf");
    a.hidden = !pr.pdf_url;
    if (pr.pdf_url) a.href = pdfHref(pr.pdf_url);

    $("results").hidden = false;
    setTimeout(function () { $("score-card").scrollIntoView({ behavior: "smooth" }); }, 400);
  }
})();

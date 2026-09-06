const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  PageBreak, TableOfContents, convertInchesToTwip, PageOrientation,
  ExternalHyperlink, LevelFormat,
} = require("docx");

// ── palette ────────────────────────────────────────────────────────
const INK   = "13272F";
const TEAL  = "1F7A8C";
const AMBER = "B3651F";
const MUTED = "5F7A85";
const RULE  = "D6E2E6";
const CODEBG= "F4F7F8";
const HDRBG = "13272F";
const ALTBG = "F7FAFB";
const QUOTEBG = "FFF6E8";

// code token colours
const C_KW="0B5FA5", C_STR="A31515", C_COM="6A8A94", C_NUM="098658", C_TYPE="267F99", C_FN="795E26";

const CONTENT_W = 9360;   // Letter 12240 - 2*1440 margins

// ── inline markdown → TextRun[] ────────────────────────────────────
function inline(text, base = {}) {
  const runs = [];
  // tokenise **bold**, *italic*, `code`, [text](url)
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
  let last = 0, m;
  const push = (t, o) => { if (t) runs.push(new TextRun({ text: t, ...base, ...o })); };
  while ((m = re.exec(text)) !== null) {
    push(text.slice(last, m.index), {});
    const tok = m[0];
    if (tok.startsWith("**")) push(tok.slice(2, -2), { bold: true });
    else if (tok.startsWith("`")) push(tok.slice(1, -1), { font: "Consolas", color: AMBER, size: (base.size || 20) - 2 });
    else if (tok.startsWith("[")) {
      const mm = /\[([^\]]+)\]\(([^)]+)\)/.exec(tok);
      runs.push(new ExternalHyperlink({
        children: [new TextRun({ text: mm[1], ...base, color: TEAL, underline: {} })],
        link: mm[2],
      }));
    } else push(tok.slice(1, -1), { italics: true });
    last = m.index + tok.length;
  }
  push(text.slice(last), {});
  return runs.length ? runs : [new TextRun({ text: "", ...base })];
}

function clean(s) {
  return s.replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">");
}

// ── syntax highlighting ────────────────────────────────────────────
const SQL_KW = /\b(CREATE|TABLE|TYPE|AS|ENUM|PRIMARY|KEY|DEFAULT|REFERENCES|ON|DELETE|UPDATE|CASCADE|RESTRICT|SET|NULL|NOT|UNIQUE|INDEX|USING|CHECK|BETWEEN|AND|OR|WHERE|SELECT|FROM|INSERT|INTO|VALUES|ALTER|ADD|COLUMN|CONSTRAINT|FOREIGN|EXTENSION|IF|EXISTS)\b/gi;
const SQL_TY = /\b(UUID|TEXT|CITEXT|INT|BIGSERIAL|SMALLINT|BOOLEAN|TIMESTAMPTZ|JSONB|NUMERIC|vector|user_role|case_status|case_origin|session_status|event_type)\b/g;
const PY_KW  = /\b(def|class|import|from|return|if|else|elif|for|in|while|try|except|with|as|None|True|False|and|or|not|lambda|yield|async|await|pass|raise|assert)\b/g;
const PY_TY  = /\b(str|int|float|bool|list|dict|tuple|UUID|BaseModel|Field|Literal|dataclass)\b/g;

function highlight(line, lang) {
  const runs = [];
  const F = { font: "Consolas", size: 16 };
  const isDiagram = /[│─┌┐└┘├┤▼►▲◄]/.test(line);
  if (isDiagram || !lang) { return [new TextRun({ text: line, ...F, color: lang ? INK : "3A5560" })]; }

  // comments first
  const cm = lang === "sql" ? /--.*$/ : /#.*$/;
  const cIdx = line.search(cm);
  let code = line, tail = "";
  if (cIdx >= 0) { code = line.slice(0, cIdx); tail = line.slice(cIdx); }

  // split on strings
  const parts = code.split(/('[^']*'|"[^"]*")/g);
  for (const p of parts) {
    if (!p) continue;
    if (/^['"]/.test(p)) { runs.push(new TextRun({ text: p, ...F, color: C_STR })); continue; }
    // keyword / type / number segmentation
    const kw = lang === "sql" ? SQL_KW : PY_KW;
    const ty = lang === "sql" ? SQL_TY : PY_TY;
    let seg = p, buf = "", i = 0;
    const toks = seg.split(/(\b\w+\b)/g);
    for (const t of toks) {
      if (!t) continue;
      kw.lastIndex = 0; ty.lastIndex = 0;
      if (kw.test(t))      runs.push(new TextRun({ text: t, ...F, color: C_KW, bold: true }));
      else if (ty.test(t)) runs.push(new TextRun({ text: t, ...F, color: C_TYPE }));
      else if (/^\d+(\.\d+)?$/.test(t)) runs.push(new TextRun({ text: t, ...F, color: C_NUM }));
      else runs.push(new TextRun({ text: t, ...F, color: INK }));
    }
  }
  if (tail) runs.push(new TextRun({ text: tail, ...F, color: C_COM, italics: true }));
  return runs.length ? runs : [new TextRun({ text: line, ...F, color: INK })];
}

// ── table column width heuristic ───────────────────────────────────
function colWidths(rows) {
  const n = rows[0].length;
  const maxLen = new Array(n).fill(1);
  rows.forEach(r => r.forEach((c, i) => {
    if (i < n) maxLen[i] = Math.max(maxLen[i], clean(String(c)).replace(/[*`]/g, "").length);
  }));
  const total = maxLen.reduce((a, b) => a + b, 0) || n;
  const min = Math.max(600, Math.floor(CONTENT_W / (n * 3.2)));
  // proportional, then floor at min, then rescale to exactly CONTENT_W
  let w = maxLen.map(l => Math.max(min, (l / total) * CONTENT_W));
  const s = w.reduce((a, b) => a + b, 0);
  w = w.map(x => Math.max(120, Math.floor((x * CONTENT_W) / s)));
  const diff = CONTENT_W - w.reduce((a, b) => a + b, 0);
  const widest = w.indexOf(Math.max(...w));
  w[widest] += diff;                      // absorb rounding in the widest column
  return w;
}

function buildTable(rows) {
  const widths = colWidths(rows);
  const trs = rows.map((cells, ri) => new TableRow({
    tableHeader: ri === 0,
    children: cells.map((c, ci) => new TableCell({
      width: { size: widths[ci], type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: ri === 0 ? HDRBG : (ri % 2 === 0 ? ALTBG : "FFFFFF") },
      margins: { top: 70, bottom: 70, left: 110, right: 110 },
      children: [new Paragraph({
        spacing: { before: 0, after: 0 },
        children: inline(clean(c), ri === 0
          ? { bold: true, color: "FFFFFF", size: 17 }
          : { size: 17, color: INK }),
      })],
    })),
  }));
  return new Table({
    columnWidths: widths,
    width: { size: CONTENT_W, type: WidthType.DXA },
    rows: trs,
    borders: {
      top:   { style: BorderStyle.SINGLE, size: 2, color: RULE },
      bottom:{ style: BorderStyle.SINGLE, size: 2, color: RULE },
      left:  { style: BorderStyle.SINGLE, size: 2, color: RULE },
      right: { style: BorderStyle.SINGLE, size: 2, color: RULE },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 1, color: RULE },
      insideVertical:   { style: BorderStyle.SINGLE, size: 1, color: RULE },
    },
  });
}

// ── parse markdown ─────────────────────────────────────────────────
const src = fs.readFileSync("PLATFORM_SPEC.md", "utf8").split("\n");
const body = [];
let i = 0;
let inTocSection = false;

// skip the front-matter block (title + meta) — rendered on the cover page
while (i < src.length && !/^# 0\. Preface/.test(src[i])) i++;

for (; i < src.length; i++) {
  let line = src[i];

  // ── code fence ──
  if (/^```/.test(line)) {
    const lang = line.replace(/```/, "").trim().toLowerCase() || null;
    const buf = [];
    i++;
    while (i < src.length && !/^```/.test(src[i])) { buf.push(src[i]); i++; }
    buf.forEach((cl, idx) => {
      body.push(new Paragraph({
        shading: { type: ShadingType.CLEAR, fill: CODEBG },
        spacing: { before: idx === 0 ? 100 : 0, after: idx === buf.length - 1 ? 140 : 0, line: 240 },
        indent: { left: 200, right: 200 },
        border: {
          left: { style: BorderStyle.SINGLE, size: 12, color: TEAL, space: 8 },
        },
        children: highlight(cl.length ? cl : " ", lang),
      }));
    });
    continue;
  }

  // ── table ──
  if (/^\|/.test(line) && i + 1 < src.length && /^\|[\s:|-]+\|/.test(src[i + 1])) {
    const rows = [];
    const parse = l => l.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(s => s.trim());
    rows.push(parse(line));
    i += 2; // skip separator
    while (i < src.length && /^\|/.test(src[i])) { rows.push(parse(src[i])); i++; }
    i--;
    body.push(buildTable(rows));
    body.push(new Paragraph({ text: "", spacing: { after: 160 } }));
    continue;
  }

  // ── headings ──
  let m;
  if ((m = /^# (.+)$/.exec(line))) {
    const t = clean(m[1]);
    if (/^Contents$/i.test(t)) { inTocSection = true; continue; }
    inTocSection = false;
    body.push(new Paragraph({ children: [new PageBreak()] }));
    body.push(new Paragraph({
      heading: HeadingLevel.HEADING_1,
      spacing: { before: 0, after: 200 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: TEAL, space: 6 } },
      children: [new TextRun({ text: t, bold: true, size: 34, color: INK, font: "Georgia" })],
    }));
    continue;
  }
  if ((m = /^## (.+)$/.exec(line))) {
    const t = clean(m[1]);
    if (/^Contents$/i.test(t)) { inTocSection = true; continue; }
    inTocSection = false;
    body.push(new Paragraph({
      heading: HeadingLevel.HEADING_2,
      spacing: { before: 300, after: 130 },
      children: [new TextRun({ text: t, bold: true, size: 25, color: TEAL, font: "Georgia" })],
    }));
    continue;
  }
  if ((m = /^### (.+)$/.exec(line))) {
    body.push(new Paragraph({
      heading: HeadingLevel.HEADING_3,
      spacing: { before: 220, after: 100 },
      children: [new TextRun({ text: clean(m[1]), bold: true, size: 22, color: INK, font: "Georgia" })],
    }));
    continue;
  }
  if (inTocSection) continue;

  // ── horizontal rule ──
  if (/^---+$/.test(line.trim())) {
    body.push(new Paragraph({
      spacing: { before: 120, after: 120 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: RULE, space: 2 } },
      children: [new TextRun({ text: "" })],
    }));
    continue;
  }

  // ── blockquote ──
  if ((m = /^>\s?(.*)$/.exec(line))) {
    const buf = [clean(m[1])];
    while (i + 1 < src.length && /^>\s?/.test(src[i + 1])) { i++; buf.push(clean(src[i].replace(/^>\s?/, ""))); }
    body.push(new Paragraph({
      shading: { type: ShadingType.CLEAR, fill: QUOTEBG },
      spacing: { before: 140, after: 160, line: 300 },
      indent: { left: 260, right: 200 },
      border: { left: { style: BorderStyle.SINGLE, size: 16, color: AMBER, space: 10 } },
      children: inline(buf.join(" "), { size: 20, color: INK }),
    }));
    continue;
  }

  // ── bullets ──
  if ((m = /^(\s*)[-*] (.+)$/.exec(line))) {
    const depth = Math.floor(m[1].length / 2);
    body.push(new Paragraph({
      bullet: { level: Math.min(depth, 2) },
      spacing: { before: 40, after: 40, line: 280 },
      children: inline(clean(m[2]), { size: 20, color: INK }),
    }));
    continue;
  }

  // ── numbered ──
  if ((m = /^(\s*)\d+\. (.+)$/.exec(line))) {
    body.push(new Paragraph({
      numbering: { reference: "num", level: 0 },
      spacing: { before: 40, after: 40, line: 280 },
      children: inline(clean(m[2]), { size: 20, color: INK }),
    }));
    continue;
  }

  // ── blank ──
  if (!line.trim()) continue;

  // ── paragraph ──
  body.push(new Paragraph({
    spacing: { before: 60, after: 120, line: 300 },
    children: inline(clean(line), { size: 20, color: INK }),
  }));
}

// ── cover page ─────────────────────────────────────────────────────
const cover = [
  new Paragraph({ text: "", spacing: { after: 2200 } }),
  new Paragraph({
    spacing: { after: 120 },
    children: [new TextRun({ text: "PLATFORM SPECIFICATION v2", bold: true, size: 19, color: AMBER, characterSpacing: 60 })],
  }),
  new Paragraph({
    spacing: { after: 100 },
    children: [new TextRun({ text: "VPSim", bold: true, size: 72, color: INK, font: "Georgia" })],
  }),
  new Paragraph({
    spacing: { after: 340 },
    children: [new TextRun({ text: "Admin Console · Accounts · Commercial Platform", size: 26, color: TEAL, font: "Georgia" })],
  }),
  new Paragraph({
    spacing: { after: 420 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: AMBER, space: 6 } },
    children: [new TextRun({ text: "" })],
  }),
  ...[
    ["Authors", "Vraj Patel (202301408) · Yogesh Bagotia (202301114)"],
    ["Mentor", "Abhishek Gupta"],
    ["Institution", "DAU (Dhirubhai Ambani University), Gandhinagar"],
    ["Status", "Draft v2.0 — supersedes parts of v1"],
    ["Scope", "Research prototype → commercial B2C product"],
  ].map(([k, v]) => new Paragraph({
    spacing: { after: 110 },
    children: [
      new TextRun({ text: k.padEnd(14), bold: true, size: 19, color: MUTED, font: "Consolas" }),
      new TextRun({ text: v, size: 21, color: INK }),
    ],
  })),
  new Paragraph({ children: [new PageBreak()] }),
  new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { after: 240 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: TEAL, space: 6 } },
    children: [new TextRun({ text: "Contents", bold: true, size: 34, color: INK, font: "Georgia" })],
  }),
  new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-3" }),
];

const doc = new Document({
  creator: "Vraj Patel, Yogesh Bagotia",
  title: "VPSim — System Design & Engineering Specification",
  numbering: {
    config: [{
      reference: "num",
      levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.START,
                 style: { paragraph: { indent: { left: 460, hanging: 260 } } } }],
    }],
  },
  styles: {
    default: { document: { run: { font: "Calibri", size: 20, color: INK } } },
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    children: [...cover, ...body],
  }],
});

Packer.toBuffer(doc).then(b => {
  fs.writeFileSync("VPSim_Platform_Spec.docx", b);
  console.log("Written VPSim_Platform_Spec.docx —", (b.length / 1024).toFixed(0), "KB");
});

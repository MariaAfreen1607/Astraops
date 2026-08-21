"use client";
import { useState } from "react";
import { api, ResearchAnswer } from "@/lib/api";
import Explain from "@/components/Explain";
import { Book } from "@/components/Sticker";

const EXAMPLES = [
  "Why did the February 2022 Starlink satellites re-enter?",
  "How does a geomagnetic storm change atmospheric density at 300 km?",
  "What mitigation measures reduce debris growth in low Earth orbit?",
];

export default function Research() {
  const [q, setQ] = useState("");
  const [res, setRes] = useState<ResearchAnswer | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const ask = async (question: string) => {
    if (!question.trim()) return;
    setBusy(true); setErr(null); setRes(null);
    try {
      const r = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/research/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, top_k: 5 }),
      });
      if (!r.ok) throw new Error((await r.json()).detail ?? r.statusText);
      setRes(await r.json());
    } catch (e: any) { setErr(e.message); }
    finally { setBusy(false); }
  };

  return (
    <div>
      <div className="flex items-center gap-3">
        <Book size={30} />
        <h1 className="doc-title">Research Copilot</h1>
      </div>
      <p className="mt-4 text-[13px]" style={{ maxWidth: "72ch" }}>
        Ask a question and get an answer drawn from indexed space-operations literature,
        with the source passages shown so you can check the reasoning yourself.
      </p>

      <div className="mt-7 flex gap-3">
        <input value={q} onChange={e => setQ(e.target.value)}
          onKeyDown={e => e.key === "Enter" && ask(q)}
          placeholder="Ask about orbital debris, space weather, or mission failures"
          className="field flex-1" />
        <button className="btn btn-primary" onClick={() => ask(q)} disabled={busy || !q.trim()}>
          {busy ? "Retrieving…" : "Ask"}
        </button>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {EXAMPLES.map(x => (
          <button key={x} className="chip chip-low" style={{ cursor: "pointer" }}
                  onClick={() => { setQ(x); ask(x); }}>{x}</button>
        ))}
      </div>

      {busy && (
        <div className="sheet mt-6 p-5">
          <div className="eyebrow">Retrieving</div>
          <div className="mt-2 text-[12.5px]">
            Embedding the question, searching the vector index, and asking Granite to answer from
            the retrieved passages.
          </div>
          <div className="mt-2 text-[11px]" style={{ color: "var(--ink-dim)" }}>
            The first query after a restart also builds the index and can take a minute.
          </div>
        </div>
      )}

      {err && <div className="sheet mt-6 p-4 text-[12.5px]" style={{ borderLeft: "3px solid var(--oxide)" }}>{err}</div>}

      {res && (
        <>
          <div className="brief-panel mt-7 p-5">
            <div className="eyebrow">Answer · {res.model_used}</div>
            <div className="mt-3 text-[13px] leading-relaxed" style={{ maxWidth: "78ch" }}>{res.answer}</div>
          </div>

          <div className="mt-6">
            <div className="eyebrow">Retrieved passages · ranked by similarity</div>
            <div className="mt-3 space-y-3">
              {res.sources.map((s, i) => (
                <div key={i} className="sheet p-4">
                  <div className="flex items-baseline justify-between gap-4">
                    <div className="text-[12px] font-medium">[{i + 1}] {s.title}</div>
                    <div className="text-[11px] shrink-0" style={{ color: "var(--ink-dim)" }}>
                      similarity {s.score.toFixed(3)}
                    </div>
                  </div>
                  <div className="mt-2 text-[11.5px] leading-relaxed" style={{ color: "var(--ink-mid)" }}>
                    {s.excerpt}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      <Explain title="How this works">
        <p>Source PDFs are split into 800-character passages and embedded with IBM&apos;s slate-125m
        retrieval model, then stored in a local Chroma vector database.</p>
        <p>Your question is embedded the same way, and the five nearest passages are retrieved by
        cosine similarity. Only those passages are given to Granite — the model answers from the
        retrieved text, not from its training data, and is instructed to say it doesn&apos;t know
        rather than guess.</p>
        <p>Every passage used is shown above with its similarity score, so an answer can always be
        traced back to a specific paragraph in a specific paper.</p>
      </Explain>
    </div>
  );
}

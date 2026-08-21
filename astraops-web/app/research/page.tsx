"use client";
export default function Research() {
  return (
    <div>
      <h1 className="text-2xl font-semibold">Research Copilot</h1>
      <p className="mt-1 text-sm text-slate-400">
        Retrieval-augmented answers over space mission literature, grounded in cited sources.
      </p>
      <div className="mt-8 rounded-lg border border-dashed border-slate-700 p-8 text-sm text-slate-500">
        RAG pipeline in progress — vector store and Granite retrieval chain.
      </div>
    </div>
  );
}

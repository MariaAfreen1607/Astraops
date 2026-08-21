export default function Explain({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="sheet mt-6 p-6">
      <div className="eyebrow">{title}</div>
      <div
        className="mt-4 text-[12.5px] leading-relaxed"
        style={{ columnWidth: "34rem", columnGap: "3rem" }}
      >
        {children}
      </div>
    </div>
  );
}

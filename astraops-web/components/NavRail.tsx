"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "Dashboard", hint: "Live status" },
  { href: "/conjunctions", label: "Conjunctions", hint: "Collision risk" },
  { href: "/spaceweather", label: "Space weather", hint: "Drag & radiation" },
  { href: "/research", label: "Research", hint: "Ask the literature" },
];

export default function NavRail() {
  const path = usePathname();
  return (
    <nav className="mt-9">
      {NAV.map(n => (
        <Link key={n.href} href={n.href} className="nav-item" data-active={path === n.href}>
          <div>{n.label}</div>
          <div className="eyebrow mt-0.5" style={{ fontSize: 9 }}>{n.hint}</div>
        </Link>
      ))}
    </nav>
  );
}

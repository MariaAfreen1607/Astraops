/** Flat 2D marks in the project palette — section markers, not decoration for its own sake. */

const C = { ink: "#14161A", plot: "#1F4E79", oxide: "#A8321E", amber: "#D9A21B", paper: "#F6F3EA" };

export function Rocket({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <path d="M16 3c4 3.5 6 8 6 13l-3 3h-6l-3-3c0-5 2-9.5 6-13z" fill={C.paper} stroke={C.ink} strokeWidth="1.6" strokeLinejoin="round"/>
      <circle cx="16" cy="12" r="2.6" fill={C.plot} stroke={C.ink} strokeWidth="1.4"/>
      <path d="M10 15l-4 4 4 .5M22 15l4 4-4 .5" fill={C.oxide} stroke={C.ink} strokeWidth="1.5" strokeLinejoin="round"/>
      <path d="M13 22c1 3 2 4.5 3 6 1-1.5 2-3 3-6" fill={C.amber} stroke={C.ink} strokeWidth="1.4" strokeLinejoin="round"/>
    </svg>
  );
}

export function Satellite({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <rect x="13" y="12" width="6" height="8" rx="1" fill={C.paper} stroke={C.ink} strokeWidth="1.6"/>
      <rect x="3" y="13" width="8" height="6" rx="1" fill={C.plot} stroke={C.ink} strokeWidth="1.5"/>
      <rect x="21" y="13" width="8" height="6" rx="1" fill={C.plot} stroke={C.ink} strokeWidth="1.5"/>
      <path d="M16 12V7" stroke={C.ink} strokeWidth="1.5"/>
      <circle cx="16" cy="6" r="1.8" fill={C.amber} stroke={C.ink} strokeWidth="1.3"/>
    </svg>
  );
}

export function Sun({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <circle cx="16" cy="16" r="6.5" fill={C.amber} stroke={C.ink} strokeWidth="1.6"/>
      {[0,45,90,135,180,225,270,315].map(a => (
        <path key={a} d="M16 5.5V2.5" stroke={C.ink} strokeWidth="1.6" strokeLinecap="round"
              transform={`rotate(${a} 16 16)`}/>
      ))}
    </svg>
  );
}

export function Star({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden>
      <path d="M12 2l2.6 6.6L21 11l-6.4 2.4L12 20l-2.6-6.6L3 11l6.4-2.4z"
            fill={C.paper} stroke={C.ink} strokeWidth="1.5" strokeLinejoin="round"/>
    </svg>
  );
}

export function Book({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <path d="M5 6h9a3 3 0 013 3v17a3 3 0 00-3-3H5z" fill={C.paper} stroke={C.ink} strokeWidth="1.6" strokeLinejoin="round"/>
      <path d="M27 6h-9a3 3 0 00-3 3v17a3 3 0 013-3h9z" fill={C.plot} stroke={C.ink} strokeWidth="1.6" strokeLinejoin="round"/>
    </svg>
  );
}

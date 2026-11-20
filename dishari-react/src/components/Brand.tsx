export function Brand() {
  return (
    <div className="brand" aria-label="Dishari">
      <span className="brand-mark" aria-hidden="true">
        <svg viewBox="0 0 32 32" width="32" height="32" fill="none">
          <path d="M16 7l-7 8m7-8 7 8M16 7v13" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="16" cy="25" r="2" fill="white" />
        </svg>
      </span>
      <span className="brand-name">Dishari</span>
      <span className="brand-bengali" lang="bn">দিশারী</span>
    </div>
  );
}

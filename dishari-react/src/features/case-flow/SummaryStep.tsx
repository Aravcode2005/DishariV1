import { AlertTriangle, ArrowLeft, Info, Printer, RotateCcw } from 'lucide-react';
import { StatusIcon } from '../../components/Status';
import type { ReviewBundle } from '../../domain/contracts';

interface Props { review: ReviewBundle; onBack(): void; onReset(): void }

export function SummaryStep({ review, onBack, onReset }: Props) {
  const { citizenSummary: summary, schemes, analysisOrigin } = review.result;
  const simulated = review.origin === 'bundled_demo' || analysisOrigin === 'sample';
  return <section className="page-section summary-page" aria-labelledby="summary-title">
    <div className="summary-controls no-print">
      <div className="page-heading">
        <p className="kicker">Step 3 of 3</p>
        <h1 id="summary-title">Citizen summary</h1>
        <p>Hand this to the applicant. It prints on one page.</p>
      </div>
      <div className="summary-top-actions">
        <button className="button button-secondary" type="button" onClick={onBack}><ArrowLeft size={18} aria-hidden="true" />Back to review</button>
        <button className="button button-primary" type="button" onClick={() => window.print()}><Printer size={18} aria-hidden="true" />Print</button>
      </div>
    </div>

    <article className="citizen-sheet sheet" lang="bn" aria-label="Printable citizen summary">
      {simulated && <div className="sheet-demo-banner">ডেমো নমুনা — সরকারি ব্যবহারের জন্য নয় / DEMONSTRATION ONLY</div>}
      <header className="sheet-header"><h2>{summary.title}</h2><p>{summary.applicantLabel}: <strong>{summary.applicantName}</strong></p></header>
      {summary.issue && <section className="sheet-issue">
        <h3><AlertTriangle size={30} aria-hidden="true" />{summary.issue.title}</h3>
        <p>{summary.issue.description}</p>
        <p><strong>{summary.issue.actionLabel}:</strong> {summary.issue.action}</p>
      </section>}
      <section aria-labelledby="sheet-scheme-title" className="sheet-schemes">
        <h3 id="sheet-scheme-title">{summary.schemesHeading}</h3>
        <div className="sheet-rows">
          {summary.rows.map((row) => {
            const scheme = schemes.find((candidate) => candidate.id === row.schemeId);
            if (!scheme) return null; // Server schema can include more rows; ignore dangling references safely.
            return <div className={`sheet-status sheet-${scheme.status}`} key={row.schemeId}>
              <span className="sheet-status-icon"><StatusIcon status={scheme.status} size={32} /></span>
              <div><strong>{row.title}</strong><p>{row.description}</p></div>
            </div>;
          })}
        </div>
      </section>
      <footer className="sheet-footer"><Info size={22} aria-hidden="true" /><span>{summary.footer}</span></footer>
    </article>
    <div className="new-case-row no-print"><button type="button" className="button button-secondary" onClick={onReset}><RotateCcw size={18} aria-hidden="true" />Start a new case</button></div>
  </section>;
}

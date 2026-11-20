import { AlertTriangle, ArrowLeft, Check, CheckCircle2, ExternalLink, Info, Wrench, XCircle } from 'lucide-react';
import { StatusPill, ProvisionalBadge } from '../../components/Status';
import { documentShortLabels, type Mismatch, type ReviewBundle, type Scheme } from '../../domain/contracts';
import { caseLine } from '../../lib/format';
import type { CaseForm } from '../../domain/contracts';

interface Props { form: CaseForm; review: ReviewBundle; onBack(): void; onApprove(): void }

function MismatchCard({ mismatch }: { mismatch: Mismatch }) {
  return <section className="mismatch-card" aria-label="Document mismatch">
    <div className="mismatch-title-row">
      <span className="status-pill mismatch-pill"><AlertTriangle size={18} aria-hidden="true" />Mismatch</span>
      <h2>{mismatch.title}</h2>
    </div>
    <div className="name-grid">
      {mismatch.values.map((item) => {
        const outlier = mismatch.likelyOutlier === item.doc;
        return <div className={`name-tile ${outlier ? 'name-outlier' : ''}`} key={item.doc}>
          <span className="name-source">{documentShortLabels[item.doc]}</span>
          <strong className="name-text">{item.value}</strong>
          <span className={`name-note ${outlier ? 'name-note-outlier' : ''}`}>
            {outlier ? <XCircle size={17} aria-hidden="true" /> : <CheckCircle2 size={17} aria-hidden="true" />}
            {item.note ?? (outlier ? 'Likely outlier' : 'Consistent with another document')}
          </span>
        </div>;
      })}
    </div>
    <div className="fix-route">
      <Wrench size={22} aria-hidden="true" />
      <div className="fix-text"><span className="overline">Fix route</span><strong>{mismatch.fix.label}</strong></div>
      <span className="route-chip route-cost">{mismatch.fix.cost}</span>
      <span className="route-chip route-place">{mismatch.fix.where}</span>
    </div>
    {mismatch.inferred && <span className="inference-badge"><Info size={16} aria-hidden="true" />Dishari's inference, not an official rule</span>}
  </section>;
}

function SchemeCard({ scheme }: { scheme: Scheme }) {
  const validLookup = scheme.lookupUrl && new URL(scheme.lookupUrl).protocol === 'https:';
  return <article className={`scheme-card scheme-${scheme.status}`}>
    <div><StatusPill status={scheme.status} /></div>
    <h3>{scheme.name}</h3>
    <p>{scheme.detail}</p>
    {scheme.missingDocuments && scheme.missingDocuments.length > 0 && <div className="missing-documents">
      <strong>Documents still needed</strong>
      <ul>{scheme.missingDocuments.map((doc) => <li key={doc}>{doc}</li>)}</ul>
    </div>}
    {scheme.reason && <p className="scheme-reason"><strong>Reason:</strong> {scheme.reason}</p>}
    {validLookup && <a href={scheme.lookupUrl} className="lookup-link" target="_blank" rel="noopener noreferrer">Look up on the PM-JAY site <ExternalLink size={17} aria-hidden="true" /></a>}
    {scheme.ruleSourceUrl && <a href={scheme.ruleSourceUrl} className="rule-source" target="_blank" rel="noopener noreferrer">View official rule source <ExternalLink size={15} aria-hidden="true" /></a>}
    {scheme.illustrative && <span className="illustrative-label">Illustrative demo result — not verified</span>}
    {scheme.provisional && <div className="scheme-card-footer"><ProvisionalBadge /></div>}
  </article>;
}

export function ReviewStep({ form, review, onBack, onApprove }: Props) {
  const { result } = review;
  const simulated = review.origin === 'bundled_demo' || result.analysisOrigin === 'sample';
  return <section className="page-section review-page no-print" aria-labelledby="review-title">
    <div className="page-heading">
      <p className="kicker">Step 2 of 3</p>
      <h1 id="review-title">Review the findings</h1>
      <p>{caseLine(form.applicant, form.crop, form.amount)}</p>
    </div>
    {simulated && <div className="sample-banner" role="status"><Info size={19} aria-hidden="true" /><div><strong>Sample results — demonstration only.</strong> This is not a real eligibility decision or verified government guidance.</div></div>}

    {result.mismatches.length > 0
      ? result.mismatches.map((mismatch, index) => <MismatchCard key={`${mismatch.field}-${index}`} mismatch={mismatch} />)
      : <div className="no-mismatch panel"><Check size={22} aria-hidden="true" /><span>No cross-document mismatches were reported. Check the originals before proceeding.</span></div>}

    <section aria-labelledby="scheme-title" className="schemes-section">
      <h2 id="scheme-title">Scheme eligibility</h2>
      <div className="scheme-grid">
        {result.schemes.map((scheme) => <SchemeCard key={scheme.id} scheme={scheme} />)}
      </div>
    </section>

    <div className="approve-bar">
      <div><h2>Dishari prepares. A person submits.</h2><p>Approve only after you have checked the findings above.</p></div>
      <div className="approve-actions">
        <button className="button button-secondary" type="button" onClick={onBack}><ArrowLeft size={18} aria-hidden="true" />Back</button>
        <button className="button button-primary" type="button" onClick={onApprove}><Check size={18} aria-hidden="true" />Approve and continue</button>
      </div>
    </div>
    <p className="review-footer-note"><AlertTriangle size={16} aria-hidden="true" />No government application is submitted by Dishari. Official submission stays with the operator.</p>
  </section>;
}

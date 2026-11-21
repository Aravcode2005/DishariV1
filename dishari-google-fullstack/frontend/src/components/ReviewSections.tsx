import { AlertTriangle, CheckCircle2, Clock3, ExternalLink, HelpCircle, Info, Wrench, XCircle } from 'lucide-react';
import type { CheckResult, Language } from '../contracts/types';
import { resolveText, safeExternalUrl } from '../contracts/types';
import { documentLabel, fieldLabel, t } from '../i18n/translations';

function sourceName(doc: string, lang: Language): string {
  const known: Record<string, 'aadhaar' | 'bank_passbook' | 'khatian'> = {
    aadhaar: 'aadhaar', aadhar: 'aadhaar', passbook: 'bank_passbook', bank_passbook: 'bank_passbook', khatian: 'khatian',
  };
  return known[doc.toLowerCase()] ? documentLabel(lang, known[doc.toLowerCase()]) : doc;
}
export function MismatchSection({ result, lang }: { result: CheckResult; lang: Language }) {
  return <section className="section-stack" aria-labelledby="mismatch-heading">
    <div className="section-heading"><h2 id="mismatch-heading">{t(lang, 'discrepancies')}</h2><span className="section-count">{result.mismatches.length.toString().padStart(2, '0')}</span></div>
    {result.mismatches.length === 0 ? <div className="clear-card"><CheckCircle2/><div><strong>{t(lang, 'noDiscrepancies')}</strong><p>{t(lang, 'noDiscrepanciesDesc')}</p></div></div>
    : result.mismatches.map((mismatch, index) => <article className="mismatch-card" key={`${mismatch.field}-${index}`}>
        <div className="mismatch-title"><span className="status-pill red"><AlertTriangle size={16}/>{t(lang, 'mismatch')}</span><h3>{fieldLabel(lang, mismatch.field)}</h3></div>
        <div className="evidence-grid">
          {mismatch.values.map((value, i) => <div className={`evidence-tile ${mismatch.likelyOutlier === value.doc ? 'outlier' : ''}`} key={`${value.doc}-${i}`}>
            <span className="evidence-label">{sourceName(value.doc, lang)}</span>
            <strong>{value.value}</strong>
            {mismatch.likelyOutlier === value.doc && <span className="outlier-note"><AlertTriangle size={14}/>{t(lang, 'likelyOutlier')}</span>}
          </div>)}
        </div>
        {mismatch.fix && <div className="fix-box"><Wrench size={19}/><div><small>{t(lang, 'correction')}</small><p>{resolveText(mismatch.fix.label, lang)}</p>
          {(mismatch.fix.cost || mismatch.fix.where) && <div className="chips">
            {mismatch.fix.cost && <span>{resolveText(mismatch.fix.cost, lang)}</span>}
            {mismatch.fix.where && <span>{resolveText(mismatch.fix.where, lang)}</span>}
          </div>}
        </div></div>}
        {mismatch.inferred && <span className="inference-note"><Info size={15}/>{t(lang, 'inference')}</span>}
      </article>)}
  </section>;
}

const iconMap = { eligible: CheckCircle2, cannot_determine: HelpCircle, not_eligible: XCircle };
const classMap = { eligible: 'green', cannot_determine: 'amber', not_eligible: 'red' };
export function SchemeSection({ result, lang }: { result: CheckResult; lang: Language }) {
  return <section className="section-stack" aria-labelledby="schemes-heading">
    <div className="section-heading"><div><h2 id="schemes-heading">{t(lang, 'schemes')}</h2><p>{t(lang, 'schemesDesc')}</p></div><span className="section-count">{result.schemes.length.toString().padStart(2, '0')}</span></div>
    {result.schemes.length === 0 && <div className="clear-card"><HelpCircle/><p>{t(lang, 'noSchemes')}</p></div>}
    <div className="schemes-grid">
      {result.schemes.map((scheme, index) => {
        const Icon = iconMap[scheme.status];
        const url = safeExternalUrl(scheme.sourceUrl || scheme.lookupUrl);
        return <article key={scheme.id ?? index} className={`scheme-card ${classMap[scheme.status]}`}>
          <span className={`status-pill ${classMap[scheme.status]}`}><Icon size={16}/>{t(lang, scheme.status)}</span>
          <h3>{resolveText(scheme.name, lang)}</h3>
          <p>{resolveText(scheme.detail, lang)}</p>
          {scheme.reason && <p>{resolveText(scheme.reason, lang)}</p>}
          {!!scheme.missingDocuments?.length && <div className="missing-documents"><strong>{t(lang, 'missingDocs')}</strong><ul>
            {scheme.missingDocuments.map((d, i) => <li key={i}>{resolveText(d, lang)}</li>)}
          </ul></div>}
          {url && <a className="external-link" href={url} target="_blank" rel="noopener noreferrer"><ExternalLink size={16}/>{t(lang, scheme.sourceUrl ? 'source' : 'lookup')}</a>}
          {scheme.ruleVersion && <small className="rule-version">{t(lang, 'ruleVersion')}: {scheme.ruleVersion}</small>}
          {scheme.provisional && <span className="provisional-note"><Clock3 size={15}/>{t(lang, 'provisional')}</span>}
        </article>;
      })}
    </div>
  </section>;
}

export { sourceName };

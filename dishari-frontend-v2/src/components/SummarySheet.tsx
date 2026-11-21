import { AlertTriangle, CheckCircle2, HelpCircle, XCircle } from 'lucide-react';
import type { ApplicantType, CheckResult, Language } from '../contracts/types';
import { resolveText } from '../contracts/types';
import { applicantLabel, fieldLabel, money, t } from '../i18n/translations';
import { sourceName } from './ReviewSections';

const statusIcon = { eligible: CheckCircle2, cannot_determine: HelpCircle, not_eligible: XCircle };
export default function SummarySheet({
  result, lang, applicant, crop, amount,
}: {
  result: CheckResult; lang: Language; applicant: ApplicantType | ''; crop: string; amount: number | null;
}) {
  const isSample = result.analysisOrigin === 'sample';
  return <article className="citizen-sheet" id="citizen-sheet" lang={lang} aria-label={t(lang, 'summaryHeading')}>
    <header className="sheet-header">
      <div className="sheet-brand"><span className="sheet-logo">↗</span> Dishari · দিশারী</div>
      <h2>{t(lang, 'summaryHeading')}</h2>
      {isSample && <strong className="sheet-sample">{t(lang, 'printSample')}</strong>}
    </header>
    <div className="sheet-details">
      {result.applicantName && <p><span>{result.applicantName}</span></p>}
      <p><span>{t(lang, 'applicantLabel')}</span><strong>{applicantLabel(lang, applicant)}</strong></p>
      <p><span>{t(lang, 'activityLabel')}</span><strong>{crop || t(lang, 'cropMissing')}</strong></p>
      <p><span>{t(lang, 'amountLabel')}</span><strong>{money(amount, lang)}</strong></p>
    </div>
    <section className="sheet-section">
      <h3>{t(lang, 'actionNeeded')}</h3>
      {result.mismatches.length ? result.mismatches.map((mismatch, index) => <div className="sheet-warning" key={index}>
        <AlertTriangle size={24} aria-hidden="true"/>
        <div><strong>{t(lang, 'mismatch')}: {fieldLabel(lang, mismatch.field)}</strong>
          <p>{mismatch.values.map(v => `${sourceName(v.doc, lang)}: ${v.value}`).join(' · ')}</p>
          {mismatch.fix && <p><strong>{t(lang, 'correction')}: </strong>{resolveText(mismatch.fix.label, lang)}</p>}
          {mismatch.inferred && <small>{t(lang, 'inference')}</small>}
        </div>
      </div>) : <p>{t(lang, 'noAction')}</p>}
    </section>
    <section className="sheet-section">
      <h3>{t(lang, 'screeningResults')}</h3>
      <div className="sheet-schemes">
        {result.schemes.length ? result.schemes.map((scheme, index) => {
          const Icon = statusIcon[scheme.status];
          return <div className={`sheet-scheme ${scheme.status}`} key={scheme.id ?? index}>
            <Icon size={23} aria-hidden="true"/><div>
              <strong>{resolveText(scheme.name, lang)} — {t(lang, scheme.status)}</strong>
              <p>{resolveText(scheme.detail, lang)}</p>
              {!!scheme.missingDocuments?.length && <p><b>{t(lang, 'nextDocuments')}:</b> {scheme.missingDocuments.map(d => resolveText(d, lang)).join(', ')}</p>}
              {scheme.provisional && <small>{t(lang, 'provisional')}</small>}
            </div>
          </div>;
        }) : <p>{t(lang, 'noSchemes')}</p>}
      </div>
    </section>
    {result.citizenSummary && <p className="sheet-extra">{resolveText(result.citizenSummary, lang)}</p>}
    <footer className="sheet-footer">{t(lang, 'disclaimer')}</footer>
  </article>;
}

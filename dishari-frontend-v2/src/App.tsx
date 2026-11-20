import { useEffect, useMemo, useState } from 'react';
import {
  AlertCircle, ArrowLeft, ArrowRight, CheckCircle2, FileCheck2,
  Languages, LockKeyhole, Printer, RotateCcw, ShieldCheck, Sparkles,
} from 'lucide-react';
import { ApiError, checkCase } from './api/caseApi';
import LanguageSwitch from './components/LanguageSwitch';
import Stepper from './components/Stepper';
import DocumentSlot from './components/DocumentSlot';
import { MismatchSection, SchemeSection } from './components/ReviewSections';
import SummarySheet from './components/SummarySheet';
import { demoResult } from './data/demo';
import type { ApplicantType, CheckResult, DocumentType, Language, UploadSlot } from './contracts/types';
import { emptySlots } from './contracts/types';
import { applicantLabel, money, t } from './i18n/translations';
import { checkUploadFile, isUploadReady, MAX_FILES_PER_DOCUMENT } from './utils/validation';

const errorFromApi = (lang: Language, error: unknown): string => {
  if (!(error instanceof ApiError)) return t(lang, 'serverError');
  if (error.code === 'network') return t(lang, 'networkError');
  if (error.code === 'timeout') return t(lang, 'timeoutError');
  if (error.code === 'invalid_response') return t(lang, 'contractError');
  return `${t(lang, 'serverError')} (HTTP ${error.status ?? 'error'})`;
};

export default function App() {
  const [lang, setLang] = useState<Language>('en');
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [consent, setConsent] = useState(false);
  const [applicant, setApplicant] = useState<ApplicantType | ''>('');
  const [crop, setCrop] = useState('');
  const [amount, setAmount] = useState('');
  const [slots, setSlots] = useState<UploadSlot[]>(emptySlots);
  const [result, setResult] = useState<CheckResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [errorCode, setErrorCode] = useState<unknown>(null);
  const [slotErrors, setSlotErrors] = useState<Record<number, 'fileInvalid' | 'fileTooLarge' | 'fileTooMany' | 'fileExists' | ''>>({});

  // All copy, including review and print, reacts to language changes immediately.
  useEffect(() => { document.documentElement.lang = lang; }, [lang]);

  const ready = useMemo(() => isUploadReady(consent, applicant, slots) &&
    (!amount || (Number.isSafeInteger(Number(amount)) && Number(amount) > 0)), [consent, applicant, slots, amount]);
  const completedCount = slots.filter(s => s.type && s.files.length).length;
  const numericAmount = amount.trim() === '' ? null : Number(amount);
  const validAmount = !amount || (Number.isSafeInteger(Number(amount)) && Number(amount) > 0);
  const hint = !consent ? 'hintConsent' : !applicant ? 'hintApplicant' : !validAmount ? 'hintAmount' : !ready ? 'hintDocs' : 'hintReady';
  const hasError = !!errorCode;

  const clearAll = () => {
    setStep(1); setConsent(false); setApplicant(''); setCrop(''); setAmount('');
    setSlots(emptySlots()); setResult(null); setBusy(false); setErrorCode(null); setSlotErrors({});
  };

  const setConsentChecked = (checked: boolean) => {
    setConsent(checked);
    if (!checked) { // Revoked consent invalidates local case data and any previous result.
      setSlots(emptySlots()); setResult(null); setStep(1); setErrorCode(null); setSlotErrors({});
    }
  };

  const changeType = (id: number, type: DocumentType | '') => {
    setSlots(previous => {
      // Defensive guard, not just disabled HTML options: duplicates cannot enter state.
      if (type && previous.some(s => s.id !== id && s.type === type)) return previous;
      return previous.map(s => s.id === id ? { ...s, type, files: s.type === type ? s.files : [] } : s);
    });
    setSlotErrors(previous => ({ ...previous, [id]: '' }));
    setErrorCode(null);
  };

  const addFiles = (id: number, inputFiles: File[]) => {
    const slot = slots.find(s => s.id === id);
    if (!slot || !slot.type) return;
    let nextError: 'fileInvalid' | 'fileTooLarge' | 'fileTooMany' | 'fileExists' | '' = '';
    let combined = [...slot.files];
    for (const file of inputFiles) {
      const reason = checkUploadFile(file);
      if (reason) { nextError = reason === 'invalid_type' ? 'fileInvalid' : 'fileTooLarge'; continue; }
      if (combined.length >= MAX_FILES_PER_DOCUMENT) { nextError = 'fileTooMany'; break; }
      if (combined.some(existing => existing.name === file.name && existing.size === file.size)) { nextError = 'fileExists'; continue; }
      combined.push(file);
    }
    setSlots(previous => previous.map(s => s.id === id ? { ...s, files: combined } : s));
    setSlotErrors(previous => ({ ...previous, [id]: nextError }));
    setErrorCode(null);
  };

  const removeFile = (id: number, index: number) => {
    setSlots(previous => previous.map(s => s.id === id ? { ...s, files: s.files.filter((_, fileIndex) => fileIndex !== index) } : s));
    setSlotErrors(previous => ({ ...previous, [id]: '' }));
  };

  const submit = async () => {
    if (!ready || !consent || !applicant || busy) return;
    setBusy(true); setErrorCode(null);
    try {
      const data = await checkCase({
        consent, applicant_type: applicant, crop_or_activity: crop.trim(),
        requested_loan_amount: numericAmount, preferred_language: lang, slots,
      });
      setResult(data);
      setStep(2);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
      setErrorCode(error);
    } finally { setBusy(false); }
  };

  const loadDemo = () => {
    if (!consent || busy) return;
    setApplicant('owner'); setCrop('Boro paddy'); setAmount('40000');
    setSlots([
      { id: 0, type: 'aadhaar', files: [] },
      { id: 1, type: 'bank_passbook', files: [] },
      { id: 2, type: 'khatian', files: [] },
    ]);
    setSlotErrors({}); setErrorCode(null); setResult(demoResult); setStep(2);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const goToStep = (nextStep: 1 | 2 | 3) => {
    setStep(nextStep); window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return <div className="app-shell">
    <header className="site-header no-print">
      <div className="container header-inner">
        <div className="brand"><span className="brand-mark"><span>↗</span><i/></span><div className="brand-name">Dishari <small>দিশারী</small></div></div>
        <div className="header-actions"><span className="operator-chip"><ShieldCheck size={15}/>{t(lang, 'operator')}</span><LanguageSwitch language={lang} onChange={setLang}/></div>
      </div>
    </header>

    <main className="container main-layout">
      <div className="top-intro no-print">
        <div className="intro-copy">
          <span className="eyebrow"><Sparkles size={15}/>{t(lang, 'eyebrow')}</span>
          <h1>{t(lang, 'heroTitle')} <em>{t(lang, 'heroAccent')}</em></h1>
          <p>{t(lang, 'heroDescription')}</p>
        </div>
        <aside className="intro-note"><span className="intro-note-icon"><LockKeyhole size={22}/></span><div><strong>{t(lang, 'secure')}</strong><p>{t(lang, 'powered')}</p></div></aside>
      </div>

      <Stepper step={step} lang={lang}/>

      {step === 1 && <div className="page-contents no-print">
        <div className="page-heading">
          <span className="kicker">{t(lang, 'stepOf', { current: 1 })}</span>
          <h2>{t(lang, 'uploadTitle')}</h2>
          <p>{t(lang, 'uploadDescription')}</p>
        </div>
        <section className={`consent-card ${consent ? 'consented' : ''}`}>
          <span className="consent-symbol"><ShieldCheck size={24}/></span>
          <label className="consent-main" htmlFor="consent"><strong>{t(lang, 'consentTitle')} <span className="required-asterisk">*</span></strong><span>{t(lang, 'consent')}</span>
            <small>{t(lang, 'consentNote')}</small></label>
          <input id="consent" type="checkbox" checked={consent} onChange={e => setConsentChecked(e.target.checked)} disabled={busy}/>
        </section>

        <fieldset disabled={!consent || busy} className={`form-fieldset ${!consent ? 'is-locked' : ''}`}>
          <div className="form-columns">
            <section className="card case-card">
              <div className="card-header"><span className="card-icon"><FileCheck2 size={21}/></span><div><h3>{t(lang, 'detailsTitle')}</h3><p>{t(lang, 'detailsSubtitle')}</p></div></div>
              <div className="form-fields">
                <div className="field-group"><label className="field-label" htmlFor="applicant-type">{t(lang, 'applicant')} <b>*</b></label>
                  <select id="applicant-type" className="field" value={applicant} onChange={e => setApplicant(e.target.value as ApplicantType | '')} required>
                    <option value="">{t(lang, 'selectApplicant')}</option>
                    {(['owner', 'tenant', 'joint', 'other'] as const).map(type => <option value={type} key={type}>{applicantLabel(lang, type)}</option>)}
                  </select></div>
                <div className="field-group"><label className="field-label" htmlFor="crop">{t(lang, 'crop')} <span className="optional">{t(lang, 'optional')}</span></label>
                  <input className="field" type="text" id="crop" maxLength={200} placeholder={t(lang, 'cropPlaceholder')} value={crop} onChange={e => setCrop(e.target.value)}/></div>
                <div className="field-group"><label className="field-label" htmlFor="amount">{t(lang, 'amount')} <span className="optional">{t(lang, 'optional')}</span></label>
                  <input className="field" type="number" id="amount" min="1" max="999999999" step="1" inputMode="numeric" placeholder={t(lang, 'amountPlaceholder')} value={amount} onChange={e => setAmount(e.target.value)}/></div>
              </div>
            </section>
            <section className="card documents-card">
              <div className="card-header doc-header"><span className="card-icon"><FileCheck2 size={21}/></span><div><h3>{t(lang, 'documentsTitle')}</h3><p>{t(lang, 'documentsSubtitle')}</p></div>
                <span className="completed-count">{t(lang, 'attached', { count: completedCount })}</span>
              </div>
              <div className="document-grid">
                {slots.map(slot => <DocumentSlot key={slot.id} slot={slot} slots={slots} lang={lang} locked={!consent || busy}
                  error={slotErrors[slot.id] ? t(lang, slotErrors[slot.id]) : ''} onTypeChange={changeType} onAddFiles={addFiles} onRemoveFile={removeFile}/>)}
              </div>
              <p className="duplicate-tip"><Languages size={16}/>{t(lang, 'duplicateInfo')}</p>
            </section>
          </div>
        </fieldset>

        <div className="action-card">
          <div className="action-row">
            <button className="btn btn-primary" type="button" disabled={!ready || busy} onClick={submit}>{busy ? <span className="loader"/> : <ArrowRight size={19}/>} {t(lang, busy ? 'checking' : 'check')}</button>
            <button className="btn btn-outline" type="button" disabled={!consent || busy} onClick={loadDemo}><Sparkles size={18}/>{t(lang, 'demo')}</button>
            <span className={`form-hint ${ready ? 'ready' : ''}`} role="status" aria-live="polite">{ready && <CheckCircle2 size={16}/>} {t(lang, hint)}</span>
          </div>
          <p className="demo-helper">{t(lang, 'demoNote')}</p>
          {hasError && <div className="api-error" role="alert"><AlertCircle size={22}/><div><strong>{t(lang, 'errorTitle')}</strong><p>{errorFromApi(lang, errorCode)}</p></div><button className="btn btn-outline btn-small" type="button" onClick={submit} disabled={!ready || busy}>{t(lang, 'tryAgain')}</button></div>}
        </div>
      </div>}

      {step === 2 && result && <div className="page-contents review-page no-print">
        <div className="page-heading"><span className="kicker">{t(lang, 'stepOf', { current: 2 })}</span><h2>{t(lang, 'reviewTitle')}</h2><p>{t(lang, 'reviewDescription')}</p></div>
        <div className={`source-banner ${result.analysisOrigin === 'sample' ? 'sample' : 'live'}`}><AlertCircle size={18}/>{t(lang, result.analysisOrigin === 'sample' ? 'sampleBanner' : 'liveBanner')}</div>
        <div className="case-brief"><div><small>{t(lang, 'caseSummary')}</small><strong>{applicantLabel(lang, applicant)}</strong></div><span className="brief-separator"/><span>{crop || t(lang, 'cropMissing')}</span><span className="brief-separator"/><span>{money(numericAmount, lang)}</span></div>
        <MismatchSection result={result} lang={lang}/>
        <SchemeSection result={result} lang={lang}/>
        <div className="approval-bar"><div><strong>{t(lang, 'approvalTitle')}</strong><p>{t(lang, 'approvalDesc')}</p></div><div className="approval-actions"><button className="btn btn-outline" onClick={() => goToStep(1)} type="button"><ArrowLeft size={18}/>{t(lang, 'back')}</button><button className="btn btn-primary" onClick={() => goToStep(3)} type="button">{t(lang, 'approve')}<ArrowRight size={18}/></button></div></div>
      </div>}

      {step === 3 && result && <div className="page-contents summary-page">
        <div className="summary-toolbar no-print"><div className="page-heading"><span className="kicker">{t(lang, 'stepOf', { current: 3 })}</span><h2>{t(lang, 'summaryTitle')}</h2><p>{t(lang, 'summaryDescription')}</p></div>
          <div className="summary-actions"><button className="btn btn-outline" onClick={() => goToStep(2)} type="button"><ArrowLeft size={18}/>{t(lang, 'backReview')}</button><button className="btn btn-primary" onClick={() => window.print()} type="button"><Printer size={18}/>{t(lang, 'print')}</button></div>
        </div>
        <SummarySheet result={result} lang={lang} applicant={applicant} crop={crop} amount={numericAmount}/>
        <div className="end-actions no-print"><button type="button" className="btn btn-quiet" onClick={clearAll}><RotateCcw size={17}/>{t(lang, 'startNew')}</button></div>
      </div>}
    </main>
    <footer className="site-footer no-print"><div className="container"><span>Dishari · দিশারী</span><span>{t(lang, 'footer')}</span></div></footer>
  </div>;
}

import { Check, FileCheck2, FilePlus2, Info, ShieldCheck } from 'lucide-react';
import { useState, type ChangeEvent } from 'react';
import {
  applicantLabels, applicantTypes, documentLabels, documentTypes,
  type CaseForm, type ApplicantType, type DocumentType,
} from '../../domain/contracts';

interface Props {
  form: CaseForm;
  instance: number;
  checking: boolean;
  error: string | null;
  onConsent(value: boolean): void;
  onApplicant(value: ApplicantType): void;
  onCrop(value: string): void;
  onAmount(value: string): void;
  onDocumentType(id: string, value: DocumentType): void;
  onDocumentFile(id: string, value: File | null): void;
  onCheck(): void;
  onDemo(): void;
}

const maxFileBytes = 10 * 1024 * 1024;
function acceptsFile(file: File): boolean {
  // Some devices omit MIME type; accept a known extension as a UX fallback.
  // The backend must independently inspect file signatures before processing.
  const supportedMime = file.type === 'application/pdf' || file.type.startsWith('image/');
  const supportedExtension = !file.type && /\.(pdf|png|jpe?g|webp|gif|bmp|heic)$/i.test(file.name);
  return (supportedMime || supportedExtension) && file.size <= maxFileBytes;
}

export function UploadStep(props: Props) {
  const { form, checking } = props;
  const [fileError, setFileError] = useState<string | null>(null);
  const locked = !form.consent || checking;
  const anyFile = form.slots.some((slot) => slot.file);
  const hint = !form.consent ? 'Tick the consent box to begin.' : !anyFile ? 'Add at least one document, or use the demo case.' : '';

  const onFileChange = (id: string, event: ChangeEvent<HTMLInputElement>) => {
    const file = event.currentTarget.files?.[0] ?? null;
    if (file && !acceptsFile(file)) {
      event.currentTarget.value = '';
      setFileError('Choose an image or PDF up to 10 MB.');
      return;
    }
    setFileError(null);
    props.onDocumentFile(id, file);
  };

  return <section className="page-section upload-page no-print" aria-labelledby="upload-title">
    <div className="page-heading">
      <p className="kicker">Step 1 of 3</p>
      <h1 id="upload-title">Upload the case</h1>
      <p>Tick consent, enter the case details, then add one file per document.</p>
    </div>

    <label className={`consent-panel ${form.consent ? 'consent-checked' : ''}`}>
      <input type="checkbox" checked={form.consent} onChange={(event) => props.onConsent(event.target.checked)} disabled={checking} />
      <span className="consent-copy"><strong><ShieldCheck size={18} aria-hidden="true" />Applicant consent</strong>
        <span>The applicant agrees that Dishari may read the documents below to check this case. Nothing runs until this box is ticked.</span>
      </span>
    </label>

    <fieldset disabled={locked} className={`input-fieldset ${locked ? 'fieldset-locked' : ''}`} aria-label="Case details and documents">
      <div className="upload-grid">
        <section className="panel details-card" aria-labelledby="case-details-title">
          <h2 id="case-details-title">Case details</h2>
          <div className="field-stack">
            <label htmlFor="applicant">Applicant type</label>
            <select id="applicant" value={form.applicant} onChange={(e) => props.onApplicant(e.target.value as ApplicantType)}>
              {applicantTypes.map((type) => <option key={type} value={type}>{applicantLabels[type]}</option>)}
            </select>
          </div>
          <div className="field-stack">
            <label htmlFor="crop">Crop or activity</label>
            <input id="crop" value={form.crop} placeholder="e.g. Boro paddy" onChange={(e) => props.onCrop(e.target.value)} autoComplete="off" maxLength={120} />
          </div>
          <div className="field-stack">
            <label htmlFor="amount">Requested loan amount (₹)</label>
            <input id="amount" value={form.amount} onChange={(e) => props.onAmount(e.target.value)} inputMode="numeric" pattern="[0-9]*" placeholder="e.g. 40000" autoComplete="off" />
          </div>
        </section>

        <section className="panel documents-card" aria-labelledby="documents-title">
          <h2 id="documents-title">Documents</h2>
          <p className="secondary-text">One slot per document. Say what it is, then add the file.</p>
          <div className="document-grid">
            {form.slots.map((slot, index) => {
              const label = slot.demoLabel ?? slot.file?.name;
              return <div className="document-slot" key={`${props.instance}-${slot.id}`}>
                <div className="field-stack">
                  <label htmlFor={`type-${slot.id}`}>Document {index + 1} is a</label>
                  <select id={`type-${slot.id}`} value={slot.type} onChange={(e) => props.onDocumentType(slot.id, e.target.value as DocumentType)}>
                    {documentTypes.map((type) => <option key={type} value={type}>{documentLabels[type]}</option>)}
                  </select>
                </div>
                <div className="field-stack">
                  <label htmlFor={`file-${slot.id}`}>File</label>
                  <input id={`file-${slot.id}`} type="file" accept="image/*,application/pdf" onChange={(event) => onFileChange(slot.id, event)} />
                </div>
                <div className={`file-status ${label ? 'file-attached' : ''}`} aria-live="polite">
                  {label ? <><FileCheck2 size={17} aria-hidden="true" /><span title={label}>{label}</span></> : <><FilePlus2 size={16} aria-hidden="true" />No file added yet</>}
                </div>
              </div>;
            })}
          </div>
        </section>
      </div>
    </fieldset>

    {(fileError || props.error) && <div className="inline-error" role="alert"><Info size={20} aria-hidden="true" /><span>{fileError || props.error}</span></div>}

    <div className="upload-actions">
      <button className="button button-primary" type="button" disabled={!form.consent || !anyFile || checking} onClick={props.onCheck}>
        {checking ? <span className="spinner" aria-hidden="true" /> : <Check size={19} aria-hidden="true" />}
        {checking ? 'Checking case…' : 'Check case'}
      </button>
      <button className="button button-secondary" type="button" disabled={!form.consent || checking} onClick={props.onDemo}>Use demo case</button>
      <span className="helper-text" aria-live="polite">{hint}</span>
    </div>
    <p className="demo-note"><Info size={16} aria-hidden="true" />Demo case loads a saved sample and needs no network. Documents are not submitted automatically.</p>
  </section>;
}

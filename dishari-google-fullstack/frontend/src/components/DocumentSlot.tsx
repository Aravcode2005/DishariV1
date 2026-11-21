import { CheckCircle2, FileImage, ImagePlus, X } from 'lucide-react';
import { useRef } from 'react';
import { documentTypes } from '../contracts/types';
import type { DocumentType, Language, UploadSlot } from '../contracts/types';
import { documentLabel, t } from '../i18n/translations';
import { MAX_FILES_PER_DOCUMENT, otherSelectedTypes } from '../utils/validation';

type Props = {
  slot: UploadSlot;
  slots: UploadSlot[];
  lang: Language;
  locked: boolean;
  error?: string;
  onTypeChange: (id: number, type: DocumentType | '') => void;
  onAddFiles: (id: number, files: File[]) => void;
  onRemoveFile: (id: number, index: number) => void;
};
export default function DocumentSlot({ slot, slots, lang, locked, error, onTypeChange, onAddFiles, onRemoveFile }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const unavailableTypes = otherSelectedTypes(slots, slot.id);
  const completed = slot.type !== '' && slot.files.length > 0;
  return <section className={`document-slot ${completed ? 'is-complete' : ''}`} aria-label={t(lang, 'slot', { index: slot.id + 1 })}>
    <div className="slot-top">
      <div className="slot-counter">{String(slot.id + 1).padStart(2, '0')}</div>
      <span className="slot-state">
        {completed ? <><CheckCircle2 size={15} />{t(lang, 'completed')}</> : t(lang, 'required')}
      </span>
    </div>
    <label htmlFor={`doc-type-${slot.id}`} className="field-label">{t(lang, 'documentType')}</label>
    <select id={`doc-type-${slot.id}`} className="field" value={slot.type} disabled={locked}
      onChange={event => onTypeChange(slot.id, event.target.value as DocumentType | '')} required>
      <option value="">{t(lang, 'selectDocument')}</option>
      {documentTypes.map(type => (
        <option key={type} value={type} disabled={unavailableTypes.has(type)}>{documentLabel(lang, type)}</option>
      ))}
    </select>
    <div className={`file-drop ${!slot.type || locked ? 'file-drop-disabled' : ''}`}>
      <input ref={inputRef} type="file" id={`doc-file-${slot.id}`} className="file-input" accept=".jpg,.jpeg,.png,image/jpeg,image/png" multiple
        disabled={locked || !slot.type} onChange={event => {
          const files = [...(event.target.files ?? [])];
          onAddFiles(slot.id, files);
          event.target.value = '';
        }}/>
      <label htmlFor={`doc-file-${slot.id}`} className="file-label">
        <ImagePlus size={22} aria-hidden="true"/>
        <span>{slot.type ? t(lang, 'uploadImages') : t(lang, 'selectFirst')}</span>
      </label>
      <p className="file-guide">{t(lang, 'imageGuide')}</p>
    </div>
    {slot.files.length ? <ul className="file-list" aria-label={`${slot.files.length} files`}>
      {slot.files.map((file, index) => <li key={`${file.name}-${file.size}-${index}`} className="file-item">
        <FileImage size={16} aria-hidden="true" />
        <span title={file.name}>{file.name}</span>
        <button className="icon-button" type="button" disabled={locked} title={t(lang, 'remove', { name: file.name })}
          aria-label={t(lang, 'remove', { name: file.name })} onClick={() => onRemoveFile(slot.id, index)}><X size={16}/></button>
      </li>)}
    </ul> : <p className="empty-file">{t(lang, 'noImages')}</p>}
    {slot.files.length > MAX_FILES_PER_DOCUMENT && <p className="field-error">{t(lang, 'fileTooMany')}</p>}
    {error && <p className="field-error" role="alert">{error}</p>}
  </section>;
}

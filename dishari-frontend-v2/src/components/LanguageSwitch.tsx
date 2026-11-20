import type { Language } from '../contracts/types';

type Props = { language: Language; onChange: (lang: Language) => void };
const languages: { id: Language; label: string }[] = [
  { id: 'en', label: 'English' },
  { id: 'hi', label: 'हिन्दी' },
  { id: 'bn', label: 'বাংলা' },
];
export default function LanguageSwitch({ language, onChange }: Props) {
  return (
    <div className="language-switch" role="group" aria-label="Interface language">
      {languages.map(({ id, label }) => (
        <button key={id} type="button" className={`language-button ${language === id ? 'active' : ''}`}
          aria-pressed={language === id} onClick={() => onChange(id)} lang={id}>
          {label}
        </button>
      ))}
    </div>
  );
}

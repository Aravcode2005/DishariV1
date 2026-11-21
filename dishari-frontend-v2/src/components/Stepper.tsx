import { Check } from 'lucide-react';
import type { Language } from '../contracts/types';
import { t } from '../i18n/translations';

type Props = { step: 1 | 2 | 3; lang: Language };
export default function Stepper({ step, lang }: Props) {
  const steps = [t(lang, 'stepUpload'), t(lang, 'stepReview'), t(lang, 'stepSummary')];
  return <nav className="stepper-nav no-print" aria-label="Progress">
    <ol className="stepper">
      {steps.map((label, index) => {
        const number = (index + 1) as 1 | 2 | 3;
        const state = number < step ? 'done' : number === step ? 'current' : 'next';
        return <li className={`step ${state}`} key={number} aria-current={state === 'current' ? 'step' : undefined}>
          <span className="step-bubble">{state === 'done' ? <Check size={20} strokeWidth={3} /> : number}</span>
          <span className="step-copy"><strong>{label}</strong><small>{t(lang, state)}</small></span>
        </li>;
      })}
    </ol>
  </nav>;
}

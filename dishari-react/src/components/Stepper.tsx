import { Check } from 'lucide-react';

const steps = ['Upload', 'Review', 'Citizen summary'] as const;
export function Stepper({ current }: { current: 1 | 2 | 3 }) {
  return (
    <nav className="stepper no-print" aria-label="Progress">
      <ol>
        {steps.map((name, index) => {
          const number = index + 1;
          const state = number < current ? 'done' : number === current ? 'current' : 'next';
          return (
            <li key={name} className={`stepper-item stepper-${state}`} aria-current={state === 'current' ? 'step' : undefined}>
              <span className="stepper-circle" aria-hidden="true">{state === 'done' ? <Check size={22} strokeWidth={2.2} /> : number}</span>
              <span className="stepper-copy"><span className="stepper-title">{name}</span><span className="stepper-state">{state === 'done' ? 'Done' : state === 'current' ? 'Current' : 'Next'}</span></span>
              {index < 2 && <span className="stepper-line" aria-hidden="true" />}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

import { CheckCircle2, HelpCircle, XCircle, Clock3 } from 'lucide-react';
import type { Scheme } from '../domain/contracts';

const settings = {
  eligible: { label: 'Eligible', Icon: CheckCircle2 },
  cannot_determine: { label: 'Cannot determine', Icon: HelpCircle },
  not_eligible: { label: 'Not eligible', Icon: XCircle },
} as const;

export function StatusPill({ status }: { status: Scheme['status'] }) {
  const { label, Icon } = settings[status];
  return <span className={`status-pill status-pill-${status}`}><Icon size={17} strokeWidth={2} aria-hidden="true" />{label}</span>;
}
export function ProvisionalBadge() {
  return <span className="provisional-badge"><Clock3 size={16} aria-hidden="true" />Provisional, verify at the office</span>;
}
export function StatusIcon({ status, size = 24 }: { status: Scheme['status']; size?: number }) {
  const { Icon } = settings[status];
  return <Icon size={size} strokeWidth={2} aria-hidden="true" />;
}

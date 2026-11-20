import { useEffect, useReducer, useRef } from 'react';
import { checkCase } from '../../api/caseApi';
import { demoForm, demoResult } from '../../data/demoCase';
import type { ApplicantType, CaseForm, CheckResult, DocumentType, ReviewBundle } from '../../domain/contracts';
import { friendlyError } from '../../lib/format';

type Step = 1 | 2 | 3;
type Phase = 'idle' | 'checking';
export interface WorkflowState {
  step: Step;
  form: CaseForm;
  review: ReviewBundle | null;
  phase: Phase;
  error: string | null;
  instance: number;
}

type Action =
  | { type: 'CONSENT'; value: boolean }
  | { type: 'APPLICANT'; value: ApplicantType }
  | { type: 'CROP'; value: string }
  | { type: 'AMOUNT'; value: string }
  | { type: 'DOC_TYPE'; id: string; value: DocumentType }
  | { type: 'DOC_FILE'; id: string; value: File | null }
  | { type: 'CHECKING' }
  | { type: 'CHECK_SUCCESS'; result: CheckResult }
  | { type: 'CHECK_ERROR'; message: string }
  | { type: 'DEMO' }
  | { type: 'BACK_UPLOAD' }
  | { type: 'APPROVE' }
  | { type: 'BACK_REVIEW' }
  | { type: 'RESET' };

const freshForm = (): CaseForm => ({
  consent: false, applicant: 'owner', crop: '', amount: '',
  slots: [
    { id: 'doc-1', type: 'aadhaar', file: null },
    { id: 'doc-2', type: 'khatian', file: null },
    { id: 'doc-3', type: 'passbook', file: null },
  ],
});

export const initialWorkflowState: WorkflowState = {
  step: 1, form: freshForm(), review: null, phase: 'idle', error: null, instance: 0,
};

/** Pure reducer: integration changes cannot mutate the UI state model. */
export function workflowReducer(state: WorkflowState, action: Action): WorkflowState {
  // Form is read-only during an in-flight request.
  if (state.phase === 'checking' && ['CONSENT', 'APPLICANT', 'CROP', 'AMOUNT', 'DOC_TYPE', 'DOC_FILE', 'DEMO'].includes(action.type)) return state;
  const edit = (form: CaseForm): WorkflowState => ({ ...state, form, review: null, error: null });
  switch (action.type) {
    case 'CONSENT':
      // Revocation drops retained document handles and any prior findings.
      return edit(action.value
        ? { ...state.form, consent: true }
        : { ...state.form, consent: false, slots: state.form.slots.map((slot) => ({ ...slot, file: null, demoLabel: undefined })) });
    case 'APPLICANT': return edit({ ...state.form, applicant: action.value });
    case 'CROP': return edit({ ...state.form, crop: action.value });
    case 'AMOUNT': return edit({ ...state.form, amount: action.value.replace(/[^\d]/g, '').slice(0, 12) });
    case 'DOC_TYPE': return edit({ ...state.form, slots: state.form.slots.map((slot) => slot.id === action.id ? { ...slot, type: action.value } : slot) });
    case 'DOC_FILE': return edit({ ...state.form, slots: state.form.slots.map((slot) => slot.id === action.id ? { ...slot, file: action.value, demoLabel: undefined } : slot) });
    case 'CHECKING': return { ...state, phase: 'checking', error: null };
    case 'CHECK_SUCCESS': return { ...state, phase: 'idle', step: 2, review: { result: action.result, origin: 'api' }, error: null };
    case 'CHECK_ERROR': return { ...state, phase: 'idle', error: action.message };
    case 'DEMO':
      if (!state.form.consent) return state;
      return { ...state, phase: 'idle', step: 2, form: { ...demoForm, slots: demoForm.slots.map((s) => ({ ...s })) }, review: { result: demoResult, origin: 'bundled_demo' }, error: null, instance: state.instance + 1 };
    case 'BACK_UPLOAD': return { ...state, step: 1, error: null };
    case 'APPROVE': return state.step === 2 && state.review ? { ...state, step: 3 } : state;
    case 'BACK_REVIEW': return { ...state, step: 2 };
    case 'RESET': return { ...initialWorkflowState, form: freshForm(), instance: state.instance + 1 };
  }
}

export function useCaseWorkflow() {
  const [state, dispatch] = useReducer(workflowReducer, initialWorkflowState);
  const abortRef = useRef<AbortController | null>(null);
  useEffect(() => () => abortRef.current?.abort(), []);

  const actions = {
    setConsent: (value: boolean) => dispatch({ type: 'CONSENT', value }),
    setApplicant: (value: ApplicantType) => dispatch({ type: 'APPLICANT', value }),
    setCrop: (value: string) => dispatch({ type: 'CROP', value }),
    setAmount: (value: string) => dispatch({ type: 'AMOUNT', value }),
    setDocumentType: (id: string, value: DocumentType) => dispatch({ type: 'DOC_TYPE', id, value }),
    setDocumentFile: (id: string, value: File | null) => dispatch({ type: 'DOC_FILE', id, value }),
    async check() {
      if (state.phase !== 'idle' || !state.form.consent || !state.form.slots.some((slot) => slot.file)) return;
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      dispatch({ type: 'CHECKING' });
      try {
        const result = await checkCase({ ...state.form }, controller.signal);
        if (!controller.signal.aborted) dispatch({ type: 'CHECK_SUCCESS', result });
      } catch (error) {
        if (!controller.signal.aborted) dispatch({ type: 'CHECK_ERROR', message: friendlyError(error) });
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
      }
    },
    demo: () => dispatch({ type: 'DEMO' }),
    backToUpload: () => dispatch({ type: 'BACK_UPLOAD' }),
    approve: () => dispatch({ type: 'APPROVE' }),
    backToReview: () => dispatch({ type: 'BACK_REVIEW' }),
    reset: () => { abortRef.current?.abort(); dispatch({ type: 'RESET' }); },
  };
  return { state, actions };
}

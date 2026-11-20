import { describe, expect, it } from 'vitest';
import { demoResult } from '../src/data/demoCase';
import { initialWorkflowState, workflowReducer } from '../src/features/case-flow/useCaseWorkflow';

function send(state: typeof initialWorkflowState, type: Parameters<typeof workflowReducer>[1]) {
  return workflowReducer(state, type);
}

describe('three-step operator workflow', () => {
  it('starts locked, no files, no review', () => {
    expect(initialWorkflowState.step).toBe(1);
    expect(initialWorkflowState.form.consent).toBe(false);
    expect(initialWorkflowState.review).toBe(null);
  });
  it('does not permit a demo without consent', () => {
    expect(send(initialWorkflowState, { type: 'DEMO' }).step).toBe(1);
  });
  it('loads bundled sample after consent without a network request', () => {
    const approved = send(initialWorkflowState, { type: 'CONSENT', value: true });
    const result = send(approved, { type: 'DEMO' });
    expect(result.step).toBe(2);
    expect(result.form.crop).toBe('Boro paddy');
    expect(result.review?.result.analysisOrigin).toBe('sample');
    expect(result.review?.result.mismatches[0]?.likelyOutlier).toBe('khatian');
  });
  it('requires explicit approval before seeing the citizen summary', () => {
    const consented = send(initialWorkflowState, { type: 'CONSENT', value: true });
    const reviewed = send(consented, { type: 'DEMO' });
    expect(reviewed.step).toBe(2);
    expect(send(reviewed, { type: 'APPROVE' }).step).toBe(3);
  });
  it('preserves case fields when returning from review', () => {
    const approved = send(initialWorkflowState, { type: 'CONSENT', value: true });
    const reviewed = send(approved, { type: 'DEMO' });
    const back = send(reviewed, { type: 'BACK_UPLOAD' });
    expect(back.step).toBe(1);
    expect(back.form.amount).toBe('40000');
  });
  it('clears sensitive document handles when consent is revoked', () => {
    const consented = send(initialWorkflowState, { type: 'CONSENT', value: true });
    const document = new File(['synthetic'], 'test.pdf', { type: 'application/pdf' });
    const withFile = send(consented, { type: 'DOC_FILE', id: 'doc-1', value: document });
    const revoked = send(withFile, { type: 'CONSENT', value: false });
    expect(revoked.form.slots.every((slot) => slot.file === null)).toBe(true);
    expect(revoked.review).toBeNull();
  });
  it('handles API success and surfaces separate result origin', () => {
    const checking = send(initialWorkflowState, { type: 'CHECKING' });
    const done = send(checking, { type: 'CHECK_SUCCESS', result: demoResult });
    expect(done.review?.origin).toBe('api');
    expect(done.step).toBe(2);
  });
  it('resets to a locked blank case', () => {
    const approved = send(initialWorkflowState, { type: 'CONSENT', value: true });
    const viewed = send(send(approved, { type: 'DEMO' }), { type: 'APPROVE' });
    const reset = send(viewed, { type: 'RESET' });
    expect(reset.step).toBe(1);
    expect(reset.form.consent).toBe(false);
    expect(reset.review).toBeNull();
    expect(reset.form.slots.every((slot) => !slot.file && !slot.demoLabel)).toBe(true);
  });
});

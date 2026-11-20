import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from '../src/app/App';

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe('Dishari operator UI', () => {
  it('gates fields and every action on consent', async () => {
    render(<App />);
    expect(screen.getByRole('button', { name: /check case/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /use demo case/i })).toBeDisabled();
    expect(screen.getByRole('combobox', { name: /applicant type/i })).toBeDisabled();
    await userEvent.click(screen.getByRole('checkbox', { name: /applicant consent/i }));
    expect(screen.getByRole('button', { name: /use demo case/i })).toBeEnabled();
    expect(screen.getByRole('button', { name: /check case/i })).toBeDisabled();
  });
  it('moves through demo review, summary, then resets', async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole('checkbox', { name: /applicant consent/i }));
    await user.click(screen.getByRole('button', { name: /use demo case/i }));
    expect(screen.getByRole('heading', { name: /review the findings/i })).toBeInTheDocument();
    expect(screen.getByText('Likely outlier')).toBeInTheDocument();
    expect(screen.getByText("Dishari's inference, not an official rule")).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /approve and continue/i }));
    expect(screen.getByRole('heading', { name: /citizen summary/i })).toBeInTheDocument();
    expect(screen.getByText(/DEMONSTRATION ONLY/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /start a new case/i }));
    expect(screen.getByRole('button', { name: /use demo case/i })).toBeDisabled();
  });
  it('retains demo fields on back navigation', async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole('checkbox', { name: /applicant consent/i }));
    await user.click(screen.getByRole('button', { name: /use demo case/i }));
    await user.click(screen.getByRole('button', { name: /^back$/i }));
    expect(screen.getByRole('textbox', { name: /crop or activity/i })).toHaveValue('Boro paddy');
    expect(screen.getByRole('textbox', { name: /requested loan amount/i })).toHaveValue('40000');
  });
});

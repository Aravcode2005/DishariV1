import { Brand } from '../components/Brand';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { Stepper } from '../components/Stepper';
import { UploadStep } from '../features/case-flow/UploadStep';
import { ReviewStep } from '../features/case-flow/ReviewStep';
import { SummaryStep } from '../features/case-flow/SummaryStep';
import { useCaseWorkflow } from '../features/case-flow/useCaseWorkflow';

function CaseApp() {
  const { state, actions } = useCaseWorkflow();
  return <>
    <header className="site-header no-print"><div className="container header-content"><Brand /><span className="operator-chip">Operator view</span></div></header>
    <main className="container main-container">
      <Stepper current={state.step} />
      {state.step === 1 && <UploadStep
        form={state.form} instance={state.instance} checking={state.phase === 'checking'} error={state.error}
        onConsent={actions.setConsent} onApplicant={actions.setApplicant} onCrop={actions.setCrop}
        onAmount={actions.setAmount} onDocumentType={actions.setDocumentType} onDocumentFile={actions.setDocumentFile}
        onCheck={actions.check} onDemo={actions.demo}
      />}
      {state.step === 2 && state.review && <ReviewStep form={state.form} review={state.review} onBack={actions.backToUpload} onApprove={actions.approve} />}
      {state.step === 3 && state.review && <SummaryStep review={state.review} onBack={actions.backToReview} onReset={actions.reset} />}
    </main>
  </>;
}

export function App() { return <ErrorBoundary><CaseApp /></ErrorBoundary>; }

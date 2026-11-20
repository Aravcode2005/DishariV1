/** Zero-dependency structural verification: run `node scripts/validate-package.mjs`. */
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import assert from 'node:assert/strict';
const root = resolve(import.meta.dirname, '..');
const file = (p) => readFileSync(join(root, p), 'utf8');
const required = [
  'package.json', '.env.example', 'README.md', 'src/main.tsx',
  'src/app/App.tsx', 'src/features/case-flow/UploadStep.tsx',
  'src/features/case-flow/ReviewStep.tsx', 'src/features/case-flow/SummaryStep.tsx',
  'src/features/case-flow/useCaseWorkflow.ts', 'src/domain/contracts.ts',
  'src/api/caseApi.ts', 'src/data/demoCase.ts', 'src/styles/tokens.css',
  'src/styles/print.css', 'docs/API_CONTRACTS.md', 'docs/ARCHITECTURE.md',
  'docs/INTEGRATION_PLAYBOOK.md', 'docs/ACCEPTANCE.md',
  'docs/diagrams/architecture.svg', 'docs/diagrams/processing-flow.svg',
  'docs/diagrams/data-model.svg', 'docs/diagrams/architecture.mmd',
  'public/mock/check-result.json', 'scripts/mock-api.mjs',
  'tests/app.test.tsx', 'tests/workflow.test.ts', 'tests/contracts.test.ts',
];
for (const name of required) assert(existsSync(join(root, name)), `Missing: ${name}`);
const tokens = file('src/styles/tokens.css');
for (const [name, hex] of Object.entries({
  '--bg': '#F5F3EE', '--surface': '#FFFFFF', '--primary': '#0E5A6B',
  '--eligible-fill': '#E7F3EA', '--uncertain-fill': '#FFF3D1', '--ineligible-fill': '#FDEBE8',
})) assert(tokens.includes(`${name}: ${hex}`), `Theme token differs: ${name}`);
const flow = file('src/features/case-flow/useCaseWorkflow.ts');
for (const action of ['CONSENT','CHECKING','CHECK_SUCCESS','CHECK_ERROR','DEMO','APPROVE','RESET']) {
  assert(flow.includes(`'${action}'`), `Missing workflow transition: ${action}`);
}
assert(file('src/api/caseApi.ts').includes('checkResultSchema.parse(raw)'), 'API response must be validated');
assert(file('src/features/case-flow/UploadStep.tsx').includes('<fieldset disabled={locked}'), 'Missing native consent gating');
assert(file('src/features/case-flow/SummaryStep.tsx').includes('window.print()'), 'Print hook is missing');
assert(file('src/data/demoCase.ts').includes("analysisOrigin: 'sample'"), 'Demo must be explicitly sample');
const mock = JSON.parse(file('public/mock/check-result.json'));
assert.equal(mock.analysisOrigin, 'sample');
assert.equal(mock.apiVersion, '1');
assert.equal(mock.citizenSummary.locale, 'bn');
assert(mock.schemes.every((s) => mock.citizenSummary.rows.some((r) => r.schemeId === s.id)), 'Scheme summary ID mismatch');
const dirs = ['src', 'tests'];
const sourcePaths = [];
const walk = (path) => {
  for (const item of readdirSync(join(root, path), { withFileTypes: true })) {
    const rel = join(path, item.name);
    if (item.isDirectory()) walk(rel);
    else if (rel.endsWith('.ts') || rel.endsWith('.tsx')) sourcePaths.push(rel);
  }
};
dirs.forEach(walk);
for (const path of sourcePaths) assert(!file(path).includes('dangerouslySetInnerHTML'), `Disallowed markup injection: ${path}`);
console.log(`✓ ${required.length} required files found`);
console.log('✓ Theme tokens, state transitions, consent, printing and sample markers verified');
console.log(`✓ Synthetic JSON cross-references and ${sourcePaths.length} TS/TSX files checked structurally`);
console.log('Note: structural validation is NOT a replacement for npm run typecheck/test/build.');

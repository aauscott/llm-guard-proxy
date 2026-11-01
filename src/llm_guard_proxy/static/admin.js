'use strict';
const $ = id => document.getElementById(id);
const labels = {
  terms: ['Terms', 'Words and phrases grouped by severity.'],
  regex: ['Pattern rules', 'Custom regular expressions defined below.'],
  secrets: ['Secrets', 'Common credentials, tokens, and private keys.'],
  prompt_injection: ['Prompt injection', 'Attempts to override instructions.'],
  url_obfuscation: ['URL obfuscation', 'Suspicious or disguised URLs.'],
  llama_guard: ['Model-based safety check', 'Use Llama Guard through Ollama or a compatible guard service.'],
  safety_llm_stub: ['Safety stub', 'Development placeholder, not a real safety model.']
};
const actions = ['allow', 'log', 'warn', 'block', 'redact', 'review'];
const severities = ['low', 'medium', 'high', 'critical'];
let state, draft, dirty = false, saving = false;
function status(message, error = false) { $('status').textContent = message; $('status').className = error ? 'error' : ''; }
function changed() { dirty = true; $('save').disabled = false; status('Unsaved changes'); }
function node(tag, text) { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; return el; }
function field(parent, label, value, update, choices, type = 'text') {
  const wrapper = node('label', label), input = node(choices ? 'select' : 'input');
  if (choices) choices.forEach(choice => { const option = node('option', choice); option.value = choice; input.append(option); });
  else input.type = type;
  input.value = value;
  if (type === 'number') { input.min = '0'; input.step = 'any'; }
  input.addEventListener('input', () => { update(type === 'number' ? Number(input.value) : input.value); changed(); });
  wrapper.append(input); parent.append(wrapper); return input;
}
function removeButton(parent, label, remove) { const button = node('button', 'Remove'); button.type = 'button'; button.className = 'remove'; button.setAttribute('aria-label', label); button.onclick = () => { remove(); changed(); }; parent.append(button); }
let termsExpanded = false;
function renderTermsSettings() {
  const row = node('tr'); row.id = 'terms-settings';
  const cell = node('td'); cell.colSpan = 3;
  const details = node('details'); details.id = 'terms-list'; details.open = termsExpanded;
  details.ontoggle = () => { termsExpanded = details.open; };
  const summary = node('summary'); summary.id = 'terms-summary';
  const updateCount = () => {
    const count = severities.reduce((total, severity) => total + draft.terms[severity].length, 0);
    summary.textContent = `Term lists (${count} ${count === 1 ? "term" : "terms"})`;
  };
  updateCount(); details.append(summary);
  details.append(node('p', 'One word or phrase per line. View and edit anytime. Input and Output control when these lists run.'));
  const lists = node('div'); lists.className = 'columns';
  ['critical', 'high', 'medium', 'low'].forEach(severity => {
    const label = node('label', `${severity[0].toUpperCase() + severity.slice(1)} severity`);
    const input = node('textarea'); input.id = `${severity}-terms`; input.rows = 5;
    input.placeholder = 'Add a word or phrase'; input.value = draft.terms[severity].join('\n');
    input.oninput = () => {
      draft.terms[severity] = input.value.split('\n').map(term => term.trim()).filter(Boolean);
      updateCount(); changed();
    };
    label.append(input); lists.append(label);
  });
  details.append(lists); cell.append(details); row.append(cell); $('classifiers').append(row);
}
let patternsExpanded = false;
function renderPatternSettings() {
  const row = node('tr'); row.id = 'pattern-settings';
  const cell = node('td'); cell.colSpan = 3;
  const details = node('details'); details.id = 'pattern-list'; details.open = patternsExpanded;
  details.ontoggle = () => { patternsExpanded = details.open; };
  const summary = node('summary'); summary.id = 'pattern-summary'; details.append(summary);
  details.append(node('p', 'View and edit patterns anytime. Input and Output control when these rules run.'));
  const rules = node('div'); rules.id = 'rules'; details.append(rules);
  // Reveal incomplete fields before the browser focuses a validation error.
  rules.addEventListener('invalid', () => { details.open = true; }, true);
  const add = node('button', 'Add rule'); add.type = 'button'; add.id = 'add-rule';
  add.onclick = () => {
    details.open = true;
    draft.regex.rules.push({name:'', pattern:'', severity:'high'});
    renderRules(); changed(); $('rules').lastElementChild.querySelector('input').focus();
  };
  cell.append(details, add);
  row.append(cell); $('classifiers').append(row);
  renderRules();
}
function renderRules() {
  $('rules').replaceChildren();
  if (!draft.regex.rules.length) $('rules').append(node('p', 'No pattern rules. Add one to match a custom pattern.'));
  draft.regex.rules.forEach((rule, index) => {
    const box = node('div'); box.className = 'rule';
    field(box, 'Rule name', rule.name, v => rule.name = v).required = true;
    field(box, 'Pattern (regular expression)', rule.pattern, v => rule.pattern = v).required = true;
    const row = node('div'); row.className = 'row';
    field(row, 'Severity', rule.severity, v => rule.severity = v, severities);
    removeButton(row, `Remove ${rule.name || 'rule'}`, () => { draft.regex.rules.splice(index, 1); renderRules(); });
    box.append(row); $('rules').append(box);
  });
  const count = draft.regex.rules.length;
  $('pattern-summary').textContent = `Custom patterns (${count} ${count === 1 ? 'rule' : 'rules'})`;
}
// Keep connection values in the draft when the controls are hidden.
function updateModelSettings() {
  $('model-settings').hidden = !['input', 'output'].some(stage =>
    draft.stages[stage].enabled_classifiers.includes('llama_guard'));
  const ollama = draft.llama_guard.provider === 'ollama';
  $('guard-model').parentElement.hidden = !ollama;
  $('guard-keep-alive').parentElement.hidden = !ollama;
}
function renderModelSettings() {
  const row = node('tr'); row.id = 'model-settings';
  const cell = node('td'); cell.colSpan = 3;
  const fields = node('div'); fields.className = 'columns';
  const config = draft.llama_guard;
  const provider = field(fields, 'Service type', config.provider, value => {
    config.provider = value;
    updateModelSettings();
  }, ['ollama', 'http']);
  provider.options[0].textContent = 'Ollama';
  provider.options[1].textContent = 'HTTP guard service';
  field(fields, 'Service URL (including port)', config.base_url, value => config.base_url = value);
  field(fields, 'Model', config.model, value => config.model = value).id = 'guard-model';
  cell.append(fields);
  const advanced = node('details');
  advanced.append(node('summary', 'Advanced connection settings'));
  const options = node('div'); options.className = 'columns';
  const timeout = field(options, 'Timeout (ms)', config.timeout_ms, value => config.timeout_ms = value, null, 'number');
  timeout.min = '1'; timeout.step = '1';
  field(options, 'Keep alive', config.keep_alive, value => config.keep_alive = value).id = 'guard-keep-alive';
  field(options, 'Finding severity', config.severity, value => config.severity = value, severities);
  advanced.append(options); cell.append(advanced); row.append(cell);
  $('classifiers').append(row);
  updateModelSettings();
}
function render() {
  ['name', 'description', 'mode'].forEach(key => { $(key).value = draft[key]; $(key).oninput = () => { draft[key] = $(key).value; changed(); }; });
  $('response').value = draft.defaults.canned_response;
  $('response').oninput = () => { draft.defaults.canned_response = $('response').value; changed(); };
  $('classifiers').replaceChildren();
  state.classifiers.forEach(name => {
    const row = node('tr'), cell = node('td'), [title, description] = labels[name] || [name, ''];
    cell.append(node('strong', title), node('p', description)); row.append(cell);
    ['input', 'output'].forEach(stage => {
      const td = node('td'), input = node('input'); input.type = 'checkbox';
      input.setAttribute('aria-label', `${title}: ${stage}`);
      input.checked = draft.stages[stage].enabled_classifiers.includes(name);
      input.onchange = () => { const list = draft.stages[stage].enabled_classifiers; draft.stages[stage].enabled_classifiers = input.checked ? [...list, name] : list.filter(n => n !== name); if (name === 'llama_guard') updateModelSettings(); changed(); };
      td.append(input); row.append(td);
    }); $('classifiers').append(row);
    if (name === 'llama_guard') renderModelSettings();
    if (name === 'regex') renderPatternSettings();
    if (name === 'terms') renderTermsSettings();
  });
  $('actions').replaceChildren();
  severities.forEach(level => field($('actions'), level[0].toUpperCase() + level.slice(1), draft.actions[level], v => draft.actions[level] = v, actions));
  $('advanced').replaceChildren();
  field($('advanced'), 'Classifier timeout (ms)', draft.defaults.classifier_timeout_ms, v => draft.defaults.classifier_timeout_ms = v, null, 'number').min = '1';
  field($('advanced'), 'Log prompt text', String(draft.defaults.log_prompts), v => draft.defaults.log_prompts = v === 'true', ['false', 'true']);
  ['block', 'warn', 'log'].forEach(action => { const input = field($('advanced'), `${action} confidence threshold (0–1)`, draft.thresholds[action], v => draft.thresholds[action] = v, null, 'number'); input.max = '1'; });
}
$('discard').onclick = () => { if (dirty && !confirm('Discard your unsaved changes?')) return; draft = structuredClone(state.policy); render(); dirty = false; $('save').disabled = true; status('Showing the active policy'); };
$('use-template').onclick = () => {
  const name = $('template').value; if (!name) return;
  if (dirty && !confirm('Replace your unsaved changes with this template?')) return;
  draft = structuredClone(name === 'new' ? state.templates.permissive : state.templates[name]);
  if (name === 'new') { draft.name = ''; draft.description = ''; draft.stages = {input:{enabled_classifiers:[]},output:{enabled_classifiers:[]}}; draft.terms = {critical:[],high:[],medium:[],low:[]}; draft.regex = {rules:[]}; }
  render(); changed(); $('name').focus();
};
$('editor').onsubmit = async event => {
  event.preventDefault(); if (saving) return;
  saving = true; $('save').disabled = true;
  // Freeze the draft while saving so the saved state always matches what is displayed.
  const controls = [...$('editor').querySelectorAll('input,select,textarea,button')]; controls.forEach(el => el.disabled = true);
  status('Saving policy…');
  try {
    const response = await fetch('/admin/policy', {method:'PUT', headers:{'Content-Type':'application/json','X-Editor-Token':state.token}, body:JSON.stringify({policy:draft, revision:state.revision})});
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : result.detail.map(e => `${e.loc.slice(2).join('.')}: ${e.msg}`).join('; '));
    state.revision = result.revision; state.policy = structuredClone(draft); dirty = false; status('Saved. New requests use this policy.');
  } catch (error) { status(error.message, true); }
  finally { saving = false; controls.forEach(el => el.disabled = false); $('save').disabled = !dirty; }
};
window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
(async () => {
  try {
    const response = await fetch('/admin/policy', {cache:'no-store'}); if (!response.ok) throw new Error('Unable to load the policy. Open this page on the proxy’s local address.');
    state = await response.json(); draft = structuredClone(state.policy);
    Object.entries(state.templates).forEach(([name, policy]) => { const option = node('option', name.replaceAll('_', ' ')); option.value = name; option.title = policy.description; $('template').append(option); });
    render(); $('editor').hidden = false; $('destination').textContent = `Saved to ${state.path}. Loaded automatically when the editor is enabled.`;
    status('Showing the active policy');
  } catch (error) { status(error.message, true); }
})();

import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';
import { parseTemplate } from '@angular/compiler';

const source = readFileSync('src/app/core/translations.ts', 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
}).outputText;
const exports = {};
vm.runInNewContext(compiled, { exports, Object });
const dictionary = exports.TRANSLATIONS;
for (const [key, values] of Object.entries(dictionary)) {
  assert.ok(values.fr?.trim() && values.ar?.trim(), `Missing locale value: ${key}`);
}
const files = ['src/app/app.component.ts', ...['pages','widgets'].flatMap(dir=>readdirSync(`src/app/${dir}`).filter(f => f.endsWith('.ts')).map(f => `src/app/${dir}/${f}`))];
const missing = new Set();
const exempt = new Set(['Career', 'Verse', 'Stripe · TEST', 'English', 'Français', 'you@example.com', '', '&#10003;', '&middot;', '·', '%', '--', 'G']);
function literal(expression) {
  const kind = expression?.constructor.name;
  if (kind === 'LiteralPrimitive' && typeof expression.value === 'string') {
    const key = expression.value.trim();
    if (/[A-Za-z]/.test(key) && !dictionary[key] && !exempt.has(key)) missing.add(key);
  } else if (kind === 'Conditional') {
    literal(expression.trueExp); literal(expression.falseExp);
  }
}
function expression(node) {
  if (!node) return;
  if (node.constructor.name === 'BindingPipe' && node.name === 't') literal(node.exp);
  for (const child of [node.ast, node.exp, node.left, node.right, node.trueExp, node.falseExp]) expression(child);
  for (const child of node.expressions ?? []) expression(child);
}
function visit(node) {
  if (node.constructor.name === 'Text' && /[A-Za-z]/.test(node.value) && !exempt.has(node.value.trim())) missing.add(`Untranslated template text: ${node.value.trim()}`);
  expression(node.value);
  for (const input of node.inputs ?? []) expression(input.value);
  for (const child of node.children ?? []) visit(child);
  for (const branch of node.branches ?? []) visit(branch);
  for (const child of node.empty?.children ?? []) visit(child);
}
for (const file of files) {
  const code = readFileSync(file, 'utf8');
  for (const match of code.matchAll(/template: ?`([\s\S]*?)`,/g)) {
    const template = parseTemplate(match[1], file, {preserveWhitespaces:true});
    assert.ok(!template.errors?.length, `${file}: ${template.errors}`);
    for (const node of template.nodes) visit(node);
  }
}
assert.deepEqual([...missing], [], 'Missing static interface translations');
const worker = readFileSync('public/push-worker.js', 'utf8');
const listeners = {};
const notifications = [];
const opened = [];
const fakeSelf = {
  location:{origin:'https://careerverse.example'},
  registration:{showNotification:async (title, data) => notifications.push({title,data})},
  clients:{matchAll:async () => [],openWindow:async url => opened.push(url)},
  addEventListener:(name,callback) => { listeners[name] = callback; },
};
vm.runInNewContext(worker, {self:fakeSelf,URL,console});
let promise;
listeners.push({data:{json:()=>({title:'Ready',body:'New results',path:'/results/4'})},waitUntil:value=>{promise=value;}});
await promise;
assert.equal(notifications[0].data.data.path, '/results/4');
for (const [path, expected] of [['/results/4','/results/4'],['https://evil.example','/notifications'],['//evil.example','/notifications']]) {
  listeners.notificationclick({notification:{close(){},data:{path}},waitUntil:value=>{promise=value;}});
  await promise;
  assert.equal(opened.at(-1), `https://careerverse.example${expected}`);
}
console.log(`Verified ${Object.keys(dictionary).length} locale entries, all static template strings and safe push-click routing.`);

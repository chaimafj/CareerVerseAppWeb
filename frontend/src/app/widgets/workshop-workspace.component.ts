import { Component, EventEmitter, Input, Output } from '@angular/core';
import { Question } from '../core/models';
import { TranslatePipe } from '../core/locale.service';

@Component({
  selector: 'app-workshop-workspace',
  standalone: true,
  imports: [TranslatePipe],
  template: `
    <section class="simulation-workbench">
    <header class="simulation-topline"><span><span class="simulation-dot" aria-hidden="true"></span>{{ 'INTERACTIVE SIMULATION' | t }}</span><span>{{ 'Safe training environment' | t }}</span></header>
    @if (question.kind === 'code') {
      <span class="pill premium-pill">{{ 'Code repair workshop' | t }}</span>
      <p class="muted">{{ 'Fill the missing fragment. Use the exact identifier, expression or number requested. Code is checked but never executed.' | t }}</p>
      <pre class="workshop-code" dir="ltr"><code>{{ question.workspace?.before }}<mark>{{ code || '________' }}</mark>{{ question.workspace?.after }}</code></pre>
      <label [for]="'code-' + question.id">{{ 'Your code fragment' | t }}</label>
      <textarea class="code-fragment" dir="ltr" [id]="'code-' + question.id" [value]="code"
        [disabled]="disabled" maxlength="500" spellcheck="false" autocomplete="off"
        (input)="editCode($event)"></textarea>
    }
    @if (question.kind === 'architecture') {
      <span class="pill premium-pill">{{ 'Architecture builder' | t }}</span>
      <p class="muted">{{ 'Choose a component to place in the highlighted slot. The arrows show the simplified flow.' | t }}</p>
      <div class="architecture-scroll" dir="ltr">
        <svg [attr.viewBox]="'0 0 ' + ((question.workspace?.nodes?.length ?? 0) * 220) + ' 150'"
          role="img" [attr.aria-label]="'Architecture diagram' | t" class="architecture-diagram">
          @for (node of question.workspace?.nodes ?? []; track $index; let i = $index) {
            @if (i > 0) {
              <line [attr.x1]="i * 220 - 30" y1="65" [attr.x2]="i * 220 + 8" y2="65" stroke="currentColor" stroke-width="2" />
              <path [attr.d]="'M ' + (i * 220) + ' 59 l 8 6 l -8 6'" fill="none" stroke="currentColor" stroke-width="2" />
            }
            <rect [attr.x]="i * 220 + 12" y="25" width="178" height="80" rx="12"
              [class.architecture-slot]="i === question.workspace?.gap" />
            <foreignObject [attr.x]="i * 220 + 20" y="30" width="162" height="70">
              <div xmlns="http://www.w3.org/1999/xhtml" class="architecture-node-label">{{ i === question.workspace?.gap ? selectedComponent() : node }}</div>
            </foreignObject>
          }
        </svg>
      </div>
      <fieldset class="component-bank" [disabled]="disabled">
        <legend>{{ 'Component bank' | t }}</legend>
        @for (option of question.options; track option.id) {
          <button type="button" class="theme-button" [class.selected]="selectedIds.includes(option.id)"
            [attr.aria-pressed]="selectedIds.includes(option.id)" (click)="choose.emit(option.id)">{{ option.text }}</button>
        }
      </fieldset>
    }
    @if (question.kind === 'evidence') {
      <span class="pill premium-pill">{{ 'Incident evidence desk' | t }}</span>
      <p class="body-copy">{{ question.workspace?.context }}</p>
      <p class="muted">{{ 'Mark every relevant evidence row. These records are fictional training data.' | t }}</p>
      <div class="evidence-rows" dir="ltr">
        @for (option of question.options; track option.id; let i = $index) {
          <button type="button" class="evidence-row" [class.selected]="selectedIds.includes(option.id)"
            [attr.aria-pressed]="selectedIds.includes(option.id)" [disabled]="disabled" (click)="choose.emit(option.id)">
            <span class="evidence-index">{{ i + 1 }}</span><code>{{ option.text }}</code>
            <span>{{ (selectedIds.includes(option.id) ? 'Marked' : 'Mark evidence') | t }}</span>
          </button>
        }
      </div>
    }
    @if (question.kind === 'sequence') {
      <span class="pill premium-pill">{{ 'Workflow simulator' | t }}</span>
      <p class="body-copy">{{ question.workspace?.context }}</p>
      <p class="muted">{{ 'Build the workflow in execution order. Add every stage, then use the arrows to rearrange it. No operations are executed.' | t }}</p>
      <div class="workflow-layout">
        <fieldset class="workflow-bank" [disabled]="disabled">
          <legend>{{ 'Available stages' | t }}</legend>
          @for (option of question.options; track option.id) {
            <button type="button" class="workflow-stage" [disabled]="selectedIds.includes(option.id)" (click)="choose.emit(option.id)">
              <span aria-hidden="true">{{ selectedIds.includes(option.id) ? '&#10003;' : '+' }}</span>{{ option.text }}
            </button>
          }
        </fieldset>
        <section class="workflow-canvas" [attr.aria-label]="'Your workflow' | t">
          <h3>{{ 'Your workflow' | t }} <span>{{ selectedIds.length }} / {{ question.options.length }}</span></h3>
          <ol class="workflow-steps">
            @for (step of orderedSteps(); track step.id; let i = $index) {
              <li><span class="workflow-index">{{ i + 1 }}</span><span class="workflow-text">{{ step.text }}</span>
                <div class="workflow-actions">
                  <button type="button" [disabled]="disabled || i === 0" (click)="move(i,-1)" [attr.aria-label]="('Move stage up' | t) + ': ' + step.text">&#8593;</button>
                  <button type="button" [disabled]="disabled || i === selectedIds.length - 1" (click)="move(i,1)" [attr.aria-label]="('Move stage down' | t) + ': ' + step.text">&#8595;</button>
                  <button type="button" [disabled]="disabled" (click)="choose.emit(step.id)" [attr.aria-label]="('Remove stage' | t) + ': ' + step.text">&#215;</button>
                </div>
              </li>
            } @empty {
              <li class="workflow-placeholder">{{ 'Choose a stage to start building your workflow.' | t }}</li>
            }
          </ol>
          <p class="workflow-status" role="status">{{ (selectedIds.length === question.options.length ? 'All stages placed. Review the order before submitting.' : 'Add all stages to complete this task.') | t }}</p>
        </section>
      </div>
    }
    <footer class="simulation-note">{{ 'Your work is saved when you submit the attempt. Correction and explanations appear after submission.' | t }}</footer>
    </section>
  `,
  styles: [`
    .simulation-workbench { margin-top: 18px; padding: 22px; border: 1px solid var(--line); border-radius: 18px; background: linear-gradient(140deg,var(--bg),var(--surface)); }
    .simulation-topline { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 10px; padding-bottom: 16px; margin-bottom: 20px; border-bottom: 1px solid var(--line); color: var(--muted); font-size: .8125rem; }
    .simulation-topline > span:first-child { display: flex; align-items: center; gap: 8px; font-weight: 750; color: var(--accent); letter-spacing: .8px; }
    .simulation-dot { width: 7px; height: 7px; background: #14b8a6; border-radius: 50%; }
    .simulation-note { border-top: 1px solid var(--line); margin-top: 22px; padding-top: 14px; font-size: .875rem; color: var(--muted); line-height: 1.65; }
    .workflow-layout { display: grid; grid-template-columns: minmax(0,1fr) minmax(0,1.2fr); gap: 20px; margin-top: 20px; }
    .workflow-bank { min-width: 0; }
    .workflow-bank legend { margin-bottom: 12px; }
    .workflow-stage { display: flex; gap: 10px; align-items: center; width: 100%; margin-bottom: 10px; padding: 14px; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); color: var(--ink); font-size: 1rem; line-height: 1.6; text-align: start; }
    .workflow-stage:not(:disabled):hover { border-color: var(--accent); background: var(--soft); }
    .workflow-stage:disabled { cursor: default; }
    .workflow-stage > span { color: var(--accent); font-size: 1.25rem; }
    .workflow-canvas { min-width: 0; padding: 18px; border: 1px dashed #9693ce; border-radius: 14px; background: var(--soft); }
    .workflow-canvas h3 { display: flex; flex-wrap: wrap; gap: 8px; justify-content: space-between; font-size: 1rem; }
    .workflow-canvas h3 > span { color: var(--muted); font-size: .875rem; }
    .workflow-steps { list-style: none; padding: 0; margin: 0; display: grid; gap: 14px; }
    .workflow-steps li { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; padding: 14px 12px; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); animation: workflow-arrive .2s ease-out; }
    .workflow-index { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 50%; background: var(--soft); color: var(--accent); font-size: .875rem; flex-shrink: 0; font-weight: 700; }
    .workflow-text { flex: 1; min-width: 120px; overflow-wrap: anywhere; font-size: 1rem; line-height: 1.6; }
    .workflow-actions { display: flex; gap: 5px; margin-inline-start: auto; }
    .workflow-actions button { min-width: 36px; height: 36px; border: 1px solid var(--line); background: var(--bg); color: var(--ink); border-radius: 8px; }
    .workflow-actions button:disabled { cursor: default; }
    .workflow-placeholder, .workflow-status { color: var(--muted); font-size: .875rem; line-height: 1.7; }
    .workflow-status { margin: 16px 0 0; }
    @keyframes workflow-arrive { from { opacity: .4; transform: translateY(5px); } to { opacity: 1; transform: none; } }
    @media (max-width:1000px) { .workflow-layout { grid-template-columns: minmax(0,1fr); } }
    @media (max-width:600px) { .simulation-workbench { padding: 15px; } .workflow-canvas { padding: 12px; } }
    @media (prefers-reduced-motion:reduce) { * { animation: none !important; } }
  `],
})
export class WorkshopWorkspaceComponent {
  @Input({required: true}) question!: Question;
  @Input() selectedIds: number[] = [];
  @Input() code = '';
  @Input() disabled = false;
  @Output() choose = new EventEmitter<number>();
  @Output() codeChange = new EventEmitter<string>();
  @Output() orderChange = new EventEmitter<number[]>();

  orderedSteps() {
    return this.selectedIds.flatMap(id => this.question.options.filter(option => option.id === id));
  }
  move(index: number, direction: number) {
    const target = index + direction;
    if (this.disabled || index < 0 || index >= this.selectedIds.length || target < 0 || target >= this.selectedIds.length) return;
    const next = [...this.selectedIds];
    [next[index], next[target]] = [next[target], next[index]];
    this.orderChange.emit(next);
  }

  editCode(event: Event) {
    if (event.target instanceof HTMLTextAreaElement) this.codeChange.emit(event.target.value);
  }
  selectedComponent() {
    return this.question.options.find(option => this.selectedIds.includes(option.id))?.text ?? '________';
  }
}

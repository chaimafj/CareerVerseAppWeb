import { Component, EventEmitter, Input, Output } from '@angular/core';
import { Question } from '../core/models';
import { TranslatePipe } from '../core/locale.service';

@Component({
  selector: 'app-workshop-workspace',
  standalone: true,
  imports: [TranslatePipe],
  template: `
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
  `,
})
export class WorkshopWorkspaceComponent {
  @Input({required: true}) question!: Question;
  @Input() selectedIds: number[] = [];
  @Input() code = '';
  @Input() disabled = false;
  @Output() choose = new EventEmitter<number>();
  @Output() codeChange = new EventEmitter<string>();

  editCode(event: Event) {
    if (event.target instanceof HTMLTextAreaElement) this.codeChange.emit(event.target.value);
  }
  selectedComponent() {
    return this.question.options.find(option => this.selectedIds.includes(option.id))?.text ?? '________';
  }
}

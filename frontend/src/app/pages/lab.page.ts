import { LocalDatePipe, LocaleService, TranslatePipe } from '../core/locale.service';
import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { KeyValuePipe } from '@angular/common';
import { ActivatedRoute, CanDeactivateFn, Router, RouterLink } from '@angular/router';
import { IonicModule } from '@ionic/angular';
import { ApiService, errorMessage } from '../core/api.service';
import { Attempt, CareerAssessment, LabDetail, Question, Result } from '../core/models';
import { WorkshopWorkspaceComponent } from '../widgets/workshop-workspace.component';
import { CareerAssessmentComponent } from '../widgets/career-assessment.component';

@Component({
  standalone: true,
  imports: [TranslatePipe, LocalDatePipe, IonicModule, RouterLink, WorkshopWorkspaceComponent],
  template: `
    <div class="page-heading"><div><span class="eyebrow">{{ 'PUT YOUR KNOWLEDGE TO WORK' | t }}</span><h1>{{ 'Career simulation' | t }}</h1><p class="muted">{{ 'Your answers are evaluated by the server. Take your time and think it through.' | t }}</p></div></div>
    @if (error()) { <div class="error" role="alert">{{ (error()) | t }} @if (!attempt()) { <button (click)="load()">{{ 'Retry' | t }}</button> }</div> }
    @if (loading()) { <div class="loading"><ion-spinner /> {{ 'Preparing your lab...' | t }}</div> }
    @if (!attempt() && !loading() && detail(); as lab) {
      <section class="panel mission-panel">
        <span class="pill" [class.premium-pill]="lab.is_premium">{{ (lab.is_premium ? 'Premium lab' : 'Free lab') | t }} · {{ lab.level | t }}</span>
        <h2>{{ lab.title }}</h2><h3>{{ 'Your mission' | t }}</h3><p class="body-copy">{{ lab.scenario }}</p>
        @if (lab.latest_result; as result) {
          <div class="lab-completion">
            <span class="pill success">{{ 'Lab completed' | t }}</span>
            <p>{{ 'Latest score' | t }}: {{ result.score }} / 100 · {{ (result.passed ? 'Passed' : 'Needs practice') | t }}</p>
            <a class="button-link compact" [routerLink]="['/results',result.id]">{{ 'View result & corrections →' | t }}</a>
            <p class="muted">{{ 'Retaking creates a new attempt. Previous results and corrections remain saved.' | t }}</p>
          </div>
          <details class="attempt-history"><summary>{{ 'Previous attempts' | t }} ({{ lab.attempt_count }})</summary>
            @for (previous of lab.results; track previous.id) {
              <div class="feedback"><p>{{ previous.completed_at | localDate }} · {{ previous.score }} / 100 · {{ (previous.passed ? 'Passed' : 'Needs practice') | t }}</p>
                <a class="secondary-link" [routerLink]="['/results',previous.id]">{{ 'View result & corrections →' | t }}</a>
              </div>
            }
          </details>
        }
        <h3>{{ 'Mission objectives' | t }}</h3><ul>@for (objective of lab.objectives; track objective) { <li>{{ objective }}</li> }</ul>
        <p class="muted">{{ lab.question_count }} {{ 'questions' | t }} · {{ lab.expected_seconds / 60 }} {{ 'minutes recommended' | t }}</p>
        @if (lab.locked) {
          <div class="info-panel">{{ 'Active Premium is required to start this lab.' | t }}</div>
          <a routerLink="/premium" class="button-link">{{ 'Get Premium →' | t }}</a>
        } @else {
          <p>{{ 'The timer starts when you begin. You can review your answers before submitting.' | t }}</p><ion-button [class.retake-button]="lab.completed" [disabled]="starting() || lab.question_count === 0" (click)="start()">@if (starting()) { <ion-spinner name="dots" /> } @else { {{ (lab.completed ? 'Retake simulation' : 'Begin simulation') | t }} } </ion-button>
        }
      </section>
    }
    @if (attempt(); as a) {
      <div class="quiz-toolbar"><div><strong>{{ (a.lab_title) | t }}</strong><small>{{ (a.career_title) | t }}</small></div><span class="pill">{{ (minutes()) | t }}:{{ (seconds()) | t }} {{ 'elapsed' | t }}</span></div>
      <ion-progress-bar [value]="(index() + 1) / a.questions.length" />
      <details class="panel mission-reminder"><summary>{{ 'Review mission briefing' | t }}</summary><p class="body-copy">{{ a.scenario }}</p><ul>@for (objective of a.objectives; track objective) { <li>{{ objective }}</li> }</ul></details>
      <nav class="question-navigation" [attr.aria-label]="'Review questions' | t">
        @for (question of a.questions; track question.id; let i = $index) {
          <button class="theme-button" [class.answered]="hasAnswer(question.id)" [attr.aria-current]="index() === i ? 'step' : null" [disabled]="saving()" (click)="index.set(i)">{{ i + 1 }} @if (hasAnswer(question.id)) { &#10003; }</button>
        }
      </nav>
      @if (a.questions[index()]; as q) {
        <section class="panel quiz-panel"><span class="eyebrow">{{ 'QUESTION' | t }} {{ (index() + 1) | t }} {{ 'OF' | t }} {{ (a.questions.length) | t }}</span><h2>{{ (q.prompt) | t }}</h2>
        @if (q.kind && q.kind !== 'quiz') {
          <app-workshop-workspace [question]="q" [selectedIds]="selections()[q.id] ?? []"
            [code]="codeAnswers()[q.id] ?? ''" [disabled]="saving()" (choose)="toggle(q,$event)"
            (codeChange)="setCode(q.id,$event)" (orderChange)="setOrder(q.id,$event)" />
        } @else {
        <p class="muted">{{ (q.multiple ? 'Select all correct answers.' : 'Select one answer.') | t }}</p><div class="answer-options">
          @for (option of q.options; track option.id; let i = $index) {
            <button class="answer-option" [class.selected]="selected(q.id, option.id)" [attr.aria-pressed]="selected(q.id, option.id)" [disabled]="saving()" (click)="toggle(q, option.id)"><span class="option-letter">{{ (optionLetter(i)) | t }}</span><span>{{ (option.text) | t }}</span><span class="option-check">{{ selected(q.id, option.id) ? '✓' : '' }}</span></button>
          }
        </div>
        }</section>
      }
      <div class="page-actions"><ion-button fill="outline" [disabled]="index() === 0 || saving()" (click)="index.set(index() - 1)">{{ 'Previous' | t }}</ion-button>
        @if (index() < a.questions.length - 1) { <ion-button [disabled]="!hasCurrentAnswer() || saving()" (click)="index.set(index() + 1)">{{ 'Next question →' | t }}</ion-button> }
        @else { <ion-button [disabled]="!allAnswered() || saving()" (click)="submit()">@if (saving()) { <ion-spinner name="dots" /> } @else { {{ 'Submit & see results' | t }} } </ion-button> }
      </div>
      <p class="muted">{{ answeredCount() }} / {{ a.questions.length }} {{ 'questions answered' | t }}</p>
      <p class="small muted">{{ 'Default scoring: 80% answer accuracy + 20% time score. A submitted attempt cannot be changed.' | t }}</p>
    }
  `,
})
export class LabPage implements OnInit, OnDestroy {
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  readonly attempt = signal<Attempt | null>(null);
  readonly detail = signal<LabDetail | null>(null);
  readonly index = signal(0);
  readonly elapsed = signal(0);
  readonly loading = signal(true);
  readonly starting = signal(false);
  readonly saving = signal(false);
  readonly error = signal('');
  readonly selections = signal<Partial<Record<number, number[]>>>({});
  readonly codeAnswers = signal<Partial<Record<number, string>>>({});
  optionLetter(index: number) { return index < 26 ? String.fromCharCode(65 + index) : String(index + 1); }
  private timer?: ReturnType<typeof setInterval>;
  private startTime = 0;
  ngOnInit() {
    window.addEventListener('beforeunload', this.beforeUnload);
    void this.load();
  }
  async load() {
    if (this.starting() || this.attempt()) return;
    this.loading.set(true); this.error.set('');
    try { this.detail.set(await this.api.lab(Number(this.route.snapshot.paramMap.get('id')))); }
    catch (error) { this.error.set(errorMessage(error)); }
    finally { this.loading.set(false); }
  }

  ngOnDestroy() {
    if (this.timer) clearInterval(this.timer);
    window.removeEventListener('beforeunload', this.beforeUnload);
  }
  private readonly beforeUnload = (event: BeforeUnloadEvent) => {
    if (this.attempt()) event.preventDefault();
  };
  minutes() { return Math.floor(this.elapsed() / 60).toString().padStart(2,'0'); }
  seconds() { return (this.elapsed() % 60).toString().padStart(2,'0'); }
  async start() {
    if (this.starting() || this.attempt() || this.loading() || this.detail()?.locked || !this.detail()) return;
    this.starting.set(true); this.error.set('');
    try {
      this.attempt.set(await this.api.startLab(Number(this.route.snapshot.paramMap.get('id'))));
      this.selections.set({}); this.codeAnswers.set({}); this.index.set(0); this.elapsed.set(0);
      this.startTime = Date.now();
      this.timer = setInterval(() => this.elapsed.set(Math.floor((Date.now() - this.startTime) / 1000)),1000);
    } catch (error) { this.error.set(errorMessage(error)); }
    finally { this.starting.set(false); }
  }
  selected(question: number, option: number) { return (this.selections()[question] ?? []).includes(option); }
  hasAnswer(question: number) {
    const task = this.attempt()?.questions.find(q => q.id === question);
    if (task?.kind === 'sequence') return (this.selections()[question]?.length ?? 0) === task.options.length;
    return task?.kind === 'code' ? !!this.codeAnswers()[question]?.trim() :
      (this.selections()[question]?.length ?? 0) > 0;
  }
  setCode(question: number, text: string) {
    this.codeAnswers.update(value => ({...value, [question]: text}));
  }
  setOrder(question: number, order: number[]) {
    if (this.saving()) return;
    this.selections.update(value => ({...value, [question]: order}));
  }
  answeredCount() { return this.attempt()?.questions.filter(q => this.hasAnswer(q.id)).length ?? 0; }
  toggle(question: Question, option: number) {
    if (this.saving()) return;
    const old = this.selections()[question.id] ?? [];
    const next = question.multiple ? old.includes(option) ? old.filter(id => id !== option) : [...old,option] : [option];
    this.selections.update(value => ({...value,[question.id]:next}));
  }
  hasCurrentAnswer() {
    const q = this.attempt()?.questions[this.index()];
    return !!q && this.hasAnswer(q.id);
  }
  allAnswered() { return this.attempt()?.questions.every(q => this.hasAnswer(q.id)) ?? false; }
  async submit() {
    const attempt = this.attempt();
    if (!attempt || this.saving() || !this.allAnswered()) return;
    this.saving.set(true); this.error.set('');
    try {
      const result = await this.api.submit(attempt.id, attempt.questions.map(q => ({
        question_id:q.id, option_ids:q.kind === 'code' ? [] : this.selections()[q.id] ?? [],
        ...(q.kind === 'code' ? {code_text: this.codeAnswers()[q.id] ?? ''} : {}),
      })));
      this.attempt.set(null);
      if (this.timer) clearInterval(this.timer);
      await this.router.navigate(['/results',result.id]);
    } catch (error) { this.error.set(errorMessage(error)); }
    finally { this.saving.set(false); }
  }
}

export const leaveLabGuard: CanDeactivateFn<LabPage> = component =>
  !component.attempt() || window.confirm(inject(LocaleService).t('Leave this unfinished simulation? Your answers will not be submitted.'));

@Component({
  standalone: true,
  imports: [TranslatePipe, IonicModule, RouterLink, KeyValuePipe, CareerAssessmentComponent],
  template: `
    @if (error()) { <div class="error" role="alert">{{ (error()) | t }} <button (click)="load()">{{ 'Retry' | t }}</button></div> }
    @if (loading()) { <div class="loading"><ion-spinner /> {{ 'Loading results...' | t }}</div> }
    @if (result(); as r) {
      <section class="result-hero"><span class="eyebrow">{{ 'EVERY ATTEMPT IS A STEP FORWARD' | t }}</span><div class="result-ring" [style.--score]="r.score + '%'"><strong>{{ (r.score) | t }}<small>/ 100</small></strong></div><h1>{{ (r.passed ? 'Great work. Keep growing!' : 'Keep practicing. You are learning!') | t }}</h1><p>{{ (r.career_title) | t }} · {{ (r.lab_title) | t }}</p></section>
      <div class="metrics"><article class="metric"><span>{{ 'Correct answers' | t }}</span><strong>{{ (r.correct) | t }} / {{ (r.total) | t }}</strong></article><article class="metric"><span>{{ 'Time taken' | t }}</span><strong>{{ (r.duration_seconds) | t }}<small> {{ 'seconds' | t }}</small></strong></article><article class="metric"><span>{{ 'Time score' | t }}</span><strong>{{ (r.time_score) | t }}%</strong></article></div>
      @if (assessment(); as summary) { <app-career-assessment [assessment]="summary" /> }
      <div class="page-actions">
        @if (r.lab_id !== null) { <a class="button-link retake-button" [routerLink]="['/labs',r.lab_id]">{{ 'Retake lab →' | t }}</a> }
        <button class="theme-button" [attr.aria-pressed]="errorsOnly()" (click)="errorsOnly.set(!errorsOnly())">{{ (errorsOnly() ? 'Show all answers' : 'Show mistakes only') | t }}</button>
      </div>
      <p class="muted">{{ 'Retaking creates a new attempt. Previous results and corrections remain saved.' | t }}</p>
      <div class="detail-grid"><section class="panel"><h2>{{ 'Your answer review' | t }}</h2>@for (feedback of r.feedback; track $index) {
        @if (!errorsOnly() || !feedback.correct) {
        <div class="feedback"><span class="pill" [class.success]="feedback.correct">{{ (feedback.correct ? 'Correct' : 'Incorrect answer') | t }}</span><h3>{{ feedback.prompt }}</h3>
          @if (feedback.selected_options) {
            <strong>{{ (feedback.kind === 'sequence' ? 'Your workflow' : 'Your selections') | t }}</strong>
            @if (feedback.kind === 'sequence') { <ol>@for (option of feedback.selected_options; track $index) { <li>{{ option }}</li> }</ol> }
            @else { <ul>@for (option of feedback.selected_options; track $index) { <li>{{ option }}</li> }</ul> }
          }
          @else { <p class="muted">{{ 'Selected answers were not stored for this older attempt.' | t }}</p> }
          @if (feedback.correct_options) {
            <strong>{{ (feedback.kind === 'sequence' ? 'Expected workflow' : 'Expected selections') | t }}</strong>
            @if (feedback.kind === 'sequence') { <ol>@for (option of feedback.correct_options; track $index) { <li>{{ option }}</li> }</ol> }
            @else { <ul>@for (option of feedback.correct_options; track $index) { <li>{{ option }}</li> }</ul> }
          }
          @if (feedback.kind === 'code' && feedback.workspace) {
            <h4>{{ 'Corrected code' | t }}</h4>
            <pre dir="ltr"><code>{{ feedback.workspace.before }}{{ feedback.correct_options?.[0] }}{{ feedback.workspace.after }}</code></pre>
          }
          @if (feedback.kind === 'architecture' && feedback.workspace?.nodes) {
            <h4>{{ 'Corrected architecture flow' | t }}</h4>
            <ol dir="ltr">@for (node of feedback.workspace?.nodes; track $index) {
              <li>{{ $index === feedback.workspace?.gap ? feedback.correct_options?.[0] : node }}</li>
            }</ol>
          }
          <p class="body-copy">{{ feedback.explanation }}</p>
        </div>
        }
      }
      @if (errorsOnly() && r.correct === r.total) { <p>{{ 'No mistakes in this attempt.' | t }}</p> }
      </section><aside class="panel"><h2>{{ 'Skills practiced' | t }}</h2>@for (skill of r.skills | keyvalue; track skill.key) { <div class="skill-row"><div><span>{{ (skill.key) | t }}</span><strong>{{ (skill.value) | t }}%</strong></div><ion-progress-bar [value]="skill.value / 100" /></div> }<div class="form-stack"><a class="button-link" [routerLink]="['/careers',r.career_slug]">{{ 'Continue this career →' | t }}</a><a routerLink="/recommendations" class="secondary-link">{{ 'View your updated matches' | t }}</a></div></aside></div>
    }
  `,
})
export class ResultPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);
  readonly result = signal<Result | null>(null);
  readonly assessment = signal<CareerAssessment | null>(null);
  readonly errorsOnly = signal(false);
  readonly loading = signal(true);
  readonly error = signal('');
  ngOnInit() { void this.load(); }
  async load() {
    this.loading.set(true); this.error.set('');
    this.assessment.set(null);
    try {
      const result = await this.api.result(Number(this.route.snapshot.paramMap.get('id')));
      this.result.set(result);
      this.assessment.set(await this.api.assessment(result.career_slug));
    }
    catch (error) { this.error.set(errorMessage(error)); }
    finally { this.loading.set(false); }
  }
}

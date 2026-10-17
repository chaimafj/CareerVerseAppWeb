import { TranslatePipe } from '../core/locale.service';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { IonicModule } from '@ionic/angular';
import { ApiService, errorMessage } from '../core/api.service';
import { Career } from '../core/models';
import { CareerAssessmentComponent } from '../widgets/career-assessment.component';
import { CareerArtComponent } from '../widgets/career-art.component';

@Component({
  standalone: true,
  imports: [TranslatePipe, FormsModule, RouterLink, IonicModule, CareerArtComponent],
  styleUrl: './careers.page.scss',
  template: `
    <div class="page-heading"><div><span class="eyebrow">{{ 'A WORLD OF POSSIBILITIES' | t }}</span><h1>{{ 'Find your direction.' | t }}</h1><p class="muted">{{ 'Go beyond job titles. Discover what the work really feels like.' | t }}</p></div><span class="pill">{{ (careers().length) | t }} {{ 'curated careers' | t }}</span></div>
    <div class="search-panel"><input [attr.aria-label]=" 'Search careers' | t " type="search" [placeholder]=" 'Search careers, skills or tools...' | t " [ngModel]="query()" (ngModelChange)="query.set($event)"><select [attr.aria-label]=" 'Filter category' | t " [ngModel]="category()" (ngModelChange)="category.set($event)"><option value="">{{ 'All categories' | t }}</option>@for (c of categories(); track c) { <option [value]="c">{{ (c) | t }}</option> }</select></div>
    @if (error()) { <div class="error" role="alert">{{ (error()) | t }} <button (click)="load()">{{ 'Retry' | t }}</button></div> }
    @if (loading()) { <div class="loading"><ion-spinner /> {{ 'Loading careers...' | t }}</div> }
    <div class="card-grid">
      @for (career of filtered(); track career.slug) {
        <a class="career-card" [routerLink]="['/careers',career.slug]">
          <div class="career-illustration"><app-career-art [subject]="career.slug" /></div>
          <div class="card-top"><span class="pill">{{ (career.category) | t }}</span></div>
          <h2>{{ (career.title) | t }}</h2><p class="muted">{{ (career.summary) | t }}</p><div class="tags">@for (tool of career.tools; track tool) { <span>{{ (tool) | t }}</span> }</div>
          <div class="card-bottom"><span>{{ (career.salary) | t }}</span><strong>{{ 'Explore →' | t }}</strong></div>
        </a>
      } @empty { @if (!loading() && !error()) { <div class="empty panel"><h3>{{ 'No careers match your search.' | t }}</h3><p>{{ 'Try another keyword or category.' | t }}</p></div> } }
    </div>
  `,
})
export class CareersPage implements OnInit {
  private readonly api = inject(ApiService);
  readonly careers = signal<Career[]>([]);
  readonly query = signal('');
  readonly category = signal('');
  readonly loading = signal(true);
  readonly error = signal('');
  readonly categories = computed(() => [...new Set(this.careers().map(c => c.category))]);
  readonly filtered = computed(() => {
    const query = this.query().trim().toLowerCase();
    return this.careers().filter(c => (!this.category() || c.category === this.category()) &&
      [c.title,c.summary,...c.tools,...c.interests].join(' ').toLowerCase().includes(query));
  });
  ngOnInit() { void this.load(); }
  async load() {
    this.loading.set(true); this.error.set('');
    try { this.careers.set(await this.api.careers()); }
    catch (error) { this.error.set(errorMessage(error)); }
    finally { this.loading.set(false); }
  }
}

@Component({
  standalone: true,
  imports: [TranslatePipe, RouterLink, IonicModule, CareerAssessmentComponent],
  template: `
    <a routerLink="/careers" class="back-link">{{ '← All careers' | t }}</a>
    @if (error()) { <div class="error" role="alert">{{ (error()) | t }} <button (click)="load()">{{ 'Retry' | t }}</button></div> }
    @if (loading()) { <div class="loading"><ion-spinner /> {{ 'Loading career...' | t }}</div> }
    @if (career(); as c) {
      <section class="detail-hero"><span class="pill">{{ (c.category) | t }}</span><h1>{{ (c.title) | t }}</h1><p>{{ (c.summary) | t }}</p><div class="tags">@for (tool of c.tools; track tool) { <span>{{ (tool) | t }}</span> }</div></section>
      @if (c.assessment; as assessment) { <app-career-assessment [assessment]="assessment" /> }
      <div class="detail-grid"><section class="panel"><span class="eyebrow">{{ 'THE BIG PICTURE' | t }}</span><h2>{{ 'What you will do' | t }}</h2><p class="body-copy">{{ (c.description) | t }}</p><h3>{{ 'Courses' | t }}</h3>
        @for (course of c.courses ?? []; track course.id) {
          <div class="learning-step"><div class="step-body"><h3>{{ course.title }}</h3>
            @if (course.completed) { <span class="pill success">{{ 'Course completed' | t }}</span> }
            <div class="step-actions">
              @if (course.locked) { <a class="button-link compact" routerLink="/premium">{{ 'Get Premium →' | t }}</a> }
              @else { <a class="secondary-link" [routerLink]="['/courses',course.id]">{{ (course.completed ? 'Review course' : 'Read course') | t }}</a> }
            </div>
          </div></div>
        }
        <h3>{{ 'Labs' | t }}</h3><p class="muted">{{ 'Choose a simulation independently from your courses.' | t }}</p>
        @for (lab of c.labs ?? []; track lab.id; let i = $index) {
          <div class="learning-step"><span class="step-number">{{ (i + 1) | t }}</span><div class="step-body">
            <span class="eyebrow">{{ lab.level | t }}</span><span class="pill" [class.premium-pill]="lab.is_premium">{{ (lab.is_premium ? 'Premium lab' : 'Free lab') | t }}</span>
            <h3>{{ lab.title }}</h3><p class="muted">{{ lab.scenario }}</p>
            @if (lab.latest_result; as result) {
              <span class="pill success">{{ 'Lab completed' | t }}</span>
              <p>{{ 'Latest score' | t }}: {{ result.score }} / 100 · {{ (result.passed ? 'Passed' : 'Needs practice') | t }} · {{ lab.attempt_count }} {{ 'submitted attempts' | t }}</p>
              <a class="secondary-link" [routerLink]="['/results',result.id]">{{ 'View result & corrections →' | t }}</a>
            }
            <p class="muted">{{ lab.question_count }} {{ 'questions' | t }} · {{ lab.expected_seconds / 60 }} {{ 'minutes recommended' | t }} @if (lab.best_score !== null) { {{ '· Best:' | t }} {{ lab.best_score }}% }</p>
            @if (lab.locked) { <p class="muted">{{ 'Active Premium is required to start this lab.' | t }}</p> }
            <div class="step-actions">
              <a class="secondary-link" [routerLink]="['/labs',lab.id]">{{ 'View mission →' | t }}</a>
              @if (lab.locked) { <a class="button-link compact" routerLink="/premium">{{ 'Get Premium →' | t }}</a> }
              @else { <a class="button-link compact" [class.retake-button]="lab.completed" [routerLink]="['/labs',lab.id]">{{ (lab.completed ? 'Retake lab →' : 'Start lab →') | t }}</a> }
            </div>
          </div></div>
        }
      </section><aside><section class="panel fact-panel"><h3>{{ 'Career snapshot' | t }}</h3><span class="eyebrow">{{ 'INDICATIVE SALARY' | t }}</span><p>{{ (c.salary) | t }}</p><span class="eyebrow">{{ 'EDUCATION' | t }}</span><p>{{ (c.education) | t }}</p><span class="eyebrow">{{ 'OUTLOOK' | t }}</span><p>{{ (c.outlook) | t }}</p><small class="muted">{{ 'Salary estimates are illustrative, not guaranteed or country-specific.' | t }}</small></section></aside></div>
    }
  `,
})
export class CareerPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);
  readonly career = signal<Career | null>(null);
  readonly loading = signal(true);
  readonly error = signal('');
  ngOnInit() { void this.load(); }
  async load() {
    this.loading.set(true); this.error.set('');
    try { this.career.set(await this.api.career(this.route.snapshot.paramMap.get('slug') ?? '')); }
    catch (error) { this.error.set(errorMessage(error)); }
    finally { this.loading.set(false); }
  }
}

import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { IonicModule } from '@ionic/angular';
import { ApiService, errorMessage } from '../core/api.service';
import { CareerAssessment, CourseSummary, LabSummary } from '../core/models';
import { TranslatePipe } from '../core/locale.service';
import { CareerAssessmentComponent } from '../widgets/career-assessment.component';
import { AppIconComponent } from '../widgets/app-icon.component';

function groupByCareer<T extends {career_slug: string; career_title: string}>(items: T[]) {
  const groups = new Map<string, {slug: string; title: string; items: T[]}>();
  for (const item of items) {
    let group = groups.get(item.career_slug);
    if (!group) {
      group = {slug: item.career_slug, title: item.career_title, items: []};
      groups.set(item.career_slug, group);
    }
    group.items.push(item);
  }
  return [...groups.values()];
}

@Component({
  standalone: true,
  imports: [TranslatePipe, RouterLink, IonicModule, CareerAssessmentComponent, AppIconComponent],
  template: `
    <div class="page-heading"><div>
      <h1>{{ (isCourses ? 'Courses' : 'Labs') | t }}</h1>
      <p class="muted">{{ (isCourses ? 'Learn at your own pace. Completing a course does not start a lab.' : 'Explore each career and its labs, from foundations to advanced missions.') | t }}</p>
    </div></div>
    @if (error()) { <div class="error" role="alert">{{ error() | t }} <button (click)="load()">{{ 'Retry' | t }}</button></div> }
    @if (loading()) { <div class="loading"><ion-spinner /> {{ 'Loading...' | t }}</div> }
      @if (isCourses) {
        @for (career of courseGroups(); track career.slug) {
          <section class="career-lab-group" [attr.aria-labelledby]="'career-courses-' + career.slug">
            <div class="page-heading">
              <div><span class="eyebrow">{{ 'Career courses' | t }}</span><h2 [id]="'career-courses-' + career.slug">{{ career.title }}</h2></div>
              <a class="secondary-link" [routerLink]="['/careers',career.slug]">{{ 'Explore →' | t }}</a>
            </div>
            <div class="card-grid">
        @for (course of career.items; track course.id) {
          <article class="panel learning-card">
            <span class="learning-icon"><app-icon [name]="course.is_premium ? 'crown' : 'book'" /></span>
            <h3>{{ course.title }}</h3>
            <span class="pill" [class.premium-pill]="course.is_premium">{{ (course.is_premium ? 'Premium' : 'Free course') | t }}</span>
            @if (course.completed) { <p class="pill success">{{ 'Course completed' | t }}</p> }
            <div class="step-actions">
              @if (course.locked) { <a class="button-link" routerLink="/premium">{{ 'Get Premium →' | t }}</a> }
              @else { <a class="button-link" [routerLink]="['/courses',course.id]">{{ (course.completed ? 'Review course' : 'Read course') | t }}</a> }
            </div>
          </article>
        }
            </div>
          </section>
        } @empty { @if (!loading() && !error()) { <p>{{ 'No courses available.' | t }}</p> } }
      } @else {
        @for (career of labGroups(); track career.slug) {
          <section class="career-lab-group" [attr.aria-labelledby]="'career-labs-' + career.slug">
            <div class="page-heading">
              <div><span class="eyebrow">{{ 'Career labs' | t }}</span><h2 [id]="'career-labs-' + career.slug">{{ career.title }}</h2></div>
              <a class="secondary-link" [routerLink]="['/careers',career.slug]">{{ 'Explore →' | t }}</a>
            </div>
            @if (assessmentFor(career.slug); as assessment) { <app-career-assessment [assessment]="assessment" /> }
            <div class="card-grid">
        @for (lab of career.items; track lab.id) {
          <article class="panel learning-card" [class.premium-learning-card]="lab.is_premium">
            <span class="learning-icon"><app-icon [name]="lab.is_premium ? 'crown' : 'lab'" /></span>
            <span class="eyebrow">{{ lab.level | t }}</span><h3>{{ lab.title }}</h3>
            <span class="pill" [class.premium-pill]="lab.is_premium">{{ (lab.is_premium ? 'Premium lab' : 'Free lab') | t }}</span>
            <p class="muted">{{ lab.scenario }}</p>
            <p>{{ lab.question_count }} {{ 'questions' | t }} · {{ lab.expected_seconds / 60 }} {{ 'minutes recommended' | t }}</p>
            @if (lab.latest_result; as result) {
              <span class="pill success">{{ 'Lab completed' | t }}</span>
              <p>{{ 'Latest score' | t }}: {{ result.score }} / 100 · {{ (result.passed ? 'Passed' : 'Needs practice') | t }}</p>
              <a class="secondary-link" [routerLink]="['/results',result.id]">{{ 'View result & corrections →' | t }}</a>
            }
            <div class="step-actions">
              <a class="secondary-link" [routerLink]="['/labs',lab.id]">{{ 'View mission →' | t }}</a>
              @if (lab.locked) { <a class="button-link" routerLink="/premium">{{ 'Get Premium →' | t }}</a> }
              @else { <a class="button-link" [class.retake-button]="lab.completed" [routerLink]="['/labs',lab.id]">{{ (lab.completed ? 'Retake lab →' : 'Start lab →') | t }}</a> }
            </div>
          </article>
        }
            </div>
          </section>
        } @empty { @if (!loading() && !error()) { <p>{{ 'No labs available.' | t }}</p> } }
      }
  `,
})
export class LearningCatalogPage implements OnInit {
  private readonly api = inject(ApiService);
  readonly isCourses = inject(ActivatedRoute).snapshot.data['catalog'] === 'courses';
  readonly courses = signal<CourseSummary[]>([]);
  readonly labs = signal<LabSummary[]>([]);
  readonly assessments = signal<CareerAssessment[]>([]);
  assessmentFor(slug: string) { return this.assessments().find(item => item.career_slug === slug); }
  readonly courseGroups = computed(() => groupByCareer(this.courses()));
  readonly labGroups = computed(() => groupByCareer(this.labs()));
  readonly loading = signal(true);
  readonly error = signal('');
  ngOnInit() { void this.load(); }
  async load() {
    this.loading.set(true); this.error.set('');
    try {
      if (this.isCourses) this.courses.set(await this.api.courses());
      else {
        const [labs, assessments] = await Promise.all([this.api.labs(), this.api.assessments()]);
        this.labs.set(labs); this.assessments.set(assessments);
      }
    } catch (error) { this.error.set(errorMessage(error)); }
    finally { this.loading.set(false); }
  }
}

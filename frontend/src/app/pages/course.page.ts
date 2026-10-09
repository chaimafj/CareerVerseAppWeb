import { TranslatePipe } from '../core/locale.service';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { IonicModule } from '@ionic/angular';
import { ApiService, errorMessage } from '../core/api.service';
import { Course } from '../core/models';

@Component({
  standalone: true,
  imports: [TranslatePipe, RouterLink, IonicModule],
  template: `
    @if (error()) { <div class="error" role="alert">{{ (error()) | t }} <button (click)="load()">{{ 'Retry' | t }}</button></div> }
    @if (error() === premiumError) { <a class="button-link" routerLink="/premium">{{ 'Get Premium →' | t }}</a> }
    @if (loading()) { <div class="loading"><ion-spinner /> {{ 'Loading course...' | t }}</div> }
    @if (course(); as c) {
      <a routerLink="/courses" class="back-link">{{ '← All courses' | t }}</a>
      <div class="page-heading"><div><span class="eyebrow">{{ 'LEARN BEFORE YOU LEAP' | t }}</span><h1>{{ (c.title) | t }}</h1><p class="muted">{{ (c.intro) | t }}</p></div><span class="pill">{{ (page() + 1) | t }} / {{ (c.lessons.length) | t }}</span></div>
      <ion-progress-bar [value]="(page() + 1) / c.lessons.length" />
      @if (c.lessons[page()]; as lesson) {
        <article class="panel lesson-panel"><span class="eyebrow">{{ 'LESSON' | t }} {{ (page() + 1) | t }}</span><h2>{{ (lesson.title) | t }}</h2><p class="body-copy">{{ (lesson.body) | t }}</p>@if (lesson.example) { <h3>{{ 'In practice' | t }}</h3><pre><code>{{ (lesson.example) | t }}</code></pre> }</article>
      }
      <div class="page-actions"><ion-button fill="outline" [disabled]="page() === 0 || saving()" (click)="page.set(page() - 1)">{{ 'Previous' | t }}</ion-button>
        @if (page() < c.lessons.length - 1) { <ion-button (click)="page.set(page() + 1)">{{ 'Next lesson →' | t }}</ion-button> }
        @else { <ion-button [disabled]="saving() || c.completed" (click)="finish()">@if (saving()) { <ion-spinner name="dots" /> } @else { {{ (c.completed ? 'Course completed' : 'Finish course') | t }} } </ion-button> }
      </div>
      @if (c.completed) {
        <div class="lab-completion" role="status"><span class="pill success">{{ 'Course completed' | t }}</span><p>{{ 'Your course progress is saved. Choose a lab separately whenever you are ready.' | t }}</p></div>
      }
      <div class="step-actions"><a routerLink="/courses" class="secondary-link">{{ '← All courses' | t }}</a><a routerLink="/labs" class="secondary-link">{{ 'Browse labs →' | t }}</a></div>
    }
  `,
})
export class CoursePage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);
  readonly course = signal<Course | null>(null);
  readonly page = signal(0);
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly error = signal('');
  readonly premiumError = 'Active Premium access is required for this lab and its course.';
  ngOnInit() { void this.load(); }
  async load() {
    this.loading.set(true); this.error.set('');
    try { this.course.set(await this.api.course(Number(this.route.snapshot.paramMap.get('id')))); }
    catch (error) { this.error.set(errorMessage(error)); }
    finally { this.loading.set(false); }
  }
  async finish() {
    const course = this.course();
    if (!course || course.completed || this.saving()) return;
    this.saving.set(true); this.error.set('');
    try {
      await this.api.completeCourse(course.id);
      this.course.set({...course, completed: true});
    } catch (error) { this.error.set(errorMessage(error)); }
    finally { this.saving.set(false); }
  }
}

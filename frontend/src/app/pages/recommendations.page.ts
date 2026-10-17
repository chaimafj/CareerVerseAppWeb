import { TranslatePipe } from '../core/locale.service';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { IonicModule } from '@ionic/angular';
import { ApiService, errorMessage } from '../core/api.service';
import { Match } from '../core/models';
import { OverviewArtComponent } from '../widgets/overview-art.component';
import { AppIconComponent } from '../widgets/app-icon.component';

@Component({
  standalone: true,
  imports: [TranslatePipe, RouterLink, IonicModule, OverviewArtComponent, AppIconComponent],
  styleUrl: './recommendations.page.scss',
  template: `
    <header class="matches-hero">
      <div class="hero-copy"><span class="hero-label"><app-icon name="sparkles" />{{ 'DISCOVER WHERE YOU SHINE' | t }}</span><h1>{{ 'Your possibilities, ranked.' | t }}</h1><p>{{ 'Your interests and lab results help reveal paths worth exploring.' | t }}</p><a routerLink="/profile" class="hero-action"><app-icon name="user" />{{ 'Update interests' | t }}<span aria-hidden="true">&#8594;</span></a></div>
      <div class="hero-visual" aria-hidden="true"><app-overview-art subject="ai-engineering" /></div>
    </header>
    @if (!loading() && !error() && matches().length) {
      <section class="match-summary" [attr.aria-label]="'Your matches at a glance' | t">
        <div><app-icon name="compass" /><strong>{{ matches().length }}</strong><span>{{ 'Career paths to explore' | t }}</span></div>
        <div><app-icon name="lab" /><strong>{{ testedCount }}</strong><span>{{ 'Careers tried in labs' | t }}</span></div>
        <div><app-icon name="sparkles" /><strong>{{ matches()[0].score }}%</strong><span>{{ 'Highest match score' | t }}</span></div>
      </section>
    }
    <details class="score-guide"><summary><app-icon name="shield" />{{ 'Understanding your matches' | t }}</summary><p>{{ 'These are explainable orientation scores, not predictions of career success. Tested careers use 75% lab performance and 25% interest fit. Untested careers use 60% of interest fit.' | t }}</p></details>
    @if (error()) { <div class="error" role="alert">{{ (error()) | t }} <button (click)="load()">{{ 'Retry' | t }}</button></div> }
    @if (loading()) { <div class="loading"><ion-spinner /> {{ 'Finding your matches...' | t }}</div> }
    <div class="matches-list">@for (match of matches(); track match.career_slug; let i = $index) {
      <article class="panel match-card" [class.top-match]="i === 0" [style.animation-delay.ms]="i * 55">
        <div class="match-art"><app-overview-art [subject]="match.career_slug" /><span class="rank"><span class="sr-only">{{ 'Rank' | t }}</span>{{ i + 1 }}</span><span class="match-status"><app-icon [name]="match.tested ? 'lab' : 'compass'" />{{ (match.tested ? 'Tested in labs' : 'Ready to explore') | t }}</span></div>
        <div class="match-body"><span class="eyebrow">{{ (i === 0 ? 'YOUR TOP MATCH' : 'ANOTHER PATH TO EXPLORE') | t }}</span><h2>{{ (match.career_title) | t }}</h2>
          <div class="score-heading"><strong>{{ match.score }}<small>%</small></strong><span>{{ 'match score' | t }}</span></div>
          <div class="score-track" role="progressbar" [attr.aria-label]="(match.career_title | t) + ' · ' + ('match score' | t)" [attr.aria-valuenow]="match.score" aria-valuemin="0" aria-valuemax="100"><span [style.width.%]="match.score"></span></div>
          <p class="match-evidence">@if (match.tested) { <app-icon name="lab" /> {{ 'Best-lab performance:' | t }} {{ match.performance }}%. } @else { {{ 'Not tested yet. Try a lab to refine this match.' | t }} }</p>
          <div class="tags">@for (interest of match.shared_interests; track interest) { <span>{{ (interest) | t }}</span> } @empty { <span>{{ 'No shared interests selected yet' | t }}</span> }</div>
          <a [routerLink]="['/careers',match.career_slug]" class="match-link">{{ 'Explore this career →' | t }}</a>
        </div>
      </article>
    } @empty { @if (!loading() && !error()) { <section class="panel empty">{{ 'No published careers are available yet.' | t }}</section> } }</div>
  `,
})
export class RecommendationsPage implements OnInit {
  private readonly api = inject(ApiService);
  readonly matches = signal<Match[]>([]);
  readonly loading = signal(true);
  readonly error = signal('');
  get testedCount() { return this.matches().filter(match => match.tested).length; }
  ngOnInit() { void this.load(); }
  async load() {
    this.loading.set(true); this.error.set('');
    try { this.matches.set(await this.api.recommendations()); }
    catch (error) { this.error.set(errorMessage(error)); }
    finally { this.loading.set(false); }
  }
}

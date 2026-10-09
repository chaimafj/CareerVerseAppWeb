import { TranslatePipe } from '../core/locale.service';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { IonicModule } from '@ionic/angular';
import { ApiService, errorMessage } from '../core/api.service';
import { Match } from '../core/models';

@Component({
  standalone: true,
  imports: [TranslatePipe, RouterLink, IonicModule],
  template: `
    <div class="page-heading"><div><span class="eyebrow">{{ 'DISCOVER WHERE YOU SHINE' | t }}</span><h1>{{ 'Your possibilities, ranked.' | t }}</h1><p class="muted">{{ 'Your interests and lab results help reveal paths worth exploring.' | t }}</p></div><a routerLink="/profile" class="secondary-link">{{ 'Update interests' | t }}</a></div>
    <div class="info-panel">{{ 'These are explainable orientation scores, not predictions of career success. Tested careers use 75% lab performance and 25% interest fit. Untested careers use 60% of interest fit.' | t }}</div>
    @if (error()) { <div class="error" role="alert">{{ (error()) | t }} <button (click)="load()">{{ 'Retry' | t }}</button></div> }
    @if (loading()) { <div class="loading"><ion-spinner /> {{ 'Finding your matches...' | t }}</div> }
    <div class="matches-list">@for (match of matches(); track match.career_slug; let i = $index) {
      <article class="panel match-card"><span class="rank">{{ (i + 1) | t }}</span><div class="match-body"><span class="eyebrow">{{ (i === 0 ? 'YOUR TOP MATCH' : 'ANOTHER PATH TO EXPLORE') | t }}</span><h2>{{ (match.career_title) | t }}</h2><p class="muted">@if (match.tested) { {{ 'Best-lab performance:' | t }} {{ match.performance }}%. } @else { {{ 'Not tested yet. Try a lab to refine this match.' | t }} }</p><div class="tags">@for (interest of match.shared_interests; track interest) { <span>{{ (interest) | t }}</span> } @empty { <span>{{ 'No shared interests selected yet' | t }}</span> }</div><a [routerLink]="['/careers',match.career_slug]" class="secondary-link">{{ 'Explore this career →' | t }}</a></div><div class="match-score"><strong>{{ (match.score) | t }}%</strong><small>{{ 'match score' | t }}</small><ion-progress-bar [value]="match.score / 100" /></div></article>
    } @empty { @if (!loading() && !error()) { <section class="panel empty">{{ 'No published careers are available yet.' | t }}</section> } }</div>
  `,
})
export class RecommendationsPage implements OnInit {
  private readonly api = inject(ApiService);
  readonly matches = signal<Match[]>([]);
  readonly loading = signal(true);
  readonly error = signal('');
  ngOnInit() { void this.load(); }
  async load() {
    this.loading.set(true); this.error.set('');
    try { this.matches.set(await this.api.recommendations()); }
    catch (error) { this.error.set(errorMessage(error)); }
    finally { this.loading.set(false); }
  }
}

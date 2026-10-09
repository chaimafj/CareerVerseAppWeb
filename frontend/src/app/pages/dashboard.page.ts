import { LocalDatePipe, TranslatePipe } from '../core/locale.service';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { IonicModule } from '@ionic/angular';
import { ApiService, errorMessage } from '../core/api.service';
import { AuthService } from '../core/auth.service';
import { Match, Progress } from '../core/models';
import { CareerArtComponent } from '../widgets/career-art.component';
import { AppIconComponent } from '../widgets/app-icon.component';

@Component({
  standalone: true,
  imports: [TranslatePipe, IonicModule, RouterLink, LocalDatePipe, CareerArtComponent, AppIconComponent],
  template: `
    <div class="page-heading"><div><span class="eyebrow">{{ 'MAKE YOUR NEXT MOVE' | t }}</span><h1>{{ 'Hello,' | t }} {{ auth.user()?.name }}.</h1><p class="muted">{{ 'A little curiosity today. A clearer direction tomorrow.' | t }}</p></div><a routerLink="/careers" class="button-link">{{ 'Explore careers →' | t }}</a></div>
    @if (error()) { <div class="error" role="alert">{{ (error()) | t }} <button (click)="load()">{{ 'Retry' | t }}</button></div> }
    @if (loading()) { <div class="loading"><ion-spinner /><span>{{ 'Loading your journey...' | t }}</span></div> }
    @if (progress(); as p) {
      <section class="hero-panel">
        <div><span class="eyebrow">{{ 'BUILD A FUTURE THAT FITS' | t }}</span><h2>{{ 'Your potential.' | t }}<br>{{ 'Your possibilities.' | t }}</h2><p>{{ 'Try a real-world scenario and uncover the skills you love using.' | t }}</p><a routerLink="/careers" class="button-link light">{{ 'Find your next challenge →' | t }}</a></div>
        <div class="hero-art"><app-career-art [animated]="true" /></div>
      </section>
      <div class="metrics">
        <article class="metric"><app-icon name="lab" /><span>{{ 'Labs completed' | t }}</span><strong>{{ (p.completed_labs) | t }} <small>/ {{ (p.total_labs) | t }}</small></strong><ion-progress-bar [value]="p.total_labs ? p.completed_labs / p.total_labs : 0" /></article>
        <article class="metric"><app-icon name="sparkles" /><span>{{ 'Best-attempt average' | t }}</span><strong>{{ (p.completed_labs === 0 || p.average_score === null ? '--' : p.average_score + '%') | t }}</strong><small>{{ 'Your progress, not your limits.' | t }}</small></article>
        <article class="metric"><app-icon name="book" /><span>{{ 'Courses completed' | t }}</span><strong>{{ (p.completed_courses) | t }}</strong><small>{{ 'Knowledge put into practice.' | t }}</small></article>
      </div>
      <div class="section-heading"><h2>{{ 'Your career matches' | t }}</h2><a routerLink="/recommendations">{{ 'See all →' | t }}</a></div>
      <div class="card-grid">
        @for (match of matches().slice(0,3); track match.career_slug) {
          <a class="career-card" [routerLink]="['/careers',match.career_slug]"><span class="pill">{{ (match.tested ? 'Based on your results' : 'Explore this possibility') | t }}</span><h3>{{ (match.career_title) | t }}</h3><div class="match-line"><strong>{{ (match.score) | t }}%</strong><span>{{ 'career match' | t }}</span></div><ion-progress-bar [value]="match.score / 100" /><p class="muted">{{ (match.shared_interests.join(' / ') || 'Complete your profile to improve your matches.') | t }}</p></a>
        }
      </div>
      <div class="section-heading"><h2>{{ 'Recent activity' | t }}</h2><span class="muted">{{ 'Your learning history' | t }}</span></div>
      <section class="panel">
        @for (result of p.results.slice(0,8); track result.id) {
          <a class="activity-row" [routerLink]="['/results',result.id]"><div><strong>{{ (result.lab_title) | t }}</strong><small>{{ (result.career_title) | t }} · {{ result.completed_at | localDate:'mediumDate' }}</small></div><span class="score-pill">{{ (result.score) | t }}%</span></a>
        } @empty { <div class="empty"><h3>{{ 'Your first chapter is waiting.' | t }}</h3><p>{{ 'Finish a lab to see your results here.' | t }}</p><a routerLink="/careers">{{ 'Choose a career →' | t }}</a></div> }
      </section>
    }
  `,
})
export class DashboardPage implements OnInit {
  private readonly api = inject(ApiService);
  readonly auth = inject(AuthService);
  readonly progress = signal<Progress | null>(null);
  readonly matches = signal<Match[]>([]);
  readonly loading = signal(true);
  readonly error = signal('');
  ngOnInit() { void this.load(); }
  async load() {
    this.loading.set(true); this.error.set('');
    try {
      const [progress, matches] = await Promise.all([this.api.progress(), this.api.recommendations()]);
      this.progress.set(progress); this.matches.set(matches);
    } catch (error) { this.error.set(errorMessage(error)); }
    finally { this.loading.set(false); }
  }
}

import { LocalDatePipe, TranslatePipe } from '../core/locale.service';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { IonicModule } from '@ionic/angular';
import { ApiService, errorMessage } from '../core/api.service';
import { AuthService } from '../core/auth.service';
import { Match, Progress } from '../core/models';
import { OverviewArtComponent } from '../widgets/overview-art.component';
import { AppIconComponent } from '../widgets/app-icon.component';
import { CareerCarouselComponent } from '../widgets/career-carousel.component';

@Component({
  standalone: true,
  imports: [TranslatePipe, IonicModule, RouterLink, LocalDatePipe, OverviewArtComponent, AppIconComponent, CareerCarouselComponent],
  styleUrl: './dashboard.page.scss',
  template: `
    <div class="overview-page">
    <div class="page-heading overview-heading"><div><span class="eyebrow">{{ 'YOUR PERSONAL LAUNCHPAD' | t }}</span><h1>{{ 'Hello,' | t }} <span class="greeting-name">{{ auth.user()?.name }}.</span><span class="greeting-spark" aria-hidden="true">&#10022;</span></h1><p class="muted">{{ 'A little curiosity today. A clearer direction tomorrow.' | t }}</p></div><a routerLink="/profile" class="overview-profile"><app-icon name="user" />{{ 'My learning profile' | t }}<span aria-hidden="true">&#8599;</span></a></div>
    @if (error()) { <div class="error" role="alert">{{ (error()) | t }} <button (click)="load()">{{ 'Retry' | t }}</button></div> }
    @if (loading()) { <div class="loading"><ion-spinner /><span>{{ 'Loading your journey...' | t }}</span></div> }
    @if (progress(); as p) {
      <section class="overview-banner">
        <div class="banner-orbit" aria-hidden="true"></div>
        <div class="overview-banner-copy">
          <span class="banner-label"><span aria-hidden="true"></span>{{ 'A NEW POSSIBILITY STARTS HERE' | t }}</span>
          <h2>{{ 'Small steps.' | t }}<br><span>{{ 'Extraordinary futures.' | t }}</span></h2>
          <p>{{ 'Discover your strengths in a world of possibilities. Learn, experiment, and build a career that feels like you.' | t }}</p>
          <div class="banner-actions"><a routerLink="/careers" class="button-link light">{{ 'Explore my future' | t }} <span aria-hidden="true">&#8594;</span></a><a routerLink="/labs" class="banner-secondary">{{ 'Try a lab' | t }} <span aria-hidden="true">&#8599;</span></a></div>
          <div class="banner-journey"><span class="journey-symbols" aria-hidden="true"><app-icon name="book" /><app-icon name="lab" /><app-icon name="compass" /></span><span>{{ 'Learn. Try. Find your way.' | t }}</span></div>
        </div>
        <app-career-carousel [studio]="true" />
      </section>
      <div class="overview-metrics">
        <article class="overview-stat"><span class="stat-icon"><app-icon name="lab" /></span><div><span>{{ 'Labs completed' | t }}</span><strong>{{ p.completed_labs }}<small> / {{ p.total_labs }}</small></strong><ion-progress-bar [value]="p.total_labs ? p.completed_labs / p.total_labs : 0" /></div><span class="stat-decoration" aria-hidden="true">01</span></article>
        <article class="overview-stat"><span class="stat-icon"><app-icon name="sparkles" /></span><div><span>{{ 'Best-attempt average' | t }}</span><strong>{{ (p.completed_labs === 0 || p.average_score === null ? '--' : p.average_score + '%') | t }}</strong><small>{{ 'Your progress, not your limits.' | t }}</small></div><span class="stat-decoration" aria-hidden="true">02</span></article>
        <article class="overview-stat"><span class="stat-icon"><app-icon name="book" /></span><div><span>{{ 'Courses completed' | t }}</span><strong>{{ p.completed_courses }}</strong><small>{{ 'Knowledge put into practice.' | t }}</small></div><span class="stat-decoration" aria-hidden="true">03</span></article>
      </div>
      <div class="section-heading"><div><span class="eyebrow">{{ 'MAKE IT HAPPEN' | t }}</span><h2>{{ 'What will you explore today?' | t }}</h2></div></div>
      <nav class="overview-shortcuts" [attr.aria-label]="'Your next step' | t">
        <a routerLink="/courses"><span class="shortcut-icon"><app-icon name="book" /></span><span><strong>{{ 'Keep learning' | t }}</strong><small>{{ 'Practical courses' | t }}</small></span><span class="shortcut-arrow" aria-hidden="true">&#8599;</span></a>
        <a routerLink="/labs"><span class="shortcut-icon"><app-icon name="lab" /></span><span><strong>{{ 'Take a challenge' | t }}</strong><small>{{ 'Career simulations' | t }}</small></span><span class="shortcut-arrow" aria-hidden="true">&#8599;</span></a>
        <a routerLink="/recommendations"><span class="shortcut-icon"><app-icon name="compass" /></span><span><strong>{{ 'Find your direction' | t }}</strong><small>{{ 'Personalized matches' | t }}</small></span><span class="shortcut-arrow" aria-hidden="true">&#8599;</span></a>
      </nav>
      <div class="section-heading"><div><span class="eyebrow">{{ 'CURATED FOR YOU' | t }}</span><h2>{{ 'Your career matches' | t }}</h2></div><a routerLink="/recommendations">{{ 'See all →' | t }}</a></div>
      <div class="card-grid overview-matches">
        @for (match of matches().slice(0,3); track match.career_slug) {
          <a class="career-card overview-match" [routerLink]="['/careers',match.career_slug]"><div class="overview-match-art"><app-overview-art [subject]="match.career_slug" /><span class="match-open" aria-hidden="true">&#8599;</span></div><div class="overview-match-body"><span class="pill">{{ (match.tested ? 'Based on your results' : 'Explore this possibility') | t }}</span><h3>{{ (match.career_title) | t }}</h3><div class="match-line"><strong>{{ (match.score) | t }}%</strong><span>{{ 'career match' | t }}</span></div><ion-progress-bar [value]="match.score / 100" /><p class="muted">{{ (match.shared_interests.join(' / ') || 'Complete your profile to improve your matches.') | t }}</p></div></a>
        } @empty {
          <section class="panel empty"><app-icon name="compass" /><h3>{{ 'Your first chapter is waiting.' | t }}</h3><p>{{ 'Complete your profile to improve your matches.' | t }}</p><a routerLink="/profile">{{ 'My profile' | t }} &#8594;</a></section>
        }
      </div>
      <div class="section-heading"><h2>{{ 'Recent activity' | t }}</h2><span class="muted">{{ 'Your learning history' | t }}</span></div>
      <section class="panel overview-activity">
        @for (result of p.results.slice(0,8); track result.id) {
          <a class="activity-row" [routerLink]="['/results',result.id]"><span class="activity-marker"><app-icon name="lab" /></span><div class="activity-description"><strong>{{ (result.lab_title) | t }}</strong><small>{{ (result.career_title) | t }} · {{ result.completed_at | localDate:'mediumDate' }}</small></div><span class="score-pill">{{ (result.score) | t }}%</span><span class="activity-arrow" aria-hidden="true">&#8599;</span></a>
        } @empty { <div class="empty overview-empty"><span class="empty-orbit" aria-hidden="true"><app-icon name="compass" /></span><div><h3>{{ 'Your first chapter is waiting.' | t }}</h3><p>{{ 'Finish a lab to see your results here.' | t }}</p></div><a routerLink="/careers" class="button-link">{{ 'Choose a career →' | t }}</a></div> }
      </section>
    }
    </div>
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

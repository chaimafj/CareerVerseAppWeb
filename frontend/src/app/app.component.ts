import { LocaleService, TranslatePipe } from './core/locale.service';
import { Component, effect, inject, signal } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { IonicModule } from '@ionic/angular';
import { AuthService } from './core/auth.service';
import { errorMessage } from './core/api.service';
import { ChatPage } from './pages/chat.page';
import { PushService } from './core/push.service';
import { AppIconComponent } from './widgets/app-icon.component';
import { NotificationCountService } from './core/notification-count.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [TranslatePipe, IonicModule, RouterLink, RouterLinkActive, RouterOutlet, ChatPage, AppIconComponent],
  template: `
    <ion-app>
      <div class="app-frame">
        <header class="topbar">
          <a routerLink="/" class="brand" [attr.aria-label]=" 'CareerVerse home' | t ">
            <span class="brand-mark" aria-hidden="true">&#8734;</span>
            <span>{{ 'Career' | t }}<span class="brand-blue">{{ 'Verse' | t }}</span><small>{{ 'LEARN. EXPERIENCE. DISCOVER.' | t }}</small></span>
          </a>
          <div class="top-actions">
            <select class="language-select" [attr.aria-label]="'Language' | t" [value]="locale.language()" (change)="changeLanguage($event)">
              <option value="en">English</option><option value="fr">Français</option><option value="ar">العربية</option>
            </select>
            <button class="theme-button" (click)="toggleTheme()" [attr.aria-label]="(dark() ? 'Use light theme' : 'Use dark theme') | t">
              <app-icon [name]="dark() ? 'sun' : 'moon'" />
              {{ (dark() ? 'Light theme' : 'Dark theme') | t }}
            </button>
            @if (auth.user(); as user) {
              <a routerLink="/notifications" class="notification-bell" [attr.aria-label]="('Notifications' | t) + ' · ' + (notificationCount.error() ? ('Notification count unavailable' | t) : notificationCount.unread() + ' ' + ('Unread notifications' | t))" [attr.title]="(notificationCount.error() ? 'Notification count unavailable' : 'Notifications') | t">
                <app-icon name="bell" />
                @if (notificationCount.error()) { <span class="notification-badge" aria-hidden="true">!</span> }
                @else if (notificationCount.unread() > 0) { <span class="notification-badge" aria-hidden="true">{{ notificationCount.unread() }}</span> }
              </a>
              <a routerLink="/profile" class="avatar" [attr.aria-label]="('My profile' | t) + ' · ' + user.name">@if (user.photo_url) { <img [src]="user.photo_url" alt=""> } @else { {{ user.name.slice(0, 1).toUpperCase() }} }</a>
            }
          </div>
        </header>
        @if (auth.user()) {
          <nav class="sidebar" [attr.aria-label]=" 'Main navigation' | t ">
            <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{exact:true}"><app-icon name="home" /> {{ 'Overview' | t }}</a>
            <a routerLink="/careers" routerLinkActive="active"><app-icon name="compass" /> {{ 'Explore careers' | t }}</a>
            <a routerLink="/courses" routerLinkActive="active"><app-icon name="book" /> {{ 'Courses' | t }}</a>
            <a routerLink="/labs" routerLinkActive="active"><app-icon name="lab" /> {{ 'Labs' | t }}</a>
            <a routerLink="/recommendations" routerLinkActive="active"><app-icon name="sparkles" /> {{ 'Your matches' | t }}</a>
            <a routerLink="/profile" routerLinkActive="active"><app-icon name="user" /> {{ 'My profile' | t }}</a>
            <a routerLink="/notifications" routerLinkActive="active"><app-icon name="bell" />{{ 'Notifications' | t }}@if (!notificationCount.error() && notificationCount.unread() > 0) { <span class="nav-notification-count">{{ notificationCount.unread() }}</span> }</a>
            <a routerLink="/premium" routerLinkActive="active"><app-icon name="crown" />{{ 'Premium' | t }}</a>
            @if (auth.user()?.is_staff) {
              <a href="/admin/" target="_blank" rel="noopener"><app-icon name="shield" /> {{ 'Administration' | t }}</a>
            }
            <div class="sidebar-note"><span class="eyebrow">{{ 'SMALL STEPS. BIG FUTURE.' | t }}</span><p>{{ 'Learn a skill. Try a career. Find what feels right.' | t }}</p></div>
            <button class="logout" [disabled]="loggingOut()" (click)="logout()"><app-icon name="logout" />{{ 'Sign out' | t }}</button>
          </nav>
        }
        <main [class.with-sidebar]="auth.user()" id="main-content">
          @if (error()) { <div class="error" role="alert">{{ (error()) | t }}</div> }
          @if (auth.user() && locale.language() !== 'en') { <p class="small muted">{{ 'Catalogue content is currently in English.' | t }}</p> }
          <router-outlet />
        </main>
      </div>
      @if (auth.user() && !onChatPage) {
        <button class="assistant-fab" [attr.aria-label]=" 'Open CareerVerse assistant' | t " aria-haspopup="dialog" [attr.aria-expanded]="chatOpen()" (click)="chatOpen.set(true)">
          <app-icon name="chatbot" />
          <span>{{ 'Career assistant' | t }}</span>
        </button>
        <ion-modal class="assistant-modal" [isOpen]="chatOpen()" (didDismiss)="chatOpen.set(false)" [attr.aria-label]=" 'CareerVerse assistant' | t ">
          <ng-template>
            <ion-header><ion-toolbar>
              <ion-title>{{ 'CareerVerse assistant' | t }}</ion-title>
              <ion-buttons slot="end"><ion-button [attr.aria-label]=" 'Close career assistant' | t " (click)="chatOpen.set(false)">{{ 'Close' | t }}</ion-button></ion-buttons>
            </ion-toolbar></ion-header>
            <ion-content><div class="assistant-content"><app-career-chat [embedded]="true" /></div></ion-content>
          </ng-template>
        </ion-modal>
      }
    </ion-app>
  `,
})
export class AppComponent {
  readonly locale = inject(LocaleService);
  private readonly push = inject(PushService);
  readonly auth = inject(AuthService);
  readonly notificationCount = inject(NotificationCountService);
  private readonly router = inject(Router);
  readonly dark = signal(localStorage.getItem('cv-web-theme') === 'dark');
  readonly error = signal('');
  readonly loggingOut = signal(false);
  readonly chatOpen = signal(false);
  get onChatPage() { return this.router.url.split('?')[0] === '/chat'; }
  constructor() {
    this.applyTheme();
    effect(onCleanup => {
      const userId = this.auth.user()?.id;
      this.notificationCount.reset();
      if (userId === undefined) return;
      void this.notificationCount.refresh();
      const timer = setInterval(() => {
        if (document.visibilityState === 'visible') void this.notificationCount.refresh();
      }, 30000);
      onCleanup(() => clearInterval(timer));
    });
    this.router.events.pipe(takeUntilDestroyed()).subscribe(event => {
      if (event instanceof NavigationEnd) {
        this.chatOpen.set(false);
        void this.notificationCount.refresh();
      }
    });
  }
  toggleTheme() {
    this.dark.update(value => !value);
    localStorage.setItem('cv-web-theme', this.dark() ? 'dark' : 'light');
    this.applyTheme();
  }
  async changeLanguage(event: Event) {
    const target=event.target;
    if (!(target instanceof HTMLSelectElement)) return;
    this.locale.setLanguage(target.value);
    if (this.auth.user()) {
      try { await this.push.updateLanguage(); }
      catch(error) { this.error.set(errorMessage(error)); }
    }
  }
  private applyTheme() { document.documentElement.classList.toggle('dark', this.dark()); }
  async logout() {
    this.loggingOut.set(true);
    this.error.set('');
    try {
      const navigated = await this.router.navigateByUrl('/login');
      if (navigated) {
        await this.push.disable();
        await this.auth.logout();
      }
    } catch (error) { this.error.set(errorMessage(error)); }
    finally { this.loggingOut.set(false); }
  }
}

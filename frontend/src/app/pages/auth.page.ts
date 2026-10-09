import { TranslatePipe } from '../core/locale.service';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { IonicModule } from '@ionic/angular';
import { AuthService } from '../core/auth.service';
import { errorMessage } from '../core/api.service';
import { CareerArtComponent } from '../widgets/career-art.component';
import { AppIconComponent } from '../widgets/app-icon.component';
import { GoogleSigninComponent } from '../widgets/google-signin.component';

@Component({
  standalone: true,
  imports: [TranslatePipe, FormsModule, IonicModule, RouterLink, CareerArtComponent, AppIconComponent, GoogleSigninComponent],
  template: `
    <div class="auth-layout">
      <section class="auth-story">
        <span class="eyebrow">{{ 'YOUR FUTURE IS NOT A GUESSING GAME' | t }}</span>
        <h1>{{ "Don't just choose a career." | t }}<br><em>{{ 'Experience it.' | t }}</em></h1>
        <p>{{ 'Discover real-world roles, learn the essentials, and put your skills to the test. Your next chapter starts here.' | t }}</p>
        <div class="auth-illustration"><app-career-art [animated]="true" /></div>
        <div class="auth-features"><span><app-icon name="book" />{{ 'Practical courses' | t }}</span><span><app-icon name="lab" />{{ 'Career simulations' | t }}</span><span><app-icon name="sparkles" />{{ 'Personalized matches' | t }}</span></div>
      </section>
      <section class="auth-card">
        <span class="eyebrow">{{ 'WELCOME TO CAREERVERSE' | t }}</span>
        <h2>{{ (register ? 'Create your account' : 'Welcome back') | t }}</h2>
        <p class="muted">{{ (register ? 'Start exploring what you could become.' : 'Continue building a future that fits you.') | t }}</p>
        @if (error()) { <div class="error" role="alert">{{ (error()) | t }}</div> }
        <form #form="ngForm" (ngSubmit)="submit()" class="form-stack">
          @if (register) {
            <label>{{ 'Full name' | t }}<input name="name" [(ngModel)]="name" required minlength="2" maxlength="150" autocomplete="name" [placeholder]=" 'Your name' | t "></label>
          }
          <label>{{ 'Email address' | t }}<input name="email" [(ngModel)]="email" required email type="email" autocomplete="email" [placeholder]=" 'you@example.com' | t "></label>
          <label>{{ 'Password' | t }}<input name="password" [(ngModel)]="password" required minlength="8" type="password" [attr.autocomplete]="register ? 'new-password' : 'current-password'" [placeholder]=" 'At least 8 characters' | t "></label>
          @if (register) {
            <label>{{ 'Confirm password' | t }}<input name="confirm" [(ngModel)]="confirm" required type="password" autocomplete="new-password" [placeholder]=" 'Repeat your password' | t "></label>
          }
          <ion-button expand="block" type="submit" [disabled]="form.invalid || busy()">
            @if (busy()) { <ion-spinner name="dots" /> } @else { {{ (register ? 'Create account' : 'Sign in') | t }} }
          </ion-button>
        </form>
        @if (!register) { <a routerLink="/forgot-password" class="forgot-password">{{ 'Forgot your password?' | t }}</a> }
        <app-google-signin (credential)="googleLogin($event)" />
        <p class="auth-switch">{{ (register ? 'Already have an account?' : 'New to CareerVerse?') | t }}
          <a [routerLink]="register ? '/login' : '/register'">{{ (register ? 'Sign in' : 'Create an account') | t }}</a>
        </p>
        <p class="small muted">{{ 'Your scores and learning progress are saved to your account. Demo courses are available immediately.' | t }}</p>
      </section>
    </div>
  `,
})
export class AuthPage {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  readonly register = this.route.snapshot.routeConfig?.path === 'register';
  readonly error = signal(this.route.snapshot.queryParamMap.get('connection') ? 'The API server could not be reached. Start Django and retry.' : '');
  readonly busy = signal(false);
  name = ''; email = ''; password = ''; confirm = '';
  private async navigateAfterLogin() {
    const next = this.route.snapshot.queryParamMap.get('next');
    await this.router.navigateByUrl(next?.startsWith('/') && !next.startsWith('//') ? next : '/');
  }
  async googleLogin(credential: string) {
    if (this.busy()) return;
    this.busy.set(true); this.error.set('');
    try {
      await this.auth.authenticateGoogle(credential);
      await this.navigateAfterLogin();
    } catch(error) { this.error.set(errorMessage(error)); }
    finally { this.busy.set(false); }
  }
  async submit() {
    if (this.busy()) return;
    this.error.set('');
    if (this.register && this.password !== this.confirm) {
      this.error.set('The passwords do not match.');
      return;
    }
    this.busy.set(true);
    try {
      await this.auth.authenticate(this.register ? 'register' : 'login', {
        name: this.name.trim(), email: this.email.trim(), password: this.password,
      });
      await this.navigateAfterLogin();
    } catch (error) { this.error.set(errorMessage(error)); }
    finally { this.busy.set(false); }
  }
}

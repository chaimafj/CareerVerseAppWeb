import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { IonicModule } from '@ionic/angular';
import { ApiService, errorMessage } from '../core/api.service';
import { AuthService } from '../core/auth.service';
import { LocaleService, TranslatePipe } from '../core/locale.service';
import { AppIconComponent } from '../widgets/app-icon.component';

@Component({
  standalone: true,
  imports: [FormsModule, RouterLink, IonicModule, TranslatePipe, AppIconComponent],
  template: `
    <section class="auth-card reset-card">
      <span class="learning-icon"><app-icon name="shield" /></span>
      <h1>{{ (confirming ? 'Choose a new password' : 'Reset your password') | t }}</h1>
      <p class="muted">{{ (confirming ? 'Choose a strong password that you have not used before.' : 'Enter your email address to request a reset link.') | t }}</p>
      @if (error()) { <div class="error" role="alert">{{ error() | t }}</div> }
      @if (success()) {
        <div class="success-message" role="status">
          @if (confirming) { {{ 'Password reset successfully. Sign in with your new password.' | t }} }
          @else { {{ 'A password reset link has been sent to' | t }} <bdi>{{ email.trim() }}</bdi>. }
        </div>
        @if (!confirming) { <p class="small muted">{{ 'If this address belongs to an eligible account, check your inbox and spam folder. The link expires in one hour.' | t }}</p> }
      } @else {
        <form #form="ngForm" (ngSubmit)="submit()" class="form-stack">
          @if (confirming) {
            <label>{{ 'New password' | t }}<input name="password" [(ngModel)]="password" type="password" required minlength="8" maxlength="128" autocomplete="new-password"></label>
            <label>{{ 'Confirm password' | t }}<input name="confirm" [(ngModel)]="confirm" type="password" required maxlength="128" autocomplete="new-password"></label>
          } @else {
            <label>{{ 'Email address' | t }}<input name="email" [(ngModel)]="email" type="email" required email maxlength="254" autocomplete="email"></label>
          }
          <ion-button expand="block" type="submit" [disabled]="form.invalid || busy()">
            @if (busy()) { <ion-spinner name="dots" /> } @else { {{ (confirming ? 'Save new password' : 'Send reset link') | t }} }
          </ion-button>
        </form>
      }
      @if (confirming && !success()) { <a routerLink="/forgot-password" class="secondary-link">{{ 'Request a new reset link' | t }}</a> }
      <p class="auth-switch"><a routerLink="/login">{{ 'Back to sign in' | t }}</a></p>
    </section>
  `,
})
export class PasswordResetPage {
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);
  private readonly locale = inject(LocaleService);
  private readonly params = inject(ActivatedRoute).snapshot.paramMap;
  readonly confirming = !!this.params.get('uid');
  readonly error = signal('');
  readonly success = signal(false);
  readonly busy = signal(false);
  email = ''; password = ''; confirm = '';
  async submit() {
    if (this.busy() || this.success()) return;
    this.error.set('');
    if (this.confirming && this.password !== this.confirm) {
      this.error.set('The passwords do not match.'); return;
    }
    this.busy.set(true);
    try {
      if (this.confirming) {
        await this.api.csrf();
        await this.api.post('auth/password-reset/confirm/', {
          uid: this.params.get('uid'), token: this.params.get('token'), password: this.password,
        }, {'Accept-Language': this.locale.language()});
        this.auth.user.set(null);
      } else {
        await this.auth.requestPasswordReset(this.email);
      }
      this.password = ''; this.confirm = '';
      this.success.set(true);
    } catch(error) { this.error.set(errorMessage(error)); }
    finally { this.busy.set(false); }
  }
}

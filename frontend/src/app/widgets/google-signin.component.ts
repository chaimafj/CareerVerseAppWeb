import { AfterViewInit, Component, ElementRef, EventEmitter, NgZone, OnDestroy, Output, ViewChild, inject, signal } from '@angular/core';
import { ApiService, errorMessage } from '../core/api.service';
import { GoogleConfig, GoogleSigninService } from '../core/google-signin.service';
import { LocaleService, TranslatePipe } from '../core/locale.service';

@Component({
  selector: 'app-google-signin',
  standalone: true,
  imports: [TranslatePipe],
  template: `
    <div class="auth-divider"><span>{{ 'Or continue with' | t }}</span></div>
    <div #button class="google-signin-container"></div>
    @if (!configured() && !loading() && !error()) {
      <button class="google-placeholder" disabled><span aria-hidden="true">G</span>{{ 'Continue with Google' | t }}</button>
      <p class="small muted">{{ 'Google sign-in is not configured yet.' | t }}</p>
    }
    @if (loading()) { <p class="small muted" role="status">{{ 'Loading Google sign-in...' | t }}</p> }
    @if (error()) { <p class="error" role="alert">{{ error() | t }}</p><button class="theme-button" (click)="load()">{{ 'Retry' | t }}</button> }
  `,
})
export class GoogleSigninComponent implements AfterViewInit, OnDestroy {
  private readonly api = inject(ApiService);
  private readonly google = inject(GoogleSigninService);
  private readonly locale = inject(LocaleService);
  private readonly zone = inject(NgZone);
  @ViewChild('button', {static: true}) button!: ElementRef<HTMLElement>;
  @Output() credential = new EventEmitter<string>();
  readonly loading = signal(false);
  readonly configured = signal(false);
  readonly error = signal('');
  private destroyed = false;
  ngAfterViewInit() { void this.load(); }
  ngOnDestroy() { this.destroyed = true; }
  async load() {
    if (this.loading() || this.destroyed) return;
    this.loading.set(true); this.error.set('');
    try {
      const config = await this.api.get<GoogleConfig>('auth/google/config/');
      if (this.destroyed) return;
      this.configured.set(config.configured);
      if (config.configured) await this.google.render(this.button.nativeElement, config, this.locale.language(), value=>{
        if (!this.destroyed) this.zone.run(()=>this.credential.emit(value));
      });
    } catch(error) { if (!this.destroyed) this.error.set(errorMessage(error)); }
    finally { if (!this.destroyed) this.loading.set(false); }
  }
}

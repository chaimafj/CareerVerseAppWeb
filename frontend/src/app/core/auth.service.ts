import { Injectable, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { CanActivateFn, Router } from '@angular/router';
import { ApiService } from './api.service';
import { User } from './models';
import { LocaleService } from './locale.service';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly api = inject(ApiService);
  private readonly locale = inject(LocaleService);
  readonly user = signal<User | null>(null);
  private initialization?: Promise<void>;

  initialize(): Promise<void> {
    return this.initialization ??= this.restore().catch(error => {
      this.initialization = undefined;
      throw error;
    });
  }

  private async restore() {
    await this.api.csrf();
    try {
      this.user.set(await this.api.me());
    } catch (error) {
      if (error instanceof HttpErrorResponse && [401, 403].includes(error.status)) {
        this.user.set(null);
      } else {
        throw error;
      }
    }
  }

  async authenticate(mode: 'login' | 'register', data: {email: string; password: string; name: string}) {
    await this.api.csrf();
    const payload = mode === 'register' ? data : {email: data.email, password: data.password};
    const user = await this.api.post<User>(`auth/${mode}/`, payload, {'Accept-Language': this.locale.language()});
    this.user.set(user);
    this.initialization = Promise.resolve();
  }

  async saveProfile(data: Partial<User>) {
    this.user.set(await this.api.patch<User>('me/', data));
  }

  async authenticateGoogle(credential: string) {
    await this.api.csrf();
    const user = await this.api.post<User>('auth/google/', {credential}, {'Accept-Language': this.locale.language()});
    this.user.set(user);
    this.initialization = Promise.resolve();
  }

  async requestPasswordReset(email: string) {
    await this.api.csrf();
    await this.api.post('auth/password-reset/', {email: email.trim()}, {'Accept-Language': this.locale.language()});
  }

  async uploadPhoto(file: File) {
    const body = new FormData();
    body.append('photo', file);
    this.user.set(await this.api.post<User>('me/photo/', body));
  }

  async removePhoto() {
    await this.api.delete('me/photo/', {});
    this.user.set(await this.api.me());
  }

  async logout() {
    await this.api.post('auth/logout/');
    this.user.set(null);
  }
}

export const authGuard: CanActivateFn = async (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  try {
    await auth.initialize();
    return auth.user() ? true : router.createUrlTree(['/login'], {queryParams: {next: state.url}});
  } catch (error) {
    console.error('Session initialization failed:', error);
    return router.createUrlTree(['/login'], {queryParams: {connection: 'failed'}});
  }
};

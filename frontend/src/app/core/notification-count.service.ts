import { Injectable, inject, signal } from '@angular/core';
import { ApiService, errorMessage } from './api.service';
import { AuthService } from './auth.service';

@Injectable({providedIn: 'root'})
export class NotificationCountService {
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);
  private revision = 0;
  readonly unread = signal(0);
  readonly error = signal('');

  reset() {
    this.revision++;
    this.unread.set(0);
    this.error.set('');
  }

  async refresh() {
    const userId = this.auth.user()?.id;
    if (userId === undefined) { this.reset(); return; }
    const revision = ++this.revision;
    try {
      const result = await this.api.get<{unread_count: number}>('notifications/count/');
      if (revision !== this.revision || this.auth.user()?.id !== userId) return;
      if (!Number.isSafeInteger(result.unread_count) || result.unread_count < 0) {
        throw new Error('Invalid notification count response.');
      }
      this.unread.set(result.unread_count);
      this.error.set('');
    } catch (error) {
      if (revision !== this.revision || this.auth.user()?.id !== userId) return;
      this.error.set(errorMessage(error));
      console.error('Notification count refresh failed:', error);
    }
  }
}

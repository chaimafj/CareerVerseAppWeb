import { Injectable, inject } from '@angular/core';
import { ApiService } from './api.service';
import { LocaleService } from './locale.service';

export interface PushConfig { configured: boolean; public_key: string; }
export interface AppNotification {
  id: number; title: string; body: string; path: string; read: boolean; created_at: string;
}

@Injectable({providedIn:'root'})
export class PushService {
  private readonly api = inject(ApiService);
  private readonly locale = inject(LocaleService);
  readonly supported = typeof Notification !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window && window.isSecureContext;
  private async registration() {
    if (!this.supported) throw new Error('Push is not supported in this browser.');
    const registration = await navigator.serviceWorker.register('/push-worker.js', {scope:'/'});
    await navigator.serviceWorker.ready;
    return registration;
  }
  async enabled() {
    if (!this.supported) return false;
    const registration = await navigator.serviceWorker.getRegistration('/');
    return !!(await registration?.pushManager.getSubscription());
  }
  async enable() {
    const config = await this.api.get<PushConfig>('push/config/');
    if (!config.configured) throw new Error('Push notifications are not configured on the server.');
    if (!this.supported) throw new Error('Push is not supported in this browser.');
    if (await Notification.requestPermission() !== 'granted') throw new Error('Notification permission was not granted.');
    const registration = await this.registration();
    const key = config.public_key.replace(/-/g,'+').replace(/_/g,'/');
    const binary = atob(key.padEnd(Math.ceil(key.length / 4) * 4,'='));
    const bytes = Uint8Array.from(binary, char => char.charCodeAt(0));
    const existing = await registration.pushManager.getSubscription();
    const subscription = existing ??
      await registration.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:bytes});
    try {
      await this.save(subscription);
    } catch (error) {
      if (!existing) await subscription.unsubscribe();
      throw error;
    }
  }
  private save(subscription: PushSubscription) {
    const data = subscription.toJSON();
    if (!data.endpoint || !data.keys) throw new Error('Invalid browser push subscription.');
    return this.api.post('push/subscriptions/', {endpoint:data.endpoint,keys:data.keys,language:this.locale.language()});
  }
  async updateLanguage() {
    if (!this.supported) return;
    const registration = await navigator.serviceWorker.getRegistration('/');
    const subscription = await registration?.pushManager.getSubscription();
    if (subscription) await this.save(subscription);
  }
  async disable() {
    if (!this.supported) return;
    const registration = await navigator.serviceWorker.getRegistration('/');
    const subscription = await registration?.pushManager.getSubscription();
    if (!subscription) return;
    await this.api.delete('push/subscriptions/', {endpoint:subscription.endpoint});
    if (!await subscription.unsubscribe()) throw new Error('Browser push subscription could not be removed.');
  }
}

import { Injectable } from '@angular/core';

interface GoogleCredential { credential: string; }
export interface GoogleConfig { configured: boolean; client_id: string; nonce: string; }
interface GoogleIdentityApi {
  initialize(options: {client_id: string; nonce: string; callback: (response: GoogleCredential) => void; auto_select: boolean}): void;
  renderButton(element: HTMLElement, options: {theme: string; size: string; text: string; width: number; locale: string}): void;
}
declare global {
  interface Window { google?: {accounts: {id: GoogleIdentityApi}}; }
}

@Injectable({providedIn: 'root'})
export class GoogleSigninService {
  private loading?: Promise<void>;
  async render(element: HTMLElement, config: GoogleConfig, language: string, callback: (credential: string) => void) {
    await this.load();
    const google = window.google?.accounts.id;
    if (!google) throw new Error('Google sign-in could not load. Check your connection and retry.');
    google.initialize({client_id: config.client_id, nonce: config.nonce, auto_select: false, callback: result=>callback(result.credential)});
    google.renderButton(element, {theme: 'outline', size: 'large', text: 'continue_with', width: Math.min(350, element.clientWidth), locale: language});
  }

  private load(): Promise<void> {
    if (window.google?.accounts.id) return Promise.resolve();
    if (this.loading) return this.loading;
    this.loading = new Promise<void>((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      const fail = () => {
        clearTimeout(timer);
        script.remove();
        this.loading = undefined;
        reject(new Error('Google sign-in could not load. Check your connection and retry.'));
      };
      const timer = setTimeout(fail, 15000);
      script.onload = () => {clearTimeout(timer); resolve();};
      script.onerror = fail;
      document.head.appendChild(script);
    });
    return this.loading;
  }
}

import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { IonicModule } from '@ionic/angular';
import { ApiService, errorMessage } from '../core/api.service';
import { LocalDatePipe, LocaleService, TranslatePipe } from '../core/locale.service';
import { AppNotification } from '../core/push.service';

@Component({
  standalone:true,
  imports:[TranslatePipe, LocalDatePipe, IonicModule],
  template:`
    <div class="page-heading"><div><h1>{{ 'Notifications' | t }}</h1><p class="muted">{{ 'Your learning updates and account messages, in one place.' | t }}</p></div></div>
    @if (error()) { <div class="error" role="alert">{{ error() | t }}</div> }
    @if (notice()) { <div class="success-message" role="status">{{ notice() | t }}</div> }
    <div class="notification-toolbar">
      <button class="theme-button" [attr.aria-pressed]="!unreadOnly()" (click)="unreadOnly.set(false)">{{ 'All notifications' | t }} ({{ items().length }})</button>
      <button class="theme-button" [attr.aria-pressed]="unreadOnly()" (click)="unreadOnly.set(true)">{{ 'Unread notifications' | t }} ({{ unreadCount() }})</button>
      <button class="theme-button notification-delete" [disabled]="busy() || !items().length" (click)="removeAll()">{{ 'Delete all' | t }}</button>
    </div>
    @if (busy()) { <div class="loading"><ion-spinner />{{ 'Loading...' | t }}</div> }
    <section class="panel notification-list">
      @for (item of visibleItems(); track item.id) {
        <article class="notification-item" [class.unread]="!item.read" (click)="read(item)">
          <div class="notification-content" role="button" tabindex="0" [attr.aria-disabled]="busy()" (keydown.enter)="read(item)" (keydown.space)="$event.preventDefault(); read(item)">
          <span class="pill" [class.success]="item.read">{{ (item.read ? 'Read notification' : 'New notification') | t }}</span>
          <h2>{{ item.title }}</h2><p>{{ item.body }}</p><small class="muted">{{ item.created_at | localDate:'short' }}</small>
          </div>
          <div class="chat-actions" (click)="$event.stopPropagation()"><a [attr.href]="item.path" class="secondary-link" [attr.aria-disabled]="busy()" (click)="$event.preventDefault(); explore(item)">{{ 'Explore →' | t }}</a>
          </div>
        </article>
      } @empty { @if (!busy() && !error()) { <div class="empty"><h2>{{ (unreadOnly() ? 'You are all caught up.' : 'No notifications yet.') | t }}</h2><p class="muted">{{ 'New learning updates will appear here.' | t }}</p></div> } }
    </section>
  `,
})
export class NotificationsPage implements OnInit {
  private readonly api=inject(ApiService);
  private readonly locale=inject(LocaleService);
  private readonly router=inject(Router);
  readonly items=signal<AppNotification[]>([]);
  readonly busy=signal(false);
  readonly error=signal('');
  readonly notice=signal('');
  readonly unreadOnly=signal(false);
  readonly unreadCount=computed(()=>this.items().filter(item=>!item.read).length);
  readonly visibleItems=computed(()=>this.items().filter(item=>!this.unreadOnly() || !item.read));
  ngOnInit() { void this.load(); }
  async load() {
    if(this.busy())return;
    this.busy.set(true); this.error.set('');
    try {
      this.items.set(await this.api.get<AppNotification[]>('notifications/'));
    } catch(error) { this.error.set(errorMessage(error)); }
    finally { this.busy.set(false); }
  }
  async read(item:AppNotification):Promise<boolean> {
    if(this.busy())return false;
    if(item.read)return true;
    this.busy.set(true);this.error.set('');
    try {await this.api.post(`notifications/${item.id}/read/`);this.items.update(items=>items.map(n=>n.id===item.id?{...n,read:true}:n));return true;}
    catch(error){this.error.set(errorMessage(error));return false;}
    finally {this.busy.set(false);}
  }
  async explore(item:AppNotification) {
    if(!await this.read(item))return;
    try {
      if(!await this.router.navigateByUrl(item.path))this.error.set('Unable to open this notification. Please retry.');
    } catch(error){this.error.set(errorMessage(error));}
  }
  async removeAll() {
    if(this.busy() || !this.items().length || !window.confirm(this.locale.t('Delete all your notifications? This includes read and unread notifications. This action cannot be undone.')))return;
    this.busy.set(true);this.error.set('');this.notice.set('');
    try {
      await this.api.delete('notifications/', {});
      this.items.set([]);
      this.notice.set('All notifications deleted.');
    } catch(error){this.error.set(errorMessage(error));}
    finally{this.busy.set(false);}
  }
}

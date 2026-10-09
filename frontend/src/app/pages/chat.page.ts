import { LocalDatePipe, LocaleService, TranslatePipe } from '../core/locale.service';
import { AfterViewChecked, Component, ElementRef, OnInit, ViewChild, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { IonicModule } from '@ionic/angular';
import { ApiService, errorMessage } from '../core/api.service';
import { ChatExchange } from '../core/models';

@Component({
  selector: 'app-career-chat',
  standalone: true,
  imports: [TranslatePipe, FormsModule, RouterLink, IonicModule, LocalDatePipe],
  template: `
    <div class="page-heading"><div><span class="eyebrow">{{ 'EXPLORE WITH GUIDANCE' | t }}</span>@if (!embedded()) { <h1>{{ 'Career assistant' | t }}</h1> }
      <p class="muted">{{ 'Local, rule-based guidance using the catalogue and your saved progress. No data is sent to external AI services.' | t }}</p>
    </div><button class="theme-button" [disabled]="loading() || busy() || !exchanges().length" (click)="clear()">{{ 'Clear history' | t }}</button></div>
    <section class="panel chat-panel">
      @if (error()) { <div role="alert" class="error">{{ (error()) | t }} @if (loadFailed()) { <button class="theme-button" (click)="load()">{{ 'Retry loading' | t }}</button> }</div> }
      @if (loading()) { <ion-spinner name="dots" [attr.aria-label]=" 'Loading conversation' | t " /> }
      @else {
        <div #history class="chat-history" [attr.aria-label]=" 'Conversation' | t ">
          @if (!exchanges().length) {
            <h2>{{ 'What would you like to explore?' | t }}</h2>
            <p class="muted">{{ 'Ask about a career, the next course to study, your results or how recommendations work. Answers are currently in English.' | t }}</p>
            <div class="chat-actions">
              @for (question of suggestions; track question) { <button class="theme-button" [disabled]="busy() || loadFailed()" (click)="draft = question">{{ (question) | t }}</button> }
            </div>
          }
          @for (exchange of exchanges(); track exchange.id) {
            <article class="chat-exchange">
              <div class="chat-message"><strong>{{ 'You' | t }}</strong><p dir="auto">{{ (exchange.message) | t }}</p></div>
              <div class="chat-reply"><strong>{{ 'CareerVerse assistant' | t }}</strong><p dir="auto">{{ (exchange.reply) | t }}</p>
                <div class="chat-actions">@for (action of exchange.actions; track action.path) { <a class="secondary-link" [routerLink]="action.path">{{ (action.label) | t }} →</a> }</div>
                <small class="muted">{{ exchange.created_at | localDate:'short' }}</small>
              </div>
            </article>
          }
        </div>
        @if (busy()) { <p role="status"><ion-spinner name="dots" /> {{ 'Processing...' | t }}</p> }
        <form class="form-stack chat-composer" #form="ngForm" (ngSubmit)="send()">
          <label>{{ 'Your question' | t }}<textarea name="message" [(ngModel)]="draft" required maxlength="2000" rows="3" [disabled]="busy() || loadFailed()" [placeholder]=" 'Which course should I try for Angular?' | t "></textarea></label>
          <div class="chat-actions"><small class="muted">{{ (draft.length) | t }} {{ '/ 2000 · Guidance is not a definitive career assessment.' | t }}</small>
            <ion-button type="submit" [disabled]="form.invalid || !draft.trim() || busy() || loadFailed()">{{ 'Send question' | t }}</ion-button>
          </div>
        </form>
      }
    </section>
  `,
})
export class ChatPage implements OnInit, AfterViewChecked {
  private readonly locale = inject(LocaleService);
  readonly embedded = input(false);
  @ViewChild('history') private history?: ElementRef<HTMLDivElement>;
  private scrollPending = false;
  private readonly api = inject(ApiService);
  readonly exchanges = signal<ChatExchange[]>([]);
  readonly loading = signal(true);
  readonly loadFailed = signal(false);
  readonly busy = signal(false);
  readonly error = signal('');
  readonly suggestions = ['Help me choose a career', 'Tell me about Angular', 'What do my scores mean?'];
  draft = '';
  ngOnInit() { void this.load(); }
  ngAfterViewChecked() {
    if (this.scrollPending && this.history) {
      this.history.nativeElement.scrollTop = this.history.nativeElement.scrollHeight;
      this.scrollPending = false;
    }
  }
  async load() {
    this.loading.set(true); this.error.set(''); this.loadFailed.set(false);
    try { this.exchanges.set(await this.api.chatHistory()); this.scrollPending = true; }
    catch (error) { this.error.set(errorMessage(error)); this.loadFailed.set(true); }
    finally { this.loading.set(false); }
  }
  async send() {
    const message = this.draft.trim();
    if (!message || message.length > 2000 || this.busy() || this.loadFailed()) return;
    this.busy.set(true); this.error.set('');
    try {
      const exchange = await this.api.sendChat(message);
      this.exchanges.update(items => [...items, exchange].slice(-50));
      this.scrollPending = true;
      this.draft = '';
    } catch (error) { this.error.set(errorMessage(error)); }
    finally { this.busy.set(false); }
  }
  async clear() {
    if (this.busy() || !window.confirm(this.locale.t('Delete your saved conversation history?'))) return;
    this.busy.set(true); this.error.set('');
    try { await this.api.clearChat(); this.exchanges.set([]); }
    catch (error) { this.error.set(errorMessage(error)); }
    finally { this.busy.set(false); }
  }
}

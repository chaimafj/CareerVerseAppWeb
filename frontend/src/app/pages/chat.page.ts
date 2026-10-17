import { LocalDatePipe, LocaleService, TranslatePipe } from '../core/locale.service';
import { AfterViewChecked, Component, ElementRef, OnInit, ViewChild, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { IonicModule } from '@ionic/angular';
import { ApiService, errorMessage } from '../core/api.service';
import { ChatExchange } from '../core/models';
import { AppIconComponent } from '../widgets/app-icon.component';

@Component({
  selector: 'app-career-chat',
  standalone: true,
  imports: [TranslatePipe, FormsModule, RouterLink, IonicModule, LocalDatePipe, AppIconComponent],
  styleUrl: './chat.page.scss',
  template: `
    <section class="chat-studio" [class.chat-embedded]="embedded()">
    <header class="chat-header">
      <div class="chat-identity"><span class="assistant-mark"><app-icon name="sparkles" /></span><div><span class="chat-eyebrow">{{ 'YOUR CAREER COMPANION' | t }}</span>@if (!embedded()) { <h1>{{ 'Career assistant' | t }}</h1> } @else { <h2>{{ 'A clearer path forward.' | t }}</h2> }<span class="chat-status"><span aria-hidden="true"></span>{{ 'Catalogue-based guidance' | t }}</span></div></div>
      <button class="chat-clear" [disabled]="loading() || busy() || !exchanges().length" (click)="clear()">{{ 'Clear history' | t }}</button>
    </header>
    <div class="chat-trust"><app-icon name="shield" /><p>{{ 'Local, rule-based guidance using the catalogue and your saved progress. No data is sent to external AI services.' | t }}</p></div>
    <section class="chat-panel">
      @if (error()) { <div role="alert" class="error">{{ (error()) | t }} @if (loadFailed()) { <button class="theme-button" (click)="load()">{{ 'Retry loading' | t }}</button> }</div> }
      @if (loading()) { <div class="chat-loading" role="status"><ion-spinner name="dots" /><p>{{ 'Loading conversation' | t }}</p></div> }
      @else {
        <div #history class="chat-history" role="region" tabindex="0" [attr.aria-label]=" 'Conversation' | t " [attr.aria-busy]="busy()">
          @if (!exchanges().length) {
            <div class="chat-welcome">
              <span class="welcome-symbol"><app-icon name="compass" /></span>
              <span class="chat-eyebrow">{{ 'SMALL QUESTIONS. MEANINGFUL NEXT STEPS.' | t }}</span>
              <h2>{{ 'What would you like to explore?' | t }}</h2>
              <p>{{ 'Ask about a career, the next course to study, your results or how recommendations work. Answers are currently in English.' | t }}</p>
            </div>
            <div class="chat-suggestions">
              @for (question of suggestions; track question; let index = $index) {
                <button type="button" [disabled]="busy() || loadFailed()" (click)="selectSuggestion(question)">
                  <span class="suggestion-icon"><app-icon [name]="index === 0 ? 'compass' : index === 1 ? 'book' : 'sparkles'" /></span>
                  <span>{{ question | t }}</span><span class="suggestion-arrow" aria-hidden="true">&#8599;</span>
                </button>
              }
            </div>
          }
          @for (exchange of exchanges(); track exchange.id) {
            <article class="chat-exchange">
              <div class="chat-message"><div class="message-heading"><strong>{{ 'You' | t }}</strong><app-icon name="user" /></div><p dir="auto">{{ (exchange.message) | t }}</p></div>
              <div class="chat-reply"><div class="message-heading"><span class="reply-identity"><app-icon name="sparkles" /><strong>{{ 'CareerVerse assistant' | t }}</strong></span><time [attr.datetime]="exchange.created_at">{{ exchange.created_at | localDate:'short' }}</time></div><p dir="auto">{{ (exchange.reply) | t }}</p>
                <div class="chat-actions">@for (action of exchange.actions; track action.path) { <a [routerLink]="action.path">{{ (action.label) | t }} <span aria-hidden="true">&#8594;</span></a> }</div>
              </div>
            </article>
          }
        </div>
        @if (busy()) { <p class="chat-processing" role="status"><ion-spinner name="dots" /> {{ 'Processing...' | t }}</p> }
        <div class="sr-only" role="status">{{ busy() ? ('Processing...' | t) : exchanges().length ? ('Reply ready' | t) : '' }}</div>
        <form class="form-stack chat-composer" #form="ngForm" (ngSubmit)="send()">
          <label>{{ 'Your question' | t }}<textarea #messageInput name="message" [(ngModel)]="draft" required maxlength="2000" rows="2" [disabled]="busy() || loadFailed()" [placeholder]=" 'Which course should I try for Angular?' | t "></textarea></label>
          <div class="composer-footer"><small>{{ draft.length }} / 2000</small>
            <button class="chat-send" type="submit" [disabled]="form.invalid || !draft.trim() || busy() || loadFailed()">{{ 'Send question' | t }} <span aria-hidden="true">&#8593;</span></button>
          </div>
        </form>
        <p class="chat-disclaimer">{{ 'Guidance is not a definitive career assessment.' | t }}</p>
      }
    </section>
    </section>
  `,
})
export class ChatPage implements OnInit, AfterViewChecked {
  private readonly locale = inject(LocaleService);
  readonly embedded = input(false);
  @ViewChild('history') private history?: ElementRef<HTMLDivElement>;
  @ViewChild('messageInput') private messageInput?: ElementRef<HTMLTextAreaElement>;
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
  selectSuggestion(question: string) {
    if (this.busy() || this.loadFailed()) return;
    this.draft = question;
    this.messageInput?.nativeElement.focus();
  }
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

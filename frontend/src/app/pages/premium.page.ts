import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { IonicModule } from '@ionic/angular';
import { ApiService, errorMessage } from '../core/api.service';
import { LocalDatePipe, LocaleService, TranslatePipe } from '../core/locale.service';
import { CareerArtComponent } from '../widgets/career-art.component';
import { AuthService } from '../core/auth.service';
import { BillingHistoryService, PaymentTransaction } from '../core/billing-history.service';

interface BillingStatus {
  configured: boolean; premium_until: string | null; is_premium: boolean;
  amount: number; currency: string; duration_days: number;
  checkout_status: 'paid' | 'pending' | null; transactions: PaymentTransaction[];
}

@Component({
  standalone:true,
  imports:[TranslatePipe,LocalDatePipe,IonicModule,RouterLink,CareerArtComponent],
  template:`
    <div class="page-heading"><div><span class="eyebrow">Stripe · TEST</span><h1>{{ (status()?.is_premium ? 'Your Premium access' : 'Premium test payment') | t }}</h1></div></div>
    @if (error()) { <div class="error" role="alert">{{ error() | t }}</div> }
    @if (returned === 'success' && status() && status()?.checkout_status !== 'paid') { <div role="status" class="info-panel">{{ (waiting() ? 'Confirming your payment with the server...' : 'Payment confirmation is still pending. Refresh the status in a moment.') | t }}</div> }
    @if (returned === 'success' && status()?.checkout_status === 'paid') { <p role="status" class="success-message">{{ 'Payment confirmed. Your 30 days have been added.' | t }}</p> }
    @if (returned === 'cancelled' && !status()?.is_premium) { <div role="status" class="info-panel">{{ 'Checkout was cancelled. No Premium access has been activated by this return.' | t }}</div> }
    <section class="panel premium-showcase" [class.member-showcase]="status()?.is_premium">
      @if (!status()?.is_premium) { <div class="premium-illustration"><app-career-art subject="premium" [animated]="true" /></div> }
      @if (status(); as s) {
        @if (s.is_premium) {
          <div class="member-hero">
            <div class="member-copy">
              <span class="member-badge"><span aria-hidden="true">&#10003;</span> {{ 'Premium member' | t }}</span>
              <h2>{{ 'Your next level starts here.' | t }}</h2>
              <p>{{ 'Your Premium courses and advanced simulations are unlocked. Choose your next challenge and keep building your future.' | t }}</p>
              <div class="member-expiry" role="status"><strong>{{ 'Premium is active!' | t }}</strong><span>{{ 'Active until' | t }} {{ s.premium_until | localDate:'medium' }}</span></div>
              <div class="member-actions"><a routerLink="/courses" class="member-primary">{{ 'Open my courses' | t }} <span aria-hidden="true">&#8594;</span></a><a routerLink="/labs" class="member-secondary">{{ 'Start a simulation' | t }}</a></div>
            </div>
            <div class="member-art" aria-hidden="true"><app-career-art subject="premium" [animated]="true" /></div>
          </div>
          <div class="member-benefits">
            <article><span aria-hidden="true">01</span><h3>{{ 'Advanced courses unlocked' | t }}</h3><p>{{ 'Prepare with practical lessons before each Premium challenge.' | t }}</p></article>
            <article><span aria-hidden="true">02</span><h3>{{ 'More than quizzes' | t }}</h3><p>{{ 'Practice code, workflows, architecture and investigations.' | t }}</p></article>
            <article><span aria-hidden="true">03</span><h3>{{ 'Learn at your pace' | t }}</h3><p>{{ 'Find your results and continue building your skills.' | t }}</p><a routerLink="/">{{ 'View my progress' | t }} <span aria-hidden="true">&#8594;</span></a></article>
          </div>
        } @else {
          <p>{{ 'Unlock 30 days of Premium with a one-off Stripe test payment.' | t }}</p>
          <p>{{ 'No active Premium access.' | t }}</p>
          @if (!s.configured) { <p class="muted">{{ 'Stripe is not configured. No payment can be started.' | t }}</p> }
        }
        @if (s.is_premium) {
          <details class="member-renewal">
            <summary>{{ 'Manage my Premium access' | t }}</summary>
            <p>{{ 'Your access is verified by the server. A new payment adds 30 days to your current expiry date.' | t }}</p>
            <p><strong>{{ money(s.amount, s.currency) }}</strong> / {{ s.duration_days }} {{ 'days of Premium' | t }}</p>
            <p>{{ 'One-time test payment. No automatic renewal. Each confirmed payment adds 30 days.' | t }}</p>
            @if (!s.configured) { <p class="muted">{{ 'Stripe is not configured. No payment can be started.' | t }}</p> }
            <ion-button [disabled]="busy() || !s.configured || waiting()" (click)="checkout()">{{ 'Extend Premium by 30 days' | t }}</ion-button>
            <p class="small muted">{{ 'Stripe test mode: no real money is charged. Access unlocks only after verified payment confirmation.' | t }}</p>
          </details>
        } @else {
          <div class="premium-offer">
          <h2>{{ money(s.amount, s.currency) }} <small>/ {{ s.duration_days }} {{ 'days of Premium' | t }}</small></h2>
          <p>{{ 'One-time test payment. No automatic renewal. Each confirmed payment adds 30 days.' | t }}</p>
          <ion-button [disabled]="busy() || !s.configured || waiting()" (click)="checkout()">{{ 'Activate Premium for 30 days' | t }}</ion-button>
          <p class="small muted">{{ 'Stripe test mode: no real money is charged. Access unlocks only after verified payment confirmation.' | t }}</p>
        </div>
        <p class="muted">{{ 'Free learning paths remain free. Premium adds an advanced preparation course and a five-task interactive simulation for each installed career.' | t }}</p>
        <div class="card-grid premium-formats">
          <article class="panel"><h3>{{ 'Repair and configure' | t }}</h3><p>{{ 'Complete code, deployment settings and model calculations in contextual workspaces.' | t }}</p></article>
          <article class="panel"><h3>{{ 'Build a workflow' | t }}</h3><p>{{ 'Assemble and reorder delivery pipelines, model releases and recovery plans.' | t }}</p></article>
          <article class="panel"><h3>{{ 'Design and investigate' | t }}</h3><p>{{ 'Place architecture components and inspect synthetic logs, datasets and evaluation reports.' | t }}</p></article>
        </div>
        <p class="small muted">{{ 'Simulations are educational: no submitted code is executed, no cloud resources are created, and all records are synthetic.' | t }}</p>
        <div class="page-actions"><a routerLink="/courses" class="button-link">{{ 'Browse preparation courses' | t }}</a><a routerLink="/labs" class="button-link">{{ 'Explore simulations' | t }}</a></div>
        }
      }
      <button class="theme-button" [disabled]="busy()" (click)="load()">{{ 'Refresh status' | t }}</button>
      @if (busy()) { <p role="status"><ion-spinner />{{ 'Loading...' | t }}</p> }
    </section>
    <section class="panel payment-history">
      <div class="section-heading"><h2>{{ 'Payment history' | t }}</h2><span class="pill">Stripe · TEST</span></div>
      @if (offlineHistory()) { <p class="info-panel" role="status">{{ 'Showing offline history only. Cached records cannot activate Premium.' | t }} @if (savedAt()) { {{ savedAt() | localDate:'medium' }} }</p> }
      @if (cacheError()) { <p class="error" role="alert">{{ cacheError() | t }}</p> }
      @for (payment of transactions(); track payment.id) {
        <article class="payment-row">
          <div><strong>{{ money(payment.amount, payment.currency) }}</strong><span class="pill success">{{ 'Paid' | t }}</span><p class="muted">{{ payment.paid_at | localDate:'medium' }}</p></div>
          <div><strong>{{ '30 days of Premium' | t }}</strong>@if (payment.premium_until) { <p class="muted">{{ 'Access extended until' | t }} {{ payment.premium_until | localDate:'medium' }}</p> }</div>
        </article>
      } @empty { <p class="muted">{{ (busy() ? 'Loading...' : 'No confirmed payments for this account.') | t }}</p> }
      <p class="small muted">{{ 'Only server-confirmed payments are recorded. Offline copies are stored separately for each account on this browser.' | t }}</p>
    </section>
  `,
  styles: [`
    .premium-offer { margin: 26px 0; padding: 24px; border: 1px solid var(--line); border-radius: 18px; background: var(--soft); }
    .premium-offer h2 { font-size: 2rem; }
    .premium-offer h2 small { font-size: 1rem; color: var(--muted); }
    .payment-history { margin-top: 24px; }
    .payment-row { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 18px; padding: 20px 0; border-bottom: 1px solid var(--line); }
    .payment-row > div { min-width: 0; overflow-wrap: anywhere; }
    .payment-row .pill { margin-inline-start: 12px; }
    .payment-row p { font-size: 1rem; margin: 8px 0 0; }
    .premium-formats { margin-block: 24px; }
    .page-actions { flex-wrap: wrap; }
    .member-showcase { padding: 0; overflow: hidden; }
    .member-hero { position: relative; display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(180px, 1fr); gap: 24px; align-items: center; padding: clamp(24px, 4vw, 48px); background: linear-gradient(120deg, #10295c, #373089 65%, #6842a5); color: #fff; animation: member-arrive .55s ease-out both; }
    .member-copy { position: relative; z-index: 1; min-width: 0; }
    .member-badge { display: inline-flex; align-items: center; gap: 10px; padding: 7px 16px; border: 1px solid #f5d78670; border-radius: 30px; color: #ffe5a3; background: #ffffff10; font-size: .9375rem; font-weight: 750; }
    .member-hero h2 { margin: 22px 0 16px; font-size: clamp(2rem, 3.4vw, 3.3rem); line-height: 1.12; letter-spacing: -.035em; color: #fff; }
    .member-hero p { color: #e0e6ff; max-width: 650px; font-size: 1.125rem; }
    .member-expiry { display: flex; flex-direction: column; gap: 5px; margin: 24px 0; padding-inline-start: 16px; border-inline-start: 3px solid #a0efcf; }
    .member-expiry strong { color: #a0efcf; }
    .member-expiry span { font-size: 1rem; }
    .member-actions { display: flex; flex-wrap: wrap; gap: 12px; }
    .member-actions a { display: inline-flex; align-items: center; justify-content: center; gap: 12px; padding: 13px 20px; border-radius: 12px; font-size: 1rem; font-weight: 750; transition: transform .2s; }
    .member-primary { color: #172854; background: #ffe5a3; }
    .member-secondary { color: #fff; background: #ffffff14; border: 1px solid #ffffff70; }
    .member-actions a:hover { transform: translateY(-3px); }
    .member-actions a:focus-visible, .member-renewal summary:focus-visible { outline: 3px solid var(--ion-color-primary); outline-offset: 4px; }
    .member-art { width: 100%; max-width: 320px; justify-self: center; }
    .member-benefits { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px; padding: 28px; }
    .member-benefits article { min-width: 0; padding: 22px; border: 1px solid var(--line); border-radius: 16px; background: var(--soft); }
    .member-benefits article > span { color: var(--accent); font-size: .9375rem; font-weight: 800; }
    .member-benefits h3 { font-size: 1.25rem; margin: 12px 0; }
    .member-benefits p, .member-benefits a { font-size: 1rem; }
    .member-benefits p { color: var(--muted); }
    .member-renewal { margin: 0 28px 24px; padding: 20px; border: 1px solid var(--line); border-radius: 14px; }
    .member-renewal summary { cursor: pointer; font-weight: 750; }
    .member-showcase > .theme-button, .member-showcase > p { margin: 0 28px 24px; }
    @keyframes member-arrive { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
    @media (max-width: 900px) {
      .member-hero { grid-template-columns: minmax(0, 1fr); }
      .member-art { display: none; }
      .member-benefits { grid-template-columns: minmax(0, 1fr); padding: 20px; gap: 12px; }
      .member-renewal { margin-inline: 20px; }
    }
    @media (prefers-reduced-motion: reduce) {
      .member-hero { animation: none; }
      .member-actions a { transition: none; }
      .member-actions a:hover { transform: none; }
    }
  `],
})
export class PremiumPage implements OnInit, OnDestroy {
  private readonly api=inject(ApiService);
  private readonly route=inject(ActivatedRoute);
  private readonly history=inject(BillingHistoryService);
  private readonly auth=inject(AuthService);
  private readonly locale=inject(LocaleService);
  private readonly userId=this.auth.user()?.id;
  readonly returned=this.route.snapshot.queryParamMap.get('checkout');
  private readonly sessionId=this.route.snapshot.queryParamMap.get('session_id');
  readonly status=signal<BillingStatus|null>(null);
  readonly error=signal('');
  readonly busy=signal(false);
  readonly waiting=signal(this.returned === 'success');
  readonly transactions=signal<PaymentTransaction[]>([]);
  readonly offlineHistory=signal(false);
  readonly savedAt=signal('');
  readonly cacheError=signal('');
  private timer?: ReturnType<typeof setTimeout>;
  private checks=0;
  private destroyed=false;
  ngOnInit(){void this.load();}
  ngOnDestroy(){this.destroyed=true;if(this.timer)clearTimeout(this.timer);}
  async load(){
    if(this.busy() || this.destroyed)return;
    if(this.timer)clearTimeout(this.timer);
    this.busy.set(true);this.error.set('');
    try{
      const query=this.sessionId ? '?session_id=' + encodeURIComponent(this.sessionId) : '';
      let status=await this.api.get<BillingStatus>('billing/status/' + query);
      if(!this.destroyed && this.returned === 'success' && this.sessionId && status.checkout_status === 'pending') {
        const confirmation=await this.api.post<{checkout_status:'paid'|'pending'}>('billing/confirm/',{session_id:this.sessionId});
        if(confirmation.checkout_status === 'paid')status=await this.api.get<BillingStatus>('billing/status/' + query);
      }
      if(this.destroyed)return;
      this.status.set(status);
      this.transactions.set(status.transactions);
      this.offlineHistory.set(false);
      this.cacheError.set('');
      const retry=this.returned === 'success' && status.checkout_status !== 'paid' && ++this.checks < 10;
      this.waiting.set(retry);
      if(this.userId !== undefined) {
        try { await this.history.save(this.userId,status.transactions); }
        catch { if(!this.destroyed)this.cacheError.set('The offline copy could not be saved. Your server payment history is unaffected.'); }
      }
    }
    catch(error){
      if(!this.destroyed){
        this.status.set(null);this.error.set(errorMessage(error));this.waiting.set(false);
        this.offlineHistory.set(this.transactions().length > 0);
        if(this.userId !== undefined) {
          try {
            const cached=await this.history.read(this.userId);
            if(!this.destroyed && cached) {
              this.transactions.set(cached.transactions);this.savedAt.set(cached.saved_at);this.offlineHistory.set(true);
            }
          } catch { if(!this.destroyed)this.cacheError.set('The offline payment history could not be read. Retry while online.'); }
        }
      }
    }
    finally{
      this.busy.set(false);
      if(!this.destroyed && this.waiting())this.timer=setTimeout(()=>void this.load(),3000);
    }
  }
  async checkout(){
    if(this.busy() || !this.status()?.configured || this.waiting())return;
    this.busy.set(true);this.error.set('');
    try{
      const result=await this.api.post<{url:string}>('billing/checkout/');
      const url=new URL(result.url);
      if(url.protocol!=='https:' || url.hostname!=='checkout.stripe.com')throw new Error('Invalid Stripe checkout URL.');
      window.location.assign(url.href);
    }catch(error){this.error.set(errorMessage(error));this.busy.set(false);}
  }
  money(amount:number,currency:string) {
    return new Intl.NumberFormat(this.locale.language(),{style:'currency',currency}).format(amount/100);
  }
}

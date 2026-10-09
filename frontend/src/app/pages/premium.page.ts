import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { IonicModule } from '@ionic/angular';
import { ApiService, errorMessage } from '../core/api.service';
import { LocalDatePipe, TranslatePipe } from '../core/locale.service';
import { CareerArtComponent } from '../widgets/career-art.component';

interface BillingStatus { configured:boolean; premium_until:string|null; is_premium:boolean; }

@Component({
  standalone:true,
  imports:[TranslatePipe,LocalDatePipe,IonicModule,RouterLink,CareerArtComponent],
  template:`
    <div class="page-heading"><div><span class="eyebrow">Stripe · TEST</span><h1>{{ (status()?.is_premium ? 'Your Premium access' : 'Premium test payment') | t }}</h1></div></div>
    @if (error()) { <div class="error" role="alert">{{ error() | t }}</div> }
    @if (returned === 'success' && status() && !status()?.is_premium) { <div role="status" class="info-panel">{{ (waiting() ? 'Confirming your payment with the server...' : 'Payment confirmation is still pending. Refresh the status in a moment.') | t }}</div> }
    @if (returned === 'cancelled' && !status()?.is_premium) { <div role="status" class="info-panel">{{ 'Checkout was cancelled. No Premium access has been activated by this return.' | t }}</div> }
    <section class="panel premium-showcase">
      <div class="premium-illustration"><app-career-art subject="premium" [animated]="true" /></div>
      @if (status(); as s) {
        @if (s.is_premium) {
          <div class="premium-confirmation" role="status">
            <span class="premium-check" aria-hidden="true">&#10003;</span>
            <h2>{{ 'Premium is active!' | t }}</h2>
            <p>{{ 'Your access has been confirmed by the server. No further payment is needed while it is active.' | t }}</p>
            <p class="success-message">{{ 'Active until' | t }} {{ s.premium_until | localDate:'medium' }}</p>
          </div>
          <a routerLink="/careers" class="button-link">{{ 'Continue exploring careers →' | t }}</a>
        } @else {
          <p>{{ 'Unlock 30 days of Premium with a one-off Stripe test payment.' | t }}</p>
          <p>{{ 'No active Premium access.' | t }}</p>
          @if (!s.configured) { <p class="muted">{{ 'Stripe is not configured. No payment can be started.' | t }}</p> }
          @if (returned !== 'success') { <ion-button [disabled]="busy() || !s.configured" (click)="checkout()">{{ 'Pay with Stripe (test mode)' | t }}</ion-button> }
        }
        <p class="muted">{{ 'The nine original labs stay free. Premium unlocks code repair, visual Cloud architecture and incident evidence workshops, plus their preparation courses.' | t }}</p>
      }
      <button class="theme-button" [disabled]="busy()" (click)="load()">{{ 'Refresh status' | t }}</button>
      @if (busy()) { <p role="status"><ion-spinner />{{ 'Loading...' | t }}</p> }
    </section>
  `,
})
export class PremiumPage implements OnInit, OnDestroy {
  private readonly api=inject(ApiService);
  private readonly route=inject(ActivatedRoute);
  readonly returned=this.route.snapshot.queryParamMap.get('checkout');
  readonly status=signal<BillingStatus|null>(null);
  readonly error=signal('');
  readonly busy=signal(false);
  readonly waiting=signal(this.returned === 'success');
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
      const status=await this.api.get<BillingStatus>('billing/status/');
      if(this.destroyed)return;
      this.status.set(status);
      const retry=this.returned === 'success' && !status.is_premium && ++this.checks < 10;
      this.waiting.set(retry);
      if(retry)this.timer=setTimeout(()=>void this.load(),3000);
    }
    catch(error){if(!this.destroyed){this.error.set(errorMessage(error));this.waiting.set(false);}}
    finally{this.busy.set(false);}
  }
  async checkout(){
    if(this.busy() || !this.status()?.configured || this.status()?.is_premium || this.returned === 'success')return;
    this.busy.set(true);this.error.set('');
    try{
      const result=await this.api.post<{url:string}>('billing/checkout/');
      const url=new URL(result.url);
      if(url.protocol!=='https:' || url.hostname!=='checkout.stripe.com')throw new Error('Invalid Stripe checkout URL.');
      window.location.assign(url.href);
    }catch(error){this.error.set(errorMessage(error));this.busy.set(false);}
  }
}

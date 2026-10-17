import { Component, Input, OnDestroy, OnInit, signal } from '@angular/core';
import { TranslatePipe } from '../core/locale.service';
import { CareerArtComponent } from './career-art.component';
import { OverviewArtComponent } from './overview-art.component';

@Component({
  selector: 'app-career-carousel',
  standalone: true,
  imports: [TranslatePipe, CareerArtComponent, OverviewArtComponent],
  template: `
    <section class="career-carousel" [class.studio-carousel]="studio" role="region" [attr.aria-label]="'Career inspiration' | t"
      [attr.aria-roledescription]="'carousel' | t"
      (mouseenter)="hovered = true" (mouseleave)="hovered = false"
      (focusin)="paused.set(true)" (keydown)="onKeydown($event)">
      <div class="carousel-topline">
        <span><span class="carousel-status" aria-hidden="true"></span>{{ 'EXPLORE YOUR POSSIBILITIES' | t }}</span>
        <span class="carousel-counter">{{ active() + 1 }} / {{ slides.length }}</span>
      </div>
      <div class="carousel-stage" [attr.aria-live]="paused() ? 'polite' : 'off'" aria-atomic="true">
        @for (slide of slides; track slide.subject; let i = $index) {
          @if (active() === i) {
            <div class="carousel-slide" role="group" [attr.aria-roledescription]="'slide' | t"
              [attr.aria-label]="(i + 1) + ' / ' + slides.length + ': ' + (slide.title | t)">
              <div class="carousel-visual" [class]="'carousel-visual scene-' + slide.subject">
                <div class="scene-grid" aria-hidden="true"></div>
                <span class="scene-tag">{{ slide.tag | t }}</span>
                @if (studio) {
                  <app-overview-art [subject]="slide.subject" [animated]="!paused()" />
                } @else {
                  <app-career-art [subject]="slide.subject" [animated]="!paused()" />
                }
                <span class="scene-caption">{{ 'Learn by doing' | t }}<span aria-hidden="true">&#8599;</span></span>
              </div>
              <div class="carousel-caption"><h3>{{ slide.title | t }}</h3><p>{{ slide.description | t }}</p></div>
            </div>
          }
        }
      </div>
      <div class="carousel-controls">
        <div class="carousel-dots" [attr.aria-label]="'Choose an illustration' | t">
          @for (slide of slides; track slide.subject; let i = $index) {
            <button type="button" class="carousel-dot" [class.selected]="active() === i"
              [attr.aria-label]="slide.title | t" [attr.aria-current]="active() === i ? 'true' : null"
              (click)="select(i)"><span></span></button>
          }
        </div>
        <div class="carousel-buttons">
          <button type="button" (click)="paused.update(toggle)" [attr.aria-label]="(paused() ? 'Play slideshow' : 'Pause slideshow') | t">
            <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              @if (paused()) { <path d="m7 4 9 6-9 6Z"/> } @else { <path d="M5 4h4v12H5Zm6 0h4v12h-4Z"/> }
            </svg>
          </button>
          <button type="button" (click)="step(-1)" [attr.aria-label]="'Previous illustration' | t">
            <svg class="direction-arrow" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m12 5-5 5 5 5"/></svg>
          </button>
          <button type="button" (click)="step(1)" [attr.aria-label]="'Next illustration' | t">
            <svg class="direction-arrow" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m8 5 5 5-5 5"/></svg>
          </button>
        </div>
      </div>
    </section>
  `,
  styles: [`
    :host { display: block; min-width: 0; }
    .career-carousel { overflow: hidden; border: 1px solid #ffffff24; border-radius: 24px; color: #edf3ff; background: linear-gradient(145deg,#182c59,#142043 65%,#29224f); box-shadow: 0 20px 45px #152c6126; }
    .carousel-topline { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 22px 24px 0; color: #c6d5f3; font-size: .8125rem; letter-spacing: 1.6px; font-weight: 700; }
    .carousel-topline > span:first-child { display: flex; align-items: center; gap: 8px; }
    .carousel-status { width: 6px; height: 6px; background: #5eead4; border-radius: 50%; box-shadow: 0 0 12px #5eead480; flex-shrink: 0; }
    .carousel-counter { letter-spacing: 1px; white-space: nowrap; }
    .carousel-stage { position: relative; }
    .carousel-slide { animation: slide-reveal .5s ease-out both; }
    .carousel-visual { position: relative; isolation: isolate; height: 220px; display: grid; place-items: center; margin: 12px 20px 0; }
    .carousel-visual::before { content: ''; position: absolute; z-index: -1; width: 180px; height: 150px; border-radius: 50%; background: #8166ff30; filter: blur(30px); }
    .scene-cloud::before { background: #2dd4bf28; }
    .scene-security::before { background: #a78bfa40; }
    .scene-grid { position: absolute; inset: 12px 0; z-index: -1; opacity: .25; background-image: linear-gradient(#8ca9e526 1px,transparent 1px),linear-gradient(90deg,#8ca9e526 1px,transparent 1px); background-size: 28px 28px; mask-image: radial-gradient(ellipse,#000,transparent 70%); }
    app-career-art { width: min(100%,310px); color: #acbaff; }
    .scene-tag, .scene-caption { position: absolute; z-index: 1; padding: 8px 11px; border: 1px solid #c5d4ff30; border-radius: 10px; background: #192b50ed; color: #e3ecff; font-size: .875rem; box-shadow: 0 6px 16px #00000018; }
    .scene-tag { top: 16px; inset-inline-start: 0; transform: rotate(-4deg); }
    .scene-caption { bottom: 15px; inset-inline-end: 0; display: flex; gap: 16px; align-items: center; }
    .scene-caption span { color: #5eead4; font-size: 1.1875rem; }
    .carousel-caption { padding: 0 24px; min-height: 95px; }
    .carousel-caption h3 { color: #fff; font-size: 1.4375rem; letter-spacing: -.5px; margin: 0 0 8px; }
    .carousel-caption p { font-size: .9375rem; color: #bccce8; line-height: 1.65; margin: 0; }
    .carousel-controls { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin: 12px 24px 18px; border-top: 1px solid #c5d4ff20; padding-top: 12px; }
    .carousel-dots, .carousel-buttons { display: flex; align-items: center; gap: 4px; }
    button { display: grid; place-items: center; width: 36px; height: 36px; border: 1px solid #c5d4ff30; border-radius: 50%; background: transparent; color: #e3ecff; transition: background .2s, border-color .2s; }
    button:hover { background: #ffffff15; border-color: #c5d4ff80; }
    button svg { width: 18px; height: 18px; }
    .carousel-dot { border: 0; width: 28px; height: 36px; border-radius: 8px; }
    .carousel-dot span { width: 6px; height: 6px; border-radius: 6px; background: #8494b5; transition: width .25s, background .25s; }
    .carousel-dot.selected span { width: 22px; background: #9cbaff; }
    :host-context([dir="rtl"]) .direction-arrow { transform: scaleX(-1); }
    .studio-carousel { background: #10245680; border-color: #bed4ff26; box-shadow: inset 0 1px 0 #ffffff10; border-radius: 22px; }
    .studio-carousel .carousel-visual { height: 215px; margin: 0 12px; }
    .studio-carousel app-overview-art { width: min(100%,340px); }
    .studio-carousel .scene-tag { top: 18px; inset-inline-start: 8px; font-size: .75rem; }
    .studio-carousel .scene-caption { bottom: 8px; font-size: .8125rem; }
    .studio-carousel .carousel-caption { min-height: 85px; }
    .studio-carousel .carousel-caption h3 { font-size: 1.375rem; }
    .studio-carousel .carousel-controls { margin-top: 6px; }
    @keyframes slide-reveal { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
    @media (max-width:720px) {
      .carousel-topline { padding: 18px 18px 0; font-size: .75rem; }
      .carousel-visual { height: 175px; margin-top: 4px; }
      app-career-art { width: 245px; max-width: 100%; }
      .scene-tag, .scene-caption { font-size: .8125rem; padding: 6px 8px; }
      .carousel-caption { padding-inline: 18px; min-height: 90px; }
      .carousel-caption h3 { font-size: 1.3125rem; }
      .carousel-controls { margin-inline: 18px; }
    }
    @media (prefers-reduced-motion:reduce) { *, *::before { animation: none !important; transition: none !important; } }
  `],
})
export class CareerCarouselComponent implements OnInit, OnDestroy {
  @Input() studio = false;
  readonly slides = [
    {subject: 'code', tag: 'CREATE', title: 'Build something that matters.', description: 'Turn your curiosity into code, one practical challenge at a time.'},
    {subject: 'cloud', tag: 'CONNECT', title: 'Think beyond the horizon.', description: 'Explore the systems that keep our connected world running.'},
    {subject: 'security', tag: 'PROTECT', title: 'Be the first line of defense.', description: 'Follow the clues and discover your cybersecurity instincts.'},
  ];
  readonly active = signal(0);
  readonly paused = signal(false);
  readonly toggle = (value: boolean) => !value;
  hovered = false;
  private timer?: ReturnType<typeof setInterval>;
  private motion?: MediaQueryList;
  private readonly motionChanged = (event: MediaQueryListEvent) => {
    if (event.matches) this.paused.set(true);
  };
  ngOnInit() {
    this.motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    this.paused.set(this.motion.matches);
    this.motion.addEventListener('change', this.motionChanged);
    this.timer = setInterval(() => {
      if (!this.paused() && !this.hovered && !document.hidden) {
        this.active.update(index => (index + 1) % this.slides.length);
      }
    }, 6500);
  }
  select(index: number) {
    this.paused.set(true);
    this.active.set(index);
  }
  step(direction: number) {
    this.select((this.active() + direction + this.slides.length) % this.slides.length);
  }
  onKeydown(event: KeyboardEvent) {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
    event.preventDefault();
    const direction = event.key === 'ArrowRight' ? 1 : -1;
    this.step(document.documentElement.dir === 'rtl' ? -direction : direction);
  }
  ngOnDestroy() {
    clearInterval(this.timer);
    this.motion?.removeEventListener('change', this.motionChanged);
  }
}

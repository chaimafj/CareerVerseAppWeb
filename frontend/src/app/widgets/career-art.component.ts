import { Component, Input } from '@angular/core';

type ArtVariant = 'launch' | 'code' | 'cloud' | 'security' | 'premium';

@Component({
  selector: 'app-career-art',
  standalone: true,
  host: {'aria-hidden': 'true'},
  template: `
    <svg viewBox="0 0 360 250" fill="none" focusable="false" [class.animated]="animated">
      <ellipse cx="180" cy="218" rx="114" ry="13" fill="currentColor" opacity=".08"/>
      <circle cx="180" cy="122" r="98" fill="currentColor" opacity=".06"/>
      <ellipse class="art-orbit" cx="180" cy="122" rx="142" ry="90" stroke="currentColor" stroke-opacity=".22" stroke-dasharray="5 9"/>
      <g class="art-stars" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
        <path d="M44 70v14m-7-7h14 M309 152v14m-7-7h14 M279 39v10m-5-5h10"/>
        <circle cx="72" cy="174" r="4" fill="#2dd4bf" stroke="none"/>
        <circle cx="296" cy="91" r="5" fill="#fbbf24" stroke="none"/>
      </g>
      <g class="art-float">
      @switch (variant) {
        @case ('code') {
          <rect x="77" y="55" width="206" height="137" rx="16" fill="#192b51" stroke="#8495ff" stroke-width="3"/>
          <path d="M78 84h204" stroke="#8495ff" stroke-opacity=".4"/>
          <circle cx="93" cy="70" r="4" fill="#fb7185"/><circle cx="108" cy="70" r="4" fill="#fbbf24"/><circle cx="123" cy="70" r="4" fill="#2dd4bf"/>
          <path d="m143 109-24 23 24 23m74-46 24 23-24 23m-28-50-18 55" stroke="#b5c4ff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
          <rect x="135" y="188" width="90" height="8" rx="4" fill="#7185ee"/>
        }
        @case ('cloud') {
          <path d="M124 135c-45 0-45-64-8-67 11-45 80-49 97-8 47-11 73 64 28 74Z" fill="#dceaff" stroke="#5a83e8" stroke-width="4"/>
          <path d="M180 135v24m-76 18v-18h152v18" stroke="#8b93ec" stroke-width="4"/>
          <rect x="80" y="177" width="48" height="30" rx="8" fill="#2dd4bf"/>
          <rect x="156" y="177" width="48" height="30" rx="8" fill="#a78bfa"/>
          <rect x="232" y="177" width="48" height="30" rx="8" fill="#60a5fa"/>
          <path d="M98 192h12m64 0h12m64 0h12" stroke="#192b51" stroke-width="3" stroke-linecap="round"/>
        }
        @case ('security') {
          <path d="m180 40 76 29v63c0 43-45 67-76 80-31-13-76-37-76-80V69Z" fill="#23355e" stroke="#9d95ff" stroke-width="4"/>
          <path d="m143 125 24 24 50-54" stroke="#2dd4bf" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="259" cy="174" r="26" fill="#dceaff" stroke="#8495ff" stroke-width="3"/>
          <rect x="248" y="171" width="22" height="17" rx="4" fill="#6856da"/>
          <path d="M253 171v-6a6 6 0 0 1 12 0v6" stroke="#6856da" stroke-width="4"/>
        }
        @case ('premium') {
          <path d="m101 79 40 28 39-54 39 54 40-28-15 103H116Z" fill="#fbbf24" stroke="#f59e0b" stroke-width="4" stroke-linejoin="round"/>
          <rect x="117" y="191" width="126" height="13" rx="6" fill="#a78bfa"/>
          <path d="m180 111 8 16 18 3-13 13 3 18-16-8-16 8 3-18-13-13 18-3Z" fill="#fff7db"/>
        }
        @default {
          <path d="m144 151-35 10 14-39 23-16m56 35-10 35 39-14 16-23" fill="#a78bfa" stroke="#7456cd" stroke-width="3"/>
          <path d="M136 148c1-52 49-103 104-106 3 55-48 104-100 107Z" fill="#e5eeff" stroke="#a8beff" stroke-width="4"/>
          <path d="m217 45 21-3-3 24Z" fill="#a78bfa"/>
          <circle cx="197" cy="87" r="18" fill="#2dd4bf" stroke="#214677" stroke-width="5"/>
          <path class="art-flame" d="m129 155-34 44 47-31-11 26 33-35" fill="#fbbf24" stroke="#f59e0b" stroke-width="3" stroke-linejoin="round"/>
        }
      }
      </g>
      <g class="art-bubble">
        <rect x="42" y="107" width="53" height="45" rx="14" fill="#e4dcff" stroke="#a78bfa" stroke-width="2"/>
        <path d="m56 130 9 9 15-19" stroke="#7655cf" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
      </g>
    </svg>
  `,
  styles: [`
    :host { display: block; width: 100%; color: #9b86f2; }
    svg { display: block; width: 100%; height: auto; }
    .animated .art-float { animation: art-float 5s ease-in-out infinite; }
    .animated .art-bubble { animation: art-float 6s ease-in-out infinite reverse; }
    .animated .art-stars { animation: art-glow 4s ease-in-out infinite; }
    @keyframes art-float { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-9px); } }
    @keyframes art-glow { 0%,100% { opacity: .45; } 50% { opacity: 1; } }
    @media (prefers-reduced-motion: reduce) { .animated * { animation: none !important; } }
  `],
})
export class CareerArtComponent {
  @Input() subject = '';
  @Input() animated = false;
  get variant(): ArtVariant {
    const subject = this.subject.toLowerCase();
    if (subject.includes('premium')) return 'premium';
    if (subject.includes('cloud')) return 'cloud';
    if (subject.includes('cyber') || subject.includes('security')) return 'security';
    if (subject.includes('angular') || subject.includes('developer') || subject.includes('code')) return 'code';
    return 'launch';
  }
}

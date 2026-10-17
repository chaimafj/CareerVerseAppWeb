import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-overview-art',
  standalone: true,
  host: {'aria-hidden': 'true'},
  template: `
    <svg viewBox="0 0 480 300" fill="none" focusable="false" [class.moving]="animated">
      <defs>
        <linearGradient [id]="id + '-platform'" x1="90" y1="170" x2="380" y2="290" gradientUnits="userSpaceOnUse"><stop stop-color="#596ce1"/><stop offset="1" stop-color="#28396d"/></linearGradient>
        <linearGradient [id]="id + '-glass'" x1="130" y1="50" x2="340" y2="230" gradientUnits="userSpaceOnUse"><stop stop-color="#bad6ff"/><stop offset="1" stop-color="#7c7ff3"/></linearGradient>
        <linearGradient [id]="id + '-screen'" x1="140" y1="60" x2="320" y2="190" gradientUnits="userSpaceOnUse"><stop stop-color="#162c57"/><stop offset="1" stop-color="#253a72"/></linearGradient>
      </defs>
      <ellipse cx="245" cy="267" rx="168" ry="20" fill="#07112b" opacity=".25"/>
      <path d="m65 221 176-89 177 89-177 71Z" [attr.fill]="'url(#' + id + '-platform)'"/>
      <path d="m65 221 176 71v-14L65 208Z" fill="#7285ea" opacity=".5"/>
      <path d="m241 278 177-70v13l-177 71Z" fill="#314578"/>
      <g class="ambient" stroke="#8ba8f6" stroke-opacity=".35" stroke-dasharray="4 7">
        <path d="m45 166 198-99 197 99M47 185l196-99 196 99"/>
        <path d="m130 263 112-56 109 53"/>
      </g>
      @switch (variant) {
        @case ('ai') {
          <g class="scene-main">
            <path d="m165 91 78-39 76 39v98l-76 40-78-40Z" [attr.fill]="'url(#' + id + '-screen)'" stroke="#b3c6ff" stroke-width="3"/>
            <path d="m165 91 78 40 76-40m-76 40v98" stroke="#a78bfa" stroke-width="3"/>
            <g stroke="#7de3d6" stroke-width="3"><path d="m203 106 40 25 39-25m-79 0v53l40 26 39-26v-53m-39 25v54"/></g>
            <g fill="#d4cbff" stroke="#a78bfa" stroke-width="3"><circle cx="203" cy="106" r="10"/><circle cx="282" cy="106" r="10"/><circle cx="243" cy="131" r="12"/><circle cx="203" cy="159" r="10"/><circle cx="282" cy="159" r="10"/><circle cx="243" cy="185" r="10"/></g>
          </g>
          <g class="scene-satellite" fill="#31487f" stroke="#9cb5ff" stroke-width="2"><path d="m85 156 45-20 28 15v43l-45 20-28-15Z"/><path d="m340 115 42-20 28 15v43l-42 20-28-15Z"/></g>
          <path class="data-flow" d="m107 235 46 18 36-17m111-10 34 17 48-21" stroke="#5eead4" stroke-width="3" stroke-dasharray="6 5"/>
        }
        @case ('data') {
          <g class="scene-main">
            <path d="m124 77 199-34 15 145-199 34Z" [attr.fill]="'url(#' + id + '-glass)'" stroke="#c2d4ff" stroke-width="3"/>
            <path d="m137 89 175-30 12 116-175 30Z" [attr.fill]="'url(#' + id + '-screen)'"/>
            <path d="m163 164 22-4m9-16 22-4m9-23 22-4m9-26 22-4" stroke="#5eead4" stroke-width="14"/>
            <path d="m161 181 25-4m7-7 25-4m6-7 25-4m6-7 25-4" stroke="#8ba8f6" stroke-width="3"/>
            <path d="m217 209 6 23-28 13 65 6 26-13-44-10-2-23" fill="#a5b7f7"/>
          </g>
          <g class="scene-satellite"><ellipse cx="363" cy="166" rx="29" ry="13" fill="#7089cf"/><path d="M334 166v39c0 18 58 18 58 0v-39" fill="#3b568c" stroke="#91aaf3" stroke-width="2"/><ellipse cx="363" cy="166" rx="29" ry="13" fill="#7089cf" stroke="#91aaf3" stroke-width="2"/><path d="M334 180c0 18 58 18 58 0m-58 13c0 18 58 18 58 0" stroke="#5eead4" stroke-width="2"/></g>
        }
        @case ('cloud') {
          <g class="scene-main">
            <path d="M157 100c-27 0-30-37-6-44 2-31 49-41 65-13 26-13 51 10 45 32 27 8 18 35-4 35h-99Z" fill="#c7e4ff" stroke="#91c7ff" stroke-width="3"/>
            <path d="M177 112v31l67 34 66-34v-27" stroke="#5eead4" stroke-width="3" stroke-dasharray="7 6" class="data-flow"/>
            <g stroke="#9cb5ff" stroke-width="2">
              <path d="m112 184 42-22 44 22v54l-44 21-42-21Z" fill="#324d87"/>
              <path d="m112 184 42 22 44-22m-44 22v53" />
              <path d="m218 175 40-20 42 20v65l-42 20-40-20Z" fill="#4068ac"/>
              <path d="m218 175 40 21 42-21m-42 21v64"/>
              <path d="m317 148 33-17 35 17v71l-35 17-33-17Z" fill="#5765af"/>
              <path d="m317 148 33 18 35-18m-35 18v70"/>
            </g>
            <g stroke="#74e8e0" stroke-width="3" stroke-linecap="round">
              <path d="m122 201 22 11m-22 2 22 11m-22 1 22 11m84-44 20 10m-20 4 20 10m-20 4 20 10m80-63 14 7m-14 7 14 7m-14 7 14 7"/>
            </g>
            <path d="m163 70 14 14 24-27" stroke="#3874bd" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
          </g>
          <g class="scene-satellite"><circle cx="342" cy="70" r="25" fill="#263c6a" stroke="#7be9dd" stroke-width="2"/><path d="m331 70 8 8 15-17" stroke="#7be9dd" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/></g>
        }
        @case ('security') {
          <g class="scene-main">
            <path d="m165 64 77-27 78 27v84c0 50-49 81-78 96-29-15-77-46-77-96Z" [attr.fill]="'url(#' + id + '-glass)'" stroke="#c2d4ff" stroke-width="3"/>
            <path d="m180 76 62-22 63 22v70c0 38-36 65-63 81-27-16-62-43-62-81Z" [attr.fill]="'url(#' + id + '-screen)'"/>
            <circle cx="242" cy="133" r="39" stroke="#5eead4" stroke-width="2" stroke-dasharray="5 6" class="scan-ring"/>
            <rect x="222" y="124" width="40" height="34" rx="7" fill="#5eead4"/>
            <path d="M230 124v-12a12 12 0 0 1 24 0v12" stroke="#b7fff4" stroke-width="5"/>
            <circle cx="242" cy="139" r="4" fill="#1e4a67"/><path d="M242 142v7" stroke="#1e4a67" stroke-width="3"/>
          </g>
          <g class="scene-satellite">
            <path d="m337 157 42-18 31 16v51l-42 18-31-16Z" fill="#31487f" stroke="#91aaf3" stroke-width="2"/>
            <path d="m348 167 20 10 30-14m-30 14v33" stroke="#91aaf3" stroke-width="2"/>
            <path d="m90 139 45-20 28 14v46l-45 20-28-15Z" fill="#344c85" stroke="#91aaf3" stroke-width="2"/>
            <path d="m105 150 12 6 26-11m-38 17 12 6 26-11" stroke="#5eead4" stroke-width="3"/>
          </g>
          <path class="data-flow" d="m115 219 38 19 36-16m104 13 31 13 38-18" stroke="#5eead4" stroke-width="2" stroke-dasharray="5 5"/>
        }
        @default {
          <g class="scene-main">
            <path d="m129 65 190-24 14 145-190 28Z" [attr.fill]="'url(#' + id + '-glass)'" stroke="#c2d4ff" stroke-width="3"/>
            <path d="m140 78 169-22 12 116-169 25Z" [attr.fill]="'url(#' + id + '-screen)'"/>
            <path d="m145 92 165-22" stroke="#6682bd" stroke-width="2"/>
            <circle cx="151" cy="83" r="3" fill="#ff97b9"/><circle cx="162" cy="81.5" r="3" fill="#ffd990"/><circle cx="173" cy="80" r="3" fill="#5eead4"/>
            <path d="m168 116 37-5m-35 17 63-9m-60 21 27-4m-25 16 50-7m-47 19 30-4" stroke="#88aafa" stroke-width="5" stroke-linecap="round"/>
            <path d="m245 112-14 17 17 13m25-36 16 13-14 17m-17-31-5 38" stroke="#5eead4" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="m224 202 4 23-27 12 61 8 24-13-40-10-2-23" fill="#a5b7f7"/>
            <path d="m201 237 61 8 24-13v6l-24 13-61-8Z" fill="#6d83d0"/>
          </g>
          <g class="scene-satellite">
            <path d="m331 95 65 16v76l-65-16Z" fill="#a78bfa" stroke="#cfc5ff" stroke-width="2"/>
            <path d="m341 111 43 10m-43 4 28 7m-28 7 36 9m-36 5 20 5" stroke="#eee7ff" stroke-width="3" stroke-linecap="round"/>
            <path d="m77 155 39-9 7 55-39 9Z" fill="#263b6c" stroke="#91aaf3" stroke-width="2"/>
            <path d="m87 169 20-5m-19 14 12-3m-11 13 20-5" stroke="#5eead4" stroke-width="3" stroke-linecap="round"/>
          </g>
          <path d="m292 230 25-12 20 8-25 13Z" fill="#5eead4"/><path d="m292 230 20 9v8l-20-9Zm20 9 25-13v8l-25 13Z" fill="#34aeb5"/>
        }
      }
      <g class="scene-sparks" fill="#bfd4ff"><circle cx="94" cy="84" r="3"/><circle cx="390" cy="69" r="4"/><circle cx="415" cy="219" r="3"/><path d="M354 28v12m-6-6h12" stroke="#5eead4" stroke-width="2"/></g>
    </svg>
  `,
  styles: [`
    :host { display: block; width: 100%; }
    svg { display: block; width: 100%; overflow: visible; }
    .moving .scene-main { animation: studio-float 6s ease-in-out infinite; }
    .moving .scene-satellite { animation: studio-float 7s ease-in-out infinite reverse; }
    .moving .scene-sparks { animation: studio-glow 4s ease-in-out infinite; }
    .moving .data-flow { animation: studio-flow 3s linear infinite; }
    .moving .scan-ring { transform-origin: 242px 133px; animation: studio-scan 24s linear infinite; }
    @keyframes studio-float { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
    @keyframes studio-glow { 0%,100% { opacity: .35; } 50% { opacity: 1; } }
    @keyframes studio-flow { to { stroke-dashoffset: -52; } }
    @keyframes studio-scan { to { transform: rotate(360deg); } }
    @media (prefers-reduced-motion:reduce) { * { animation: none !important; } }
  `],
})
export class OverviewArtComponent {
  private static nextId = 0;
  readonly id = 'overview-art-' + OverviewArtComponent.nextId++;
  @Input() subject = '';
  @Input() animated = false;
  get variant() {
    const subject = this.subject.toLowerCase();
    if (subject.includes('cloud') || subject.includes('devops')) return 'cloud';
    if (subject.includes('security') || subject.includes('cyber')) return 'security';
    if (subject.includes('data-science')) return 'data';
    if (subject.includes('machine-learning') || subject.includes('deep-learning') || subject.includes('ai-engineering')) return 'ai';
    return 'code';
  }
}

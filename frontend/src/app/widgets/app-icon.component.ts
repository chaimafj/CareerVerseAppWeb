import { Component, Input } from '@angular/core';

export type AppIcon = 'home' | 'compass' | 'book' | 'lab' | 'sparkles' | 'user' | 'bell' | 'crown' | 'shield' | 'logout' | 'sun' | 'moon';

const PATHS: Record<AppIcon, string> = {
  home: 'M3 10 12 3l9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z',
  compass: 'M16 8 14 14 8 16l2-6Z M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20',
  book: 'M12 5v16 M12 5C9 3 6 3 3 4v15c3-1 6-1 9 2 3-3 6-3 9-2V4c-3-1-6-1-9 1',
  lab: 'M9 3h6 M10 3v6L4 19c-.6 1 .1 2 1.3 2h13.4c1.2 0 1.9-1 1.3-2L14 9V3 M7 14h10 M10 17h.01 M14 18h.01',
  sparkles: 'm12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z M20 2v4 M18 4h4',
  user: 'M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M4 21v-2a8 6 0 0 1 16 0v2',
  bell: 'M18 8a6 6 0 0 0-12 0c0 8-3 8-3 10h18c0-2-3-2-3-10 M10 21h4',
  crown: 'm3 6 4 4 5-7 5 7 4-4-2 13H5Z M7 22h10',
  shield: 'm12 2 9 4v6c0 5-5 8-9 10-4-2-9-5-9-10V6Z m-4 10 3 3 5-6',
  logout: 'M9 3H4v18h5 M9 12h12 m-4-4 4 4-4 4',
  sun: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M12 2v2 M12 20v2 M2 12h2 M20 12h2 M5 5l1.5 1.5 M17.5 17.5 19 19 M5 19l1.5-1.5 M17.5 6.5 19 5',
  moon: 'M21 13a9 9 0 0 1-10-10A9 9 0 1 0 21 13',
};

@Component({
  selector: 'app-icon',
  standalone: true,
  host: {'aria-hidden': 'true'},
  template: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" focusable="false"><path [attr.d]="path" /></svg>`,
  styles: [`:host { display: inline-flex; width: 22px; height: 22px; flex-shrink: 0; vertical-align: middle; } svg { width: 100%; height: 100%; }`],
})
export class AppIconComponent {
  @Input() name: AppIcon = 'sparkles';
  get path() { return PATHS[this.name]; }
}

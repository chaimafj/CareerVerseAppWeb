import { Injectable, Pipe, PipeTransform, inject, signal } from '@angular/core';
import { TRANSLATIONS } from './translations';

export type Language = 'en' | 'fr' | 'ar';

@Injectable({providedIn: 'root'})
export class LocaleService {
  readonly language = signal<Language>(this.readLanguage());
  constructor() { this.apply(); }
  private readLanguage(): Language {
    const stored = localStorage.getItem('cv-web-language');
    return stored === 'fr' || stored === 'ar' ? stored : 'en';
  }
  setLanguage(value: string) {
    if (value !== 'en' && value !== 'fr' && value !== 'ar') throw new Error('Unsupported language');
    this.language.set(value);
    localStorage.setItem('cv-web-language', value);
    this.apply();
  }
  private apply() {
    document.documentElement.lang = this.language();
    document.documentElement.dir = this.language() === 'ar' ? 'rtl' : 'ltr';
  }
  t(value: unknown): string {
    const text = String(value ?? '');
    const language = this.language();
    const key=text.trim();
    return language === 'en' ? text : TRANSLATIONS[key]?.[language] ?? TRANSLATIONS[key.toLowerCase()]?.[language] ?? text;
  }
}

@Pipe({name:'t', standalone:true, pure:false})
export class TranslatePipe implements PipeTransform {
  private readonly locale = inject(LocaleService);
  transform(value: unknown): string { return this.locale.t(value); }
}

@Pipe({name:'localDate',standalone:true,pure:false})
export class LocalDatePipe implements PipeTransform {
  private readonly locale=inject(LocaleService);
  transform(value:string|null, style:'short'|'medium'|'mediumDate'='short'):string {
    if(!value)return '';
    const date=new Date(value);
    const options:Intl.DateTimeFormatOptions=style==='mediumDate'?{dateStyle:'medium'}:
      {dateStyle:style,timeStyle:style==='short'?'short':'medium'};
    return new Intl.DateTimeFormat(this.locale.language(),options).format(date);
  }
}

import { LocalDatePipe, TranslatePipe } from '../core/locale.service';
import { Component, OnInit, inject, signal } from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IonicModule } from '@ionic/angular';
import { AuthService } from '../core/auth.service';
import { ApiService, errorMessage } from '../core/api.service';
import { RouterLink } from '@angular/router';
import { CareerAssessment, Progress } from '../core/models';
import { CareerAssessmentComponent } from '../widgets/career-assessment.component';

@Component({
  standalone: true,
  imports: [TranslatePipe, LocalDatePipe, FormsModule, IonicModule, TitleCasePipe, RouterLink, CareerAssessmentComponent],
  template: `
    <div class="page-heading"><div><span class="eyebrow">{{ 'YOUR STORY STARTS WITH YOU' | t }}</span><h1>{{ 'My profile' | t }}</h1><p class="muted">{{ 'Help us understand your interests. Your matches will update as you learn.' | t }}</p></div></div>
    <section class="panel profile-hero">
      <div class="profile-photo">@if (auth.user()?.photo_url; as url) { <img [src]="url" [alt]="'Profile photo' | t"> } @else { <span>{{ auth.user()?.name?.slice(0,1)?.toUpperCase() }}</span> }</div>
      <div class="profile-identity"><h2>{{ auth.user()?.name }}</h2><p class="muted">{{ auth.user()?.email }}</p>
        <p>{{ auth.user()?.university }} @if (auth.user()?.specialty) { · {{ auth.user()?.specialty }} }</p>
        <h3>{{ 'Saved interests' | t }}</h3>
        <div class="tags">@for (interest of auth.user()?.interests ?? []; track interest) { <span>{{ (interest | titlecase) | t }}</span> } @empty { <p class="muted">{{ 'No interests saved yet.' | t }}</p> }</div>
        <label class="secondary-link photo-upload">{{ 'Upload profile photo' | t }}<input type="file" accept="image/jpeg,image/png,image/webp" [disabled]="photoBusy()" (change)="uploadPhoto($event)"></label>
        @if (auth.user()?.photo_url) { <button class="theme-button" [disabled]="photoBusy()" (click)="removePhoto()">{{ 'Remove photo' | t }}</button> }
        @if (photoBusy()) { <ion-spinner name="dots" /> }
        <p class="small muted">{{ 'JPEG, PNG or WebP · up to 5 MB · photo visible only to you.' | t }}</p>
      </div>
    </section>
    @if (summaryError()) { <div class="error" role="alert">{{ summaryError() | t }} <button (click)="loadSummary()">{{ 'Retry' | t }}</button></div> }
    @if (summaryLoading()) { <div class="loading"><ion-spinner /> {{ 'Loading your progress...' | t }}</div> }
    @if (progress(); as p) {
      <div class="metrics"><article class="metric"><span>{{ 'Labs completed' | t }}</span><strong>{{ p.completed_labs }} / {{ p.total_labs }}</strong></article>
      <article class="metric"><span>{{ 'Courses completed' | t }}</span><strong>{{ p.completed_courses }}</strong></article>
      <article class="metric"><span>{{ 'Average score' | t }}</span><strong>{{ p.results.length ? p.average_score + '%' : '—' }}</strong></article></div>
    }
    <div class="detail-grid"><section class="panel">
      @if (error()) { <div class="error" role="alert">{{ (error()) | t }}</div> }
      @if (saved()) { <div class="success-message" role="status">{{ 'Your profile has been updated.' | t }}</div> }
      <form #form="ngForm" class="form-stack" (ngSubmit)="save()">
        <label>{{ 'Full name' | t }}<input name="name" [(ngModel)]="name" required minlength="2" maxlength="150" autocomplete="name"></label>
        <label>{{ 'Email' | t }}<input [value]="auth.user()?.email" disabled type="email"><small class="muted">{{ 'Your account email cannot be changed here.' | t }}</small></label>
        <div class="form-grid"><label>{{ 'University' | t }}<input name="university" [(ngModel)]="university" maxlength="200"></label><label>{{ 'Specialty' | t }}<input name="specialty" [(ngModel)]="specialty" maxlength="200"></label></div>
        <label>{{ 'Study level' | t }}<select name="study_level" [(ngModel)]="studyLevel"><option value="">{{ 'Select a level' | t }}</option>@for (level of levels; track level) { <option [value]="level">{{ (level) | t }}</option> }</select></label>
        <label>{{ 'About you' | t }}<textarea name="bio" [(ngModel)]="bio" rows="4" maxlength="2000" [placeholder]=" 'What do you enjoy learning or building?' | t "></textarea></label>
        <fieldset><legend>{{ 'Your interests' | t }}</legend>@if (loadingInterests()) { <ion-spinner name="dots" /> }<div class="interest-grid">@for (interest of choices(); track interest) { <label class="interest-choice" [class.chosen]="interests.includes(interest)"><input type="checkbox" [checked]="interests.includes(interest)" [disabled]="saving()" (change)="toggle(interest)">{{ (interest | titlecase) | t }}</label> }</div>
          <label>{{ 'Custom interest' | t }}<input name="customInterest" [(ngModel)]="customInterest" maxlength="100" [disabled]="saving()" (keydown.enter)="$event.preventDefault(); addInterest()" [placeholder]="'For example: robotics' | t"></label>
          <button type="button" class="theme-button" [disabled]="saving()" (click)="addInterest()">{{ 'Add interest' | t }}</button>
          <p class="small muted">{{ 'Select up to 30 interests. Save profile to keep your changes.' | t }}</p>
          @if (interestError()) { <p class="error" role="alert">{{ interestError() | t }}</p> }
        </fieldset>
        <ion-button type="submit" [disabled]="form.invalid || saving() || photoBusy()">@if (saving()) { <ion-spinner name="dots" /> } @else { {{ 'Save profile' | t }} } </ion-button>
      </form>
    </section><aside><section class="panel fact-panel"><h2>{{ 'Your access' | t }}</h2>
      @if (billing(); as status) {
        <span class="pill" [class.success]="status.is_premium">{{ (status.is_premium ? 'Premium is active!' : 'Free account') | t }}</span>
        @if (status.is_premium && status.premium_until) { <p>{{ 'Access until' | t }} {{ status.premium_until | localDate }}</p> }
        <a class="secondary-link" routerLink="/premium">{{ 'Manage Premium →' | t }}</a>
      }
    </section><section class="panel fact-panel"><span class="eyebrow">{{ 'WHY IT MATTERS' | t }}</span><h2>{{ 'Better context.' | t }}<br>{{ 'Better direction.' | t }}</h2><p class="body-copy">{{ 'Your selected interests contribute to your career matches. Lab performance makes those matches more meaningful.' | t }}</p><p class="muted">{{ 'No interest defines your limits. Explore a role outside your comfort zone, too.' | t }}</p></section></aside></div>
    <section class="profile-assessments"><h2>{{ 'Your progress by career' | t }}</h2>
      @for (assessment of assessments(); track assessment.career_slug) { <app-career-assessment [assessment]="assessment" /> }
    </section>
  `,
})
export class ProfilePage implements OnInit {
  readonly auth = inject(AuthService);
  private readonly api = inject(ApiService);
  readonly saving = signal(false);
  readonly saved = signal(false);
  readonly error = signal('');
  readonly interestError = signal('');
  customInterest = '';
  readonly photoBusy = signal(false);
  readonly summaryLoading = signal(true);
  readonly summaryError = signal('');
  readonly progress = signal<Progress | null>(null);
  readonly assessments = signal<CareerAssessment[]>([]);
  readonly billing = signal<{is_premium: boolean; premium_until: string | null} | null>(null);
  private readonly initial = this.auth.user();
  name = this.initial?.name ?? '';
  university = this.initial?.university ?? '';
  specialty = this.initial?.specialty ?? '';
  studyLevel = this.initial?.study_level ?? '';
  bio = this.initial?.bio ?? '';
  interests = [...new Set((this.initial?.interests ?? []).map(value => value.trim().toLowerCase()))];
  readonly levels = ['High school','Bac+1','Bac+2','Bac+3','Bac+4','Bac+5','Graduate'];
  readonly choices = signal<string[]>([...this.interests]);
  readonly loadingInterests = signal(true);
  ngOnInit() { void this.loadInterests(); void this.loadSummary(); }
  async loadSummary() {
    this.summaryLoading.set(true); this.summaryError.set('');
    try {
      const [progress, assessments, billing] = await Promise.all([
        this.api.progress(), this.api.assessments(),
        this.api.get<{is_premium: boolean; premium_until: string | null}>('billing/status/'),
      ]);
      this.progress.set(progress); this.assessments.set(assessments); this.billing.set(billing);
    } catch (error) { this.summaryError.set(errorMessage(error)); }
    finally { this.summaryLoading.set(false); }
  }
  async uploadPhoto(event: Event) {
    if (!(event.target instanceof HTMLInputElement)) return;
    const file = event.target.files?.[0]; event.target.value = '';
    if (!file || this.photoBusy() || this.saving()) return;
    this.error.set(''); this.saved.set(false);
    if (!['image/jpeg','image/png','image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024) {
      this.error.set('Choose a JPEG, PNG or WebP image up to 5 MB.'); return;
    }
    this.photoBusy.set(true);
    try { await this.auth.uploadPhoto(file); this.saved.set(true); }
    catch (error) { this.error.set(errorMessage(error)); }
    finally { this.photoBusy.set(false); }
  }
  async removePhoto() {
    if (this.photoBusy() || this.saving()) return;
    this.photoBusy.set(true); this.error.set(''); this.saved.set(false);
    try { await this.auth.removePhoto(); this.saved.set(true); }
    catch (error) { this.error.set(errorMessage(error)); }
    finally { this.photoBusy.set(false); }
  }
  async loadInterests() {
    this.loadingInterests.set(true);
    try {
      const careers = await this.api.careers();
      this.choices.set([...new Set([...this.choices(),...this.interests,...careers.flatMap(c => c.interests).map(value => value.trim().toLowerCase())])].sort());
    } catch (error) { this.error.set(errorMessage(error)); }
    finally { this.loadingInterests.set(false); }
  }
  toggle(interest: string) {
    this.interestError.set('');
    if (!this.interests.includes(interest) && this.interests.length >= 30) {
      this.interestError.set('You can select up to 30 interests.'); return;
    }
    this.interests = this.interests.includes(interest) ? this.interests.filter(i => i !== interest) : [...this.interests,interest];
    this.saved.set(false);
  }
  addInterest(): boolean {
    const interest = this.customInterest.trim().toLowerCase();
    this.interestError.set('');
    if (!interest || interest.length > 100) {
      this.interestError.set('Enter an interest between 1 and 100 characters.'); return false;
    }
    if (!this.interests.includes(interest) && this.interests.length >= 30) {
      this.interestError.set('You can select up to 30 interests.'); return false;
    }
    this.choices.set([...new Set([...this.choices(),interest])].sort());
    this.interests = [...new Set([...this.interests,interest])];
    this.customInterest = ''; this.saved.set(false);
    return true;
  }
  async save() {
    if (this.saving() || this.photoBusy()) return;
    if (this.customInterest.trim() && !this.addInterest()) return;
    this.saving.set(true); this.saved.set(false); this.error.set('');
    try {
      await this.auth.saveProfile({name:this.name.trim(),university:this.university.trim(),specialty:this.specialty.trim(),study_level:this.studyLevel,bio:this.bio.trim(),interests:this.interests});
      this.interests = [...(this.auth.user()?.interests ?? [])];
      this.saved.set(true);
    } catch (error) { this.error.set(errorMessage(error)); }
    finally { this.saving.set(false); }
  }
}

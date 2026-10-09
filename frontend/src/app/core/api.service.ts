import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { Attempt, Career, CareerAssessment, ChatExchange, Course, CourseSummary, LabDetail, LabSummary, Match, Progress, Result, User } from './models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  get<T>(path: string): Promise<T> {
    return firstValueFrom(this.http.get<T>(`/api/${path}`));
  }
  post<T>(path: string, body: unknown = {}, headers?: Record<string, string>): Promise<T> {
    return firstValueFrom(this.http.post<T>(`/api/${path}`, body, {headers}));
  }
  patch<T>(path: string, body: unknown): Promise<T> {
    return firstValueFrom(this.http.patch<T>(`/api/${path}`, body));
  }
  delete(path: string, body: unknown): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`/api/${path}`, {body}));
  }
  csrf() { return this.get<unknown>('csrf/'); }
  me() { return this.get<User>('me/'); }
  careers() { return this.get<Career[]>('careers/'); }
  career(slug: string) { return this.get<Career>(`careers/${encodeURIComponent(slug)}/`); }
  course(id: number) { return this.get<Course>(`courses/${id}/`); }
  courses() { return this.get<CourseSummary[]>('courses/'); }
  labs() { return this.get<LabSummary[]>('labs/'); }
  assessments() { return this.get<CareerAssessment[]>('career-assessments/'); }
  assessment(slug: string) { return this.get<CareerAssessment>(`careers/${encodeURIComponent(slug)}/assessment/`); }
  completeCourse(id: number) { return this.post<unknown>(`courses/${id}/complete/`); }
  startLab(id: number) { return this.post<Attempt>(`labs/${id}/start/`); }
  lab(id: number) { return this.get<LabDetail>(`labs/${id}/`); }
  submit(id: number, answers: {question_id: number; option_ids: number[]; code_text?: string}[]) {
    return this.post<Result>(`attempts/${id}/submit/`, { answers });
  }
  result(id: number) { return this.get<Result>(`results/${id}/`); }
  progress() { return this.get<Progress>('progress/'); }
  recommendations() { return this.get<Match[]>('recommendations/'); }
  chatHistory() { return this.get<ChatExchange[]>('chat/'); }
  sendChat(message: string) { return this.post<ChatExchange>('chat/', {message}); }
  clearChat() { return firstValueFrom(this.http.delete<void>('/api/chat/')); }
}

export function errorMessage(error: unknown): string {
  if (error instanceof HttpErrorResponse) {
    if (error.status === 0) return 'The server is unreachable. Check your connection and retry.';
    const body: unknown = error.error;
    if (error.status === 403 && typeof body === 'object' && body !== null &&
        'code' in body && body.code === 'premium_required') {
      return 'Active Premium access is required for this lab and its course.';
    }
    if (error.status === 401 || error.status === 403) {
      return 'Your session or permissions could not be verified. Sign in again and retry.';
    }
    if (typeof body === 'object' && body !== null) {
      const messages = Object.values(body).flatMap(value =>
        typeof value === 'string' ? [value] :
        Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
      );
      if (messages.length) return messages.join(' ');
    }
    return `Request failed (${error.status}). Please retry.`;
  }
  return error instanceof Error ? error.message : 'An unexpected error occurred. Please retry.';
}

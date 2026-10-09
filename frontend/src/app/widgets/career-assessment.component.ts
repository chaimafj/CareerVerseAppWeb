import { Component, Input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { CareerAssessment } from '../core/models';
import { TranslatePipe } from '../core/locale.service';

@Component({
  selector: 'app-career-assessment',
  standalone: true,
  imports: [RouterLink, TranslatePipe],
  template: `
    <section class="panel career-assessment" [class.improvement-needed]="assessment.needs_improvement">
      <h3>{{ 'Career assessment' | t }} · {{ assessment.career_title }}</h3>
      <p class="muted">{{ 'Based on the best score in each free lab. Premium is optional.' | t }}</p>
      @if (assessment.complete) {
        <p class="assessment-score">{{ 'Final score' | t }}: <strong>{{ assessment.final_score }}%</strong></p>
        @if (assessment.needs_improvement) {
          <p role="status">{{ 'Your score is below 60%. Strengthen your skills in this career with the learning path below.' | t }}</p>
          <h4>{{ 'Your improvement learning path' | t }}</h4>
          <p class="muted">{{ 'Start with your weakest areas: review corrections, study the course, then retake the lab.' | t }}</p>
          <ol>
            @for (step of assessment.learning_path; track step.lab_id) {
              <li class="assessment-step">
                <strong>{{ step.lab_title }}</strong> · {{ '· Best:' | t }} {{ step.best_score }}%
                @if (step.weak_skills.length) { <p>{{ 'Skills to strengthen' | t }}: {{ step.weak_skills.join(', ') }}</p> }
                <div class="step-actions">
                  <a class="secondary-link" [routerLink]="['/results',step.result_id]">{{ 'View result & corrections →' | t }}</a>
                  @if (step.course_id !== null) {
                    <a class="secondary-link" [routerLink]="['/courses',step.course_id]">{{ (step.course_completed ? 'Review course' : 'Read course') | t }} · {{ step.course_title }}</a>
                  }
                  <a class="button-link compact retake-button" [routerLink]="['/labs',step.lab_id]">{{ 'Retake lab →' | t }}</a>
                </div>
              </li>
            }
          </ol>
        } @else {
          <p>{{ 'You have reached the 60% career assessment target. Keep practicing to progress further.' | t }}</p>
        }
      } @else {
        <p>{{ assessment.completed_labs }} / {{ assessment.required_labs }} {{ 'free labs completed' | t }}</p>
        <p class="muted">{{ 'Complete every free lab in this career to unlock your final assessment.' | t }}</p>
      }
    </section>
  `,
})
export class CareerAssessmentComponent {
  @Input({required: true}) assessment!: CareerAssessment;
}

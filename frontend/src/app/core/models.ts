export interface User {
  id: number;
  email: string;
  name: string;
  interests: string[];
  university: string;
  specialty: string;
  study_level: string;
  bio: string;
  is_staff: boolean;
  photo_url: string | null;
}

export interface Career {
  slug: string;
  title: string;
  summary: string;
  description: string;
  category: string;
  tools: string[];
  interests: string[];
  salary: string;
  education: string;
  outlook: string;
  courses?: CourseLink[];
  labs?: LabLink[];
  assessment?: CareerAssessment;
}

export interface CareerAssessment {
  career_slug: string; career_title: string; completed_labs: number; required_labs: number;
  complete: boolean; final_score: number | null; needs_improvement: boolean;
  learning_path: {
    lab_id: number; lab_title: string; best_score: number; result_id: number;
    weak_skills: string[]; course_id: number | null; course_title: string | null; course_completed: boolean;
  }[];
}

export interface CourseLink {
  id: number;
  title: string;
  completed: boolean;
  lab_id: number;
  is_premium: boolean;
  locked: boolean;
}

export interface LabResultSummary {
  id: number; score: number; passed: boolean; correct: number; total: number; completed_at: string;
}

export interface LabCompletion {
  completed: boolean;
  attempt_count: number;
  latest_result: LabResultSummary | null;
}

export interface CourseSummary {
  id: number; title: string; career_slug: string; career_title: string;
  completed: boolean; is_premium: boolean; locked: boolean;
}

export interface LabSummary extends LabCompletion {
  id: number; title: string; career_slug: string; career_title: string; level: string;
  scenario: string; question_count: number; expected_seconds: number;
  is_premium: boolean; locked: boolean;
}

export interface LabLink extends LabCompletion {
  id: number;
  title: string;
  level: string;
  question_count: number;
  best_score: number | null;
  is_premium: boolean;
  locked: boolean;
  scenario: string;
  objectives: string[];
  expected_seconds: number;
}

export interface LabDetail extends LabCompletion {
  id: number; title: string; career_title: string; career_slug: string; level: string;
  is_premium: boolean; locked: boolean; scenario: string; objectives: string[];
  expected_seconds: number; question_count: number;
  results: LabResultSummary[];
}

export interface Course {
  id: number;
  title: string;
  intro: string;
  career_slug: string;
  lab_id: number;
  lessons: {title: string; body: string; example: string}[];
  completed: boolean;
}

export interface Question {
  id: number;
  prompt: string;
  multiple: boolean;
  options: {id: number; text: string}[];
  kind?: 'quiz' | 'code' | 'architecture' | 'evidence';
  workspace?: WorkshopWorkspace;
}

export interface WorkshopWorkspace {
  before?: string;
  after?: string;
  nodes?: string[];
  gap?: number;
  context?: string;
}

export interface Attempt {
  id: number;
  lab_title: string;
  career_title: string;
  questions: Question[];
  expected_seconds: number;
  scenario: string;
  objectives: string[];
  is_premium: boolean;
}

export interface Result {
  id: number;
  lab_id: number | null;
  career_title: string;
  career_slug: string;
  lab_title: string;
  correct: number;
  total: number;
  score: number;
  time_score: number;
  duration_seconds: number;
  passed: boolean;
  skills: Record<string, number>;
  feedback: {prompt: string; correct: boolean; explanation: string; selected_options?: string[]; correct_options?: string[];
    kind?: Question['kind']; workspace?: WorkshopWorkspace}[];
}

export interface Progress {
  completed_labs: number;
  total_labs: number;
  average_score: number | null;
  completed_courses: number;
  results: {id: number; career_title: string; lab_title: string; score: number; completed_at: string}[];
}

export interface Match {
  career_slug: string;
  career_title: string;
  score: number;
  tested: boolean;
  performance: number | null;
  shared_interests: string[];
}

export interface ChatExchange {
  id: number;
  message: string;
  reply: string;
  actions: {label: string; path: string}[];
  created_at: string;
}

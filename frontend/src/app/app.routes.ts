import { Routes } from '@angular/router';
import { authGuard } from './core/auth.service';
import { AuthPage } from './pages/auth.page';
import { DashboardPage } from './pages/dashboard.page';
import { CareersPage, CareerPage } from './pages/careers.page';
import { CoursePage } from './pages/course.page';
import { LabPage, ResultPage, leaveLabGuard } from './pages/lab.page';
import { RecommendationsPage } from './pages/recommendations.page';
import { ProfilePage } from './pages/profile.page';
import { ChatPage } from './pages/chat.page';
import { NotificationsPage } from './pages/notifications.page';
import { PremiumPage } from './pages/premium.page';
import { LearningCatalogPage } from './pages/learning-catalog.page';
import { PasswordResetPage } from './pages/password-reset.page';

export const routes: Routes = [
  {path: 'login', component: AuthPage},
  {path: 'register', component: AuthPage},
  {path: 'forgot-password', component: PasswordResetPage},
  {path: 'reset-password/:uid/:token', component: PasswordResetPage},
  {path: '', component: DashboardPage, canActivate: [authGuard]},
  {path: 'careers', component: CareersPage, canActivate: [authGuard]},
  {path: 'careers/:slug', component: CareerPage, canActivate: [authGuard]},
  {path: 'courses/:id', component: CoursePage, canActivate: [authGuard]},
  {path: 'courses', component: LearningCatalogPage, data: {catalog: 'courses'}, canActivate: [authGuard]},
  {path: 'labs', component: LearningCatalogPage, data: {catalog: 'labs'}, canActivate: [authGuard]},
  {path: 'labs/:id', component: LabPage, canActivate: [authGuard], canDeactivate: [leaveLabGuard]},
  {path: 'results/:id', component: ResultPage, canActivate: [authGuard]},
  {path: 'recommendations', component: RecommendationsPage, canActivate: [authGuard]},
  {path: 'profile', component: ProfilePage, canActivate: [authGuard]},
  {path: 'chat', component: ChatPage, canActivate: [authGuard]},
  {path: 'notifications', component: NotificationsPage, canActivate: [authGuard]},
  {path: 'premium', component: PremiumPage, canActivate: [authGuard]},
  {path: '**', redirectTo: ''}
];

import { bootstrapApplication } from '@angular/platform-browser';
import { provideHttpClient, withXsrfConfiguration } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { provideIonicAngular } from '@ionic/angular/standalone';
import { AppComponent } from './app/app.component';
import { routes } from './app/app.routes';

bootstrapApplication(AppComponent, {
  providers: [
    provideIonicAngular(),
    provideHttpClient(withXsrfConfiguration({
      cookieName: 'csrftoken',
      headerName: 'X-CSRFToken',
    })),
    provideRouter(routes),
  ],
}).catch(error => console.error('CareerVerse could not start:', error));

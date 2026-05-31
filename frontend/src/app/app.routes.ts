import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'onboarding/generate',
  },
  {
    path: 'onboarding/generate',
    loadChildren: () =>
      import('./features/onboarding/generate-plan/generate-plan.routes').then(
        (m) => m.generatePlanRoutes,
      ),
  },
  {
    path: '**',
    redirectTo: 'onboarding/generate',
  },
];

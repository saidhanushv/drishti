import { Routes } from '@angular/router';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { HomePageComponent } from './components/home-page/home-page.component';
import { DetailsPageComponent } from './components/dashboard/details-page/details-page.component';
import { GanttPageComponent } from './components/dashboard/gantt-page/gantt-page.component';
import { RagStatusPageComponent } from './components/dashboard/rag-status-page/rag-status-page.component';
import { AnalyticsPageComponent } from './components/dashboard/analytics-page/analytics-page.component';

export const routes: Routes = [
    {
        path: '',
        component: HomePageComponent,
        pathMatch: 'full'
    },
    {
        path: 'dashboard',
        component: DashboardComponent,
        children: [
            {
                path: 'details',
                component: DetailsPageComponent
            },
            {
                path: 'gantt',
                component: GanttPageComponent
            },
            {
                path: 'rag-status',
                component: RagStatusPageComponent
            },
            {
                path: 'analytics',
                component: AnalyticsPageComponent
            },
            {
                path: '',
                redirectTo: 'details',
                pathMatch: 'full'
            }
        ]
    }
];


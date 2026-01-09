import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css'
})
export class DashboardComponent {
  activeTabIndex = 0;

  tabs = [
    { label: 'Analysis View', route: 'details', icon: '📊' },
    { label: 'Gantt Chart', route: 'gantt', icon: '📅' },
    { label: 'RAG Status', route: 'rag-status', icon: '🚦' },
    { label: 'Analytics', route: 'analytics', icon: '📈' }
  ];

  constructor(private router: Router) { }

  selectTab(index: number): void {
    this.activeTabIndex = index;
    this.router.navigate(['/dashboard', this.tabs[index].route]);
  }
}



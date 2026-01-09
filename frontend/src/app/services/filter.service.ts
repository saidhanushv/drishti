import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { DashboardFilters } from '../models/filter.model';

@Injectable({
  providedIn: 'root'
})
export class FilterService {
  private filtersSubject = new BehaviorSubject<DashboardFilters>({});
  public filters$ = this.filtersSubject.asObservable();

  constructor() { }

  /**
   * Get current filters
   */
  getCurrentFilters(): DashboardFilters {
    return this.filtersSubject.value;
  }

  /**
   * Update filters
   */
  updateFilters(filters: Partial<DashboardFilters>): void {
    const currentFilters = this.filtersSubject.value;
    const newFilters = { ...currentFilters, ...filters };
    this.filtersSubject.next(newFilters);
  }

  /**
   * Reset all filters
   */
  resetFilters(): void {
    this.filtersSubject.next({});
  }

  /**
   * Reset specific filter
   */
  resetFilter(filterKey: keyof DashboardFilters): void {
    const currentFilters = { ...this.filtersSubject.value };
    delete currentFilters[filterKey];
    this.filtersSubject.next(currentFilters);
  }

  /**
   * Set filters from LLM response
   */
  setFiltersFromLLM(filters: DashboardFilters): void {
    this.filtersSubject.next(filters);
  }
}

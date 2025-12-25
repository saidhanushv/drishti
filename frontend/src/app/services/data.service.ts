import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, map } from 'rxjs';
import { Promotion } from '../models/promotion.model';
import { DashboardFilters } from '../models/filter.model';

@Injectable({
  providedIn: 'root'
})
export class DataService {
  private promotionsSubject = new BehaviorSubject<Promotion[]>([]);
  public promotions$ = this.promotionsSubject.asObservable();

  constructor(private http: HttpClient) {
    this.loadPromotionsFromCSV();
  }

  /**
   * Load promotions from CSV file
   */
  private loadPromotionsFromCSV(): void {
    // Load from backend API (dynamically served from ADLS/local storage)
    this.http.get('http://localhost:8000/data/csv', { responseType: 'text' }).subscribe({
      next: (csvText) => {
        console.log('CSV loaded, size:', csvText.length);
        const promotions = this.parseCSV(csvText);
        this.promotionsSubject.next(promotions);
      },
      error: (error) => {
        console.error('Error loading CSV:', error);
        this.promotionsSubject.next([]);
      }
    });
  }

  /**
   * Parse CSV text into Promotion objects
   */
  private parseCSV(csvText: string): Promotion[] {
    // Split by newline, handling both \r\n and \n
    const lines = csvText.split(/\r?\n/).filter(line => line.trim());
    if (lines.length < 2) {
      console.error('CSV has less than 2 lines');
      return [];
    }

    const headers = this.parseCSVLine(lines[0]);
    const promotions: Promotion[] = [];

    console.log(`Parsing CSV with ${lines.length - 1} data rows`);
    console.log(`Found ${headers.length} columns`);

    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;

      try {
        const values = this.parseCSVLine(line);

        const promotion: any = {};
        headers.forEach((header, index) => {
          const value = values[index] || '';
          promotion[header] = this.convertValue(value);
        });

        promotions.push(promotion as Promotion);
      } catch (error) {
        if (i < 5) { // Only log first few errors
          console.warn(`Error parsing line ${i}:`, error);
        }
      }
    }

    console.log(`Successfully parsed ${promotions.length} promotions from CSV`);
    if (promotions.length > 0) {
      console.log('Sample promotion:', promotions[0]);
    }
    return promotions;
  }

  /**
   * Parse a CSV line handling quoted values
   */
  private parseCSVLine(line: string): string[] {
    const result: string[] = [];
    let current = '';
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
      const char = line[i];

      if (char === '"') {
        inQuotes = !inQuotes;
      } else if (char === ',' && !inQuotes) {
        result.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }

    result.push(current.trim());
    return result;
  }

  /**
   * Convert string value to appropriate type
   */
  private convertValue(value: string): any {
    if (!value || value === 'null' || value === 'NULL' || value === '') return null;

    // Try to parse as number
    const num = parseFloat(value);
    if (!isNaN(num) && value.match(/^-?\d+\.?\d*$/)) {
      return num;
    }

    return value;
  }

  /**
   * Get all promotions
   */
  getAllPromotions(): Observable<Promotion[]> {
    return this.promotions$;
  }

  /**
   * Get filtered promotions
   */
  getFilteredPromotions(filters: DashboardFilters): Observable<Promotion[]> {
    return this.promotions$.pipe(
      map(promotions => {
        return promotions.filter(promo => {
          if (filters.year && promo.Promo_Year !== filters.year) return false;
          if (filters.region && filters.region.length > 0 && !filters.region.includes(promo.Region)) return false;
          if (filters.country && filters.country.length > 0 && !filters.country.includes(promo.Country)) return false;
          if (filters.category && filters.category.length > 0 && !filters.category.includes(promo.Category)) return false;
          if (filters.brand && filters.brand.length > 0 && !filters.brand.includes(promo.Brand)) return false;
          if (filters.promotionStatus && filters.promotionStatus.length > 0 && !filters.promotionStatus.includes(promo.Promotion_Status)) return false;
          if (filters.ragStatus && filters.ragStatus.length > 0 && !filters.ragStatus.includes(promo.Actual_RAG)) return false;
          return true;
        });
      })
    );
  }

  /**
   * Get unique values for filter dropdowns
   */
  getUniqueRegions(): string[] {
    const promotions = this.promotionsSubject.value;
    return [...new Set(promotions.map(p => p.Region))].filter(r => r).sort();
  }

  getUniqueCountries(): string[] {
    const promotions = this.promotionsSubject.value;
    return [...new Set(promotions.map(p => p.Country))].filter(c => c).sort();
  }

  getUniqueChannels(): string[] {
    const promotions = this.promotionsSubject.value;
    return [...new Set(promotions.map(p => p.Channel_Customer))].filter(c => c).sort();
  }

  getUniqueCategories(): string[] {
    const promotions = this.promotionsSubject.value;
    return [...new Set(promotions.map(p => p.Category))].filter(c => c).sort();
  }

  getUniqueBrands(): string[] {
    const promotions = this.promotionsSubject.value;
    return [...new Set(promotions.map(p => p.Brand))].filter(b => b).sort();
  }

  /**
   * Refresh data
   */
  refreshData(): void {
    this.loadPromotionsFromCSV();
  }
}

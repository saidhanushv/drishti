import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { NavigationInstruction, DashboardFilters } from '../models/filter.model';
import { FilterService } from './filter.service';

@Injectable({
  providedIn: 'root'
})
export class LlmParserService {
  // Keywords for page detection
  private pageKeywords = {
    'details': ['details', 'table', 'list', 'all promotions', 'show me'],
    'gantt': ['gantt', 'timeline', 'schedule', 'when', 'dates'],
    'rag-status': ['rag', 'red', 'amber', 'green', 'status', 'performance'],
    'analytics': ['top', 'analytics', 'profit', 'roi', 'revenue', 'sales', 'turnover']
  };

  // Keywords for filters
  private filterKeywords = {
    region: ['SEA', 'Europe', 'Asia', 'Americas', 'region'],
    ragStatus: ['red', 'amber', 'green'],
    promotionStatus: ['completed', 'ongoing', 'planned'],
    year: ['2024', '2025', 'previous year', 'current year', 'last year', 'this year']
  };

  constructor(
    private router: Router,
    private filterService: FilterService
  ) { }

  /**
   * Parse natural language query and extract navigation instructions
   */
  parseQuery(query: string): NavigationInstruction | null {
    const lowerQuery = query.toLowerCase();

    // Detect target page
    const targetPage = this.detectTargetPage(lowerQuery);
    if (!targetPage) {
      return null;
    }

    // Extract filters
    const filters = this.extractFilters(lowerQuery);

    // Extract limit (e.g., "top 10")
    const limit = this.extractLimit(lowerQuery);

    // Extract sort order
    const sortOrder = this.extractSortOrder(lowerQuery);

    return {
      targetPage,
      filters,
      limit,
      sortOrder
    };
  }

  /**
   * Detect which dashboard page the query is about
   */
  private detectTargetPage(query: string): 'details' | 'gantt' | 'rag-status' | 'analytics' | null {
    for (const [page, keywords] of Object.entries(this.pageKeywords)) {
      if (keywords.some(keyword => query.includes(keyword))) {
        return page as any;
      }
    }
    return null;
  }

  /**
   * Extract filters from query
   */
  private extractFilters(query: string): DashboardFilters {
    const filters: DashboardFilters = {};

    // Extract region
    if (query.includes('sea')) {
      filters.region = ['SEA'];
    } else if (query.includes('europe')) {
      filters.region = ['Europe'];
    } else if (query.includes('asia')) {
      filters.region = ['Asia'];
    }

    // Extract RAG status
    if (query.includes('green')) {
      filters.ragStatus = ['GREEN'];
    } else if (query.includes('red')) {
      filters.ragStatus = ['RED'];
    } else if (query.includes('amber')) {
      filters.ragStatus = ['AMBER'];
    }

    // Extract promotion status
    if (query.includes('completed')) {
      filters.promotionStatus = ['COMPLETED'];
    } else if (query.includes('ongoing')) {
      filters.promotionStatus = ['ONGOING'];
    } else if (query.includes('planned')) {
      filters.promotionStatus = ['PLANNED'];
    }

    // Extract year
    if (query.includes('2024') || query.includes('previous year') || query.includes('last year')) {
      filters.year = 2024;
    } else if (query.includes('2025') || query.includes('current year') || query.includes('this year')) {
      filters.year = 2025;
    }

    // Extract category
    const categoryMatch = query.match(/category\s+(\w+)/i);
    if (categoryMatch) {
      filters.category = [categoryMatch[1]];
    }

    // Extract brand
    const brandMatch = query.match(/brand\s+(\w+)/i);
    if (brandMatch) {
      filters.brand = [brandMatch[1]];
    }

    // Extract channel
    const channelMatch = query.match(/channel\s+(\w+)/i);
    if (channelMatch) {
      filters.channel = [channelMatch[1]];
    }

    // Extract Half Year (H1/H2)
    if (query.includes('h2') || query.includes('second half') || query.includes('2nd half')) {
      filters.halfYear = 'H2';
    } else if (query.includes('h1') || query.includes('first half') || query.includes('1st half')) {
      filters.halfYear = 'H1';
    }

    return filters;
  }

  /**
   * Extract limit from query (e.g., "top 10")
   */
  private extractLimit(query: string): number | undefined {
    const limitMatch = query.match(/top\s+(\d+)/i);
    if (limitMatch) {
      return parseInt(limitMatch[1], 10);
    }
    return undefined;
  }

  /**
   * Extract sort order from query
   */
  private extractSortOrder(query: string): 'asc' | 'desc' | undefined {
    if (query.includes('highest') || query.includes('top') || query.includes('best')) {
      return 'desc';
    } else if (query.includes('lowest') || query.includes('worst')) {
      return 'asc';
    }
    return undefined;
  }

  /**
   * Apply navigation instruction
   */
  applyNavigationInstruction(instruction: NavigationInstruction): void {
    // Apply filters
    if (instruction.filters) {
      this.filterService.setFiltersFromLLM(instruction.filters);
    }

    // Navigate to target page
    this.router.navigate(['/dashboard', instruction.targetPage]);
  }

  /**
   * Parse and apply query in one step
   */
  parseAndApply(query: string): boolean {
    const instruction = this.parseQuery(query);
    if (instruction) {
      this.applyNavigationInstruction(instruction);
      return true;
    }
    return false;
  }
}

export interface DashboardFilters {
    startDate?: string;
    endDate?: string;
    region?: string[];
    country?: string[];
    channel?: string[];
    category?: string[];
    brand?: string[];
    promotionStatus?: string[];
    ragStatus?: string[];
    year?: number;
    halfYear?: string; // H1 or H2
}

export interface NavigationInstruction {
    targetPage: 'details' | 'gantt' | 'rag-status' | 'analytics';
    filters?: DashboardFilters;
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
    limit?: number;
}

export interface LLMResponse {
    answer: string;
    navigation?: NavigationInstruction;
}

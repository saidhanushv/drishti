import { Component, OnInit, OnDestroy } from '@angular/core';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AgGridAngular } from 'ag-grid-angular';
import { ColDef, GridOptions, ModuleRegistry, GridApi } from 'ag-grid-community';
import { AllCommunityModule } from 'ag-grid-community';
import { Promotion } from '../../../models/promotion.model';
import { DataService } from '../../../services/data.service';
import { FilterService } from '../../../services/filter.service';

// Register AG Grid modules
ModuleRegistry.registerModules([AllCommunityModule]);

@Component({
  selector: 'app-details-page',
  standalone: true,
  imports: [CommonModule, AgGridAngular, FormsModule],
  templateUrl: './details-page.component.html',
  styleUrl: './details-page.component.css'
})
export class DetailsPageComponent implements OnInit, OnDestroy {
  rowData: Promotion[] = [];
  allPromotions: Promotion[] = [];
  totalRecords = 0;
  private gridApi!: GridApi;

  // Filter state
  filters = {
    region: '',
    customer: '',
    product: '',
    status: '',
    year: '',
    ragStatus: ''
  };

  // Available filter options
  availableRegions: string[] = [];
  availableCustomers: string[] = [];
  availableProducts: string[] = [];
  availableYears: number[] = [];

  // KPIs
  kpis = {
    totalPromotions: 0,
    totalSalesValue: 0,
    totalGrossProfit: 0,
    averageROI: 0
  };

  private destroy$ = new Subject<void>();

  columnDefs: ColDef[] = [
    { field: 'PromoID', headerName: 'Promo ID', filter: 'agTextColumnFilter', pinned: 'left', width: 150 },
    { field: 'Promo_Year', headerName: 'Year', filter: 'agNumberColumnFilter', width: 100 },
    { field: 'Region', headerName: 'Region', filter: 'agTextColumnFilter', width: 120 },
    { field: 'Country', headerName: 'Country', filter: 'agTextColumnFilter', width: 120 },
    { field: 'Category', headerName: 'Category', filter: 'agTextColumnFilter', width: 130 },
    { field: 'Brand', headerName: 'Brand', filter: 'agTextColumnFilter', width: 120 },
    { field: 'Channel_Customer', headerName: 'Channel', filter: 'agTextColumnFilter', width: 150 },
    { field: 'Promotion', headerName: 'Promotion Type', filter: 'agTextColumnFilter', width: 150 },
    {
      field: 'Promotion_Status', headerName: 'Status', filter: 'agTextColumnFilter', width: 130,
      cellStyle: (params) => {
        if (params.value === 'COMPLETED') return { backgroundColor: '#d4edda', color: '#155724' };
        if (params.value === 'ONGOING') return { backgroundColor: '#fff3cd', color: '#856404' };
        if (params.value === 'PLANNED') return { backgroundColor: '#d1ecf1', color: '#0c5460' };
        return null;
      }
    },
    { field: 'Start_Prom', headerName: 'Start Date', filter: 'agDateColumnFilter', width: 130 },
    { field: 'End_Prom', headerName: 'End Date', filter: 'agDateColumnFilter', width: 130 },
    {
      field: 'Sales_Value', headerName: 'Sales Value', filter: 'agNumberColumnFilter', width: 140,
      valueFormatter: (params) => params.value ? `$${params.value.toFixed(2)}` : ''
    },
    {
      field: 'Gross_Profit', headerName: 'Gross Profit', filter: 'agNumberColumnFilter', width: 140,
      valueFormatter: (params) => params.value ? `$${params.value.toFixed(2)}` : ''
    },
    {
      field: 'ROI%', headerName: 'ROI %', filter: 'agNumberColumnFilter', width: 120,
      valueFormatter: (params) => params.value ? `${params.value.toFixed(2)}%` : ''
    },
    {
      field: 'Actual_RAG', headerName: 'Actual RAG', filter: 'agTextColumnFilter', width: 130,
      cellStyle: (params) => {
        if (params.value === 'GREEN') return { backgroundColor: '#28a745', color: 'white', fontWeight: 'bold' };
        if (params.value === 'AMBER') return { backgroundColor: '#ffc107', color: 'black', fontWeight: 'bold' };
        if (params.value === 'RED') return { backgroundColor: '#dc3545', color: 'white', fontWeight: 'bold' };
        return null;
      }
    },
    {
      field: 'Planned_RAG', headerName: 'Planned RAG', filter: 'agTextColumnFilter', width: 130,
      cellStyle: (params) => {
        if (params.value === 'GREEN') return { backgroundColor: '#28a745', color: 'white', fontWeight: 'bold' };
        if (params.value === 'AMBER') return { backgroundColor: '#ffc107', color: 'black', fontWeight: 'bold' };
        if (params.value === 'RED') return { backgroundColor: '#dc3545', color: 'white', fontWeight: 'bold' };
        return null;
      }
    },
    { field: 'ProductDescription', headerName: 'Product', filter: 'agTextColumnFilter', width: 250 },
    { field: 'Packsize', headerName: 'Pack Size', filter: 'agTextColumnFilter', width: 120 }
  ];

  defaultColDef: ColDef = {
    sortable: true,
    filter: true,
    resizable: true,
    floatingFilter: true
  };

  gridOptions: GridOptions = {
    pagination: true,
    paginationPageSize: 50,
    paginationPageSizeSelector: [25, 50, 100, 200],
    domLayout: 'normal',
    animateRows: true,
    enableCellTextSelection: true,
    onGridReady: (params) => {
      this.gridApi = params.api;
    }
  };

  constructor(
    private dataService: DataService,
    private filterService: FilterService
  ) { }

  ngOnInit(): void {
    this.loadData();

    // Subscribe to filter changes
    this.filterService.filters$
      .pipe(takeUntil(this.destroy$))
      .subscribe(filters => {
        this.updateLocalFilters(filters);
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  updateLocalFilters(filters: any): void {
    // Map DashboardFilters (arrays) to local component filter strings
    // Taking the first item if array exists to support simple filtering for now
    this.filters.region = filters.region && filters.region.length > 0 ? filters.region[0] : '';
    this.filters.status = filters.promotionStatus && filters.promotionStatus.length > 0 ? filters.promotionStatus[0] : '';
    this.filters.year = filters.year ? filters.year.toString() : '';
    this.filters.ragStatus = filters.ragStatus && filters.ragStatus.length > 0 ? filters.ragStatus[0] : '';

    // Note: Customer and Product filters not yet supported in LLM parser

    // Apply filters if data is already loaded
    if (this.allPromotions.length > 0) {
      this.applyFilters();
    }
  }

  loadData(): void {
    // Load real data from CSV via DataService
    this.dataService.getAllPromotions().subscribe({
      next: (promotions) => {
        this.allPromotions = promotions;
        this.totalRecords = promotions.length;
        this.populateFilterOptions(promotions);
        this.applyFilters();
        console.log(`Loaded ${promotions.length} promotions into AG Grid`);
      },
      error: (error) => {
        console.error('Error loading promotions:', error);
        this.rowData = [];
      }
    });
  }

  populateFilterOptions(promotions: Promotion[]): void {
    // Extract unique values for filters
    this.availableRegions = [...new Set(promotions.map(p => p.Region).filter(r => r))].sort();
    this.availableCustomers = [...new Set(promotions.map(p => p.Channel_Customer).filter(c => c))].sort();
    this.availableProducts = [...new Set(promotions.map(p => p.ProductDescription).filter(p => p))].sort();
    this.availableYears = [...new Set(promotions.map(p => p.Promo_Year).filter((y): y is number => y !== null))].sort((a, b) => b - a);
  }

  applyFilters(): void {
    let filtered = [...this.allPromotions];

    if (this.filters.region) {
      filtered = filtered.filter(p => p.Region === this.filters.region);
    }
    if (this.filters.customer) {
      filtered = filtered.filter(p => p.Channel_Customer === this.filters.customer);
    }
    if (this.filters.product) {
      filtered = filtered.filter(p => p.ProductDescription === this.filters.product);
    }
    if (this.filters.status) {
      filtered = filtered.filter(p => p.Promotion_Status === this.filters.status);
    }
    if (this.filters.year) {
      filtered = filtered.filter(p => p.Promo_Year === Number(this.filters.year));
    }
    if (this.filters.ragStatus) {
      filtered = filtered.filter(p => p.Actual_RAG === this.filters.ragStatus);
    }

    this.rowData = filtered;
    this.calculateKPIs(filtered);
  }

  clearFilters(): void {
    this.filterService.resetFilters();
  }

  calculateKPIs(promotions: Promotion[]): void {
    this.kpis.totalPromotions = promotions.length;
    this.kpis.totalSalesValue = promotions.reduce((sum, p) => sum + (p.Sales_Value || 0), 0);
    this.kpis.totalGrossProfit = promotions.reduce((sum, p) => sum + (p.Gross_Profit || 0), 0);

    const validROIs = promotions.filter(p => p['ROI%'] != null).map(p => p['ROI%']);
    this.kpis.averageROI = validROIs.length > 0
      ? validROIs.reduce((sum, roi) => sum + roi, 0) / validROIs.length
      : 0;
  }

  onExportCsv(): void {
    if (this.gridApi) {
      this.gridApi.exportDataAsCsv({
        fileName: 'promotion-analytics-export.csv',
        columnSeparator: ','
      });
    } else {
      console.error('Grid API not available');
    }
  }
}

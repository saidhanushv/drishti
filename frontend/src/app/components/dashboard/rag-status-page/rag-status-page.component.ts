import { Component, OnInit, OnDestroy } from '@angular/core';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { NgxEchartsModule } from 'ngx-echarts';
import { EChartsOption } from 'echarts';
import { DataService } from '../../../services/data.service';
import { FilterService } from '../../../services/filter.service';
import { Promotion } from '../../../models/promotion.model';

@Component({
  selector: 'app-rag-status-page',
  standalone: true,
  imports: [CommonModule, NgxEchartsModule, FormsModule],
  templateUrl: './rag-status-page.component.html',
  styleUrl: './rag-status-page.component.css'
})
export class RagStatusPageComponent implements OnInit, OnDestroy {
  actualGaugeOption: EChartsOption = {};
  plannedGaugeOption: EChartsOption = {};
  comparisonChartOption: EChartsOption = {};
  allPromotions: Promotion[] = [];

  // Filter state
  filters = {
    year: '',
    startDate: '',
    endDate: '',
    region: '',
    customer: '',
    product: ''
  };

  // Available filter options
  availableYears: number[] = [];
  availableRegions: string[] = [];
  availableCustomers: string[] = [];
  availableProducts: string[] = [];

  ragCounts = {
    actual: { red: 0, amber: 0, green: 0 },
    planned: { red: 0, amber: 0, green: 0 }
  };

  aggregateKPIs = {
    successCount: 0,
    totalEventCount: 0,
    totalEventSpent: 0,
    avgVolumeUplift: 0,
    avgValueUplift: 0,
    avgROI: 0
  };

  private destroy$ = new Subject<void>();

  constructor(
    private dataService: DataService,
    private filterService: FilterService
  ) { }

  ngOnInit(): void {
    this.loadRAGData();

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
    this.filters.year = filters.year ? filters.year.toString() : '';
    this.filters.region = filters.region && filters.region.length > 0 ? filters.region[0] : '';
    // Note: LLM doesn't map to customer/product yet, but structure allows it

    if (this.allPromotions.length > 0) {
      this.applyFilters();
    }
  }

  loadRAGData(): void {
    this.dataService.getAllPromotions().subscribe({
      next: (promotions) => {
        this.allPromotions = promotions;
        this.populateFilterOptions(promotions);
        this.applyFilters();
      },
      error: (error) => {
        console.error('Error loading RAG data:', error);
      }
    });
  }

  populateFilterOptions(promotions: Promotion[]): void {
    this.availableYears = [...new Set(promotions.map(p => p.Promo_Year).filter((y): y is number => y !== null))].sort((a, b) => b - a);
    this.availableRegions = [...new Set(promotions.map(p => p.Region).filter(r => r))].sort();
    this.availableCustomers = [...new Set(promotions.map(p => p.Channel_Customer).filter(c => c))].sort();
    this.availableProducts = [...new Set(promotions.map(p => p.ProductDescription).filter(p => p))].sort();
  }

  applyFilters(): void {
    let filtered = [...this.allPromotions];

    if (this.filters.year) {
      filtered = filtered.filter(p => p.Promo_Year === Number(this.filters.year));
    }
    if (this.filters.startDate) {
      const startDate = new Date(this.filters.startDate);
      filtered = filtered.filter(p => {
        const promoStart = this.parseDate(p.Start_Prom);
        return promoStart >= startDate;
      });
    }
    if (this.filters.endDate) {
      const endDate = new Date(this.filters.endDate);
      filtered = filtered.filter(p => {
        const promoEnd = this.parseDate(p.End_Prom);
        return promoEnd <= endDate;
      });
    }
    if (this.filters.region) {
      filtered = filtered.filter(p => p.Region === this.filters.region);
    }
    if (this.filters.customer) {
      filtered = filtered.filter(p => p.Channel_Customer === this.filters.customer);
    }
    if (this.filters.product) {
      filtered = filtered.filter(p => p.ProductDescription === this.filters.product);
    }

    const ragData = this.calculateRAGData(filtered);
    this.ragCounts = ragData.counts;
    this.actualGaugeOption = this.createGaugeChart('Actual RAG Status', ragData.actualPercentages);
    this.plannedGaugeOption = this.createGaugeChart('Planned RAG Status', ragData.plannedPercentages);
    this.comparisonChartOption = this.createComparisonChart(ragData);
    this.calculateAggregateKPIs(filtered);
  }

  clearFilters(): void {
    this.filterService.resetFilters();
  }

  calculateAggregateKPIs(promotions: Promotion[]): void {
    this.aggregateKPIs.successCount = promotions.filter(p => p.Actual_RAG === 'GREEN').length;
    this.aggregateKPIs.totalEventCount = promotions.reduce((sum, p) => sum + (p.Event_Count || 0), 0);
    this.aggregateKPIs.totalEventSpent = promotions.reduce((sum, p) => sum + (p.Actual_Event_Spent || 0), 0);

    const validVolumeUplifts = promotions.filter(p => p.Actual_Promo_Sales_Volume_Uplift != null)
      .map(p => p.Actual_Promo_Sales_Volume_Uplift);
    this.aggregateKPIs.avgVolumeUplift = validVolumeUplifts.length > 0
      ? validVolumeUplifts.reduce((sum, u) => sum + u, 0) / validVolumeUplifts.length
      : 0;

    const validValueUplifts = promotions.filter(p => p['Actual_Promo_Sales_Value_Uplift_%'] != null)
      .map(p => p['Actual_Promo_Sales_Value_Uplift_%']);
    this.aggregateKPIs.avgValueUplift = validValueUplifts.length > 0
      ? validValueUplifts.reduce((sum, u) => sum + u, 0) / validValueUplifts.length
      : 0;

    const validROIs = promotions.filter(p => p['ROI%'] != null).map(p => p['ROI%']);
    this.aggregateKPIs.avgROI = validROIs.length > 0
      ? validROIs.reduce((sum, roi) => sum + roi, 0) / validROIs.length
      : 0;
  }

  parseDate(dateStr: string): Date {
    if (dateStr && dateStr.includes('-')) {
      const parts = dateStr.split('-');
      if (parts.length === 3) {
        return new Date(parseInt(parts[2]), parseInt(parts[1]) - 1, parseInt(parts[0]));
      }
    }
    return new Date(dateStr);
  }

  calculateRAGData(promotions: Promotion[]): any {
    const actualGreen = promotions.filter(p => p.Actual_RAG === 'GREEN').length;
    const actualAmber = promotions.filter(p => p.Actual_RAG === 'AMBER').length;
    const actualRed = promotions.filter(p => p.Actual_RAG === 'RED').length;

    const plannedGreen = promotions.filter(p => p.Planned_RAG === 'GREEN').length;
    const plannedAmber = promotions.filter(p => p.Planned_RAG === 'AMBER').length;
    const plannedRed = promotions.filter(p => p.Planned_RAG === 'RED').length;

    const actualTotal = actualGreen + actualAmber + actualRed || 1;
    const plannedTotal = plannedGreen + plannedAmber + plannedRed || 1;

    return {
      counts: {
        actual: { green: actualGreen, amber: actualAmber, red: actualRed },
        planned: { green: plannedGreen, amber: plannedAmber, red: plannedRed }
      },
      actualPercentages: {
        green: Math.round((actualGreen / actualTotal) * 100),
        amber: Math.round((actualAmber / actualTotal) * 100),
        red: Math.round((actualRed / actualTotal) * 100)
      },
      plannedPercentages: {
        green: Math.round((plannedGreen / plannedTotal) * 100),
        amber: Math.round((plannedAmber / plannedTotal) * 100),
        red: Math.round((plannedRed / plannedTotal) * 100)
      }
    };
  }

  createGaugeChart(title: string, percentages: any): EChartsOption {
    return {
      title: {
        text: title,
        left: 'center',
        textStyle: {
          color: '#1e293b',
          fontSize: 16,
          fontWeight: 'bold'
        }
      },
      series: [
        {
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          label: {
            show: true,
            position: 'outside',
            formatter: '{b}: {c}%'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 14,
              fontWeight: 'bold'
            }
          },
          labelLine: {
            show: true
          },
          data: [
            { value: percentages.green, name: 'Green', itemStyle: { color: '#28a745' } },
            { value: percentages.amber, name: 'Amber', itemStyle: { color: '#ffc107' } },
            { value: percentages.red, name: 'Red', itemStyle: { color: '#dc3545' } }
          ]
        }
      ]
    };
  }

  createComparisonChart(data: any): EChartsOption {
    return {
      title: {
        text: 'Actual vs Planned RAG Comparison',
        left: 'center',
        textStyle: {
          color: '#1e293b',
          fontSize: 16,
          fontWeight: 'bold'
        }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        }
      },
      legend: {
        data: ['Actual', 'Planned'],
        bottom: 10
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: ['Green', 'Amber', 'Red']
      },
      yAxis: {
        type: 'value',
        name: 'Count'
      },
      series: [
        {
          name: 'Actual',
          type: 'bar',
          data: [
            { value: data.counts.actual.green, itemStyle: { color: '#28a745' } },
            { value: data.counts.actual.amber, itemStyle: { color: '#ffc107' } },
            { value: data.counts.actual.red, itemStyle: { color: '#dc3545' } }
          ]
        },
        {
          name: 'Planned',
          type: 'bar',
          data: [
            { value: data.counts.planned.green, itemStyle: { color: '#28a74580' } },
            { value: data.counts.planned.amber, itemStyle: { color: '#ffc10780' } },
            { value: data.counts.planned.red, itemStyle: { color: '#dc354580' } }
          ]
        }
      ]
    };
  }
}

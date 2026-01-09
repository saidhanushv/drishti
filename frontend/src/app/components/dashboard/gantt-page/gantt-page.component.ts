import { Component, OnInit, OnDestroy } from '@angular/core';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { CommonModule } from '@angular/common';
import { NgxEchartsModule } from 'ngx-echarts';
import { EChartsOption } from 'echarts';
import { DataService } from '../../../services/data.service';
import { FilterService } from '../../../services/filter.service';
import { Promotion } from '../../../models/promotion.model';

@Component({
  selector: 'app-gantt-page',
  standalone: true,
  imports: [CommonModule, NgxEchartsModule],
  templateUrl: './gantt-page.component.html',
  styleUrl: './gantt-page.component.css'
})
export class GanttPageComponent implements OnInit, OnDestroy {
  chartOption: EChartsOption = {};
  allPromotions: Promotion[] = [];

  // Filter state
  filters = {
    region: '',
    status: '',
    year: '',
    ragStatus: ''
  };

  kpis = {
    totalEvents: 0,
    actualEventSpent: 0,
    plannedEventSpent: 0,
    avgROI: 0,
    totalGrossProfit: 0,
    avgSalesUplift: 0,
    incrementalSales: 0,
    avgGrossMargin: 0
  };

  private destroy$ = new Subject<void>();

  constructor(
    private dataService: DataService,
    private filterService: FilterService
  ) { }

  ngOnInit(): void {
    this.loadGanttData();

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
    this.filters.region = filters.region && filters.region.length > 0 ? filters.region[0] : '';
    this.filters.status = filters.promotionStatus && filters.promotionStatus.length > 0 ? filters.promotionStatus[0] : '';
    this.filters.year = filters.year ? filters.year.toString() : '';
    this.filters.ragStatus = filters.ragStatus && filters.ragStatus.length > 0 ? filters.ragStatus[0] : '';

    if (this.allPromotions.length > 0) {
      this.applyFilters();
    }
  }

  loadGanttData(): void {
    this.dataService.getAllPromotions().subscribe({
      next: (promotions) => {
        this.allPromotions = promotions;
        this.applyFilters();
      },
      error: (error) => {
        console.error('Error loading Gantt data:', error);
      }
    });
  }

  applyFilters(): void {
    let filtered = [...this.allPromotions];

    if (this.filters.region) {
      filtered = filtered.filter(p => p.Region === this.filters.region);
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

    const ganttData = this.transformToGanttData(filtered);
    this.chartOption = this.createGanttChart(ganttData);
    this.calculateKPIs(filtered);
  }

  calculateKPIs(promotions: Promotion[]): void {
    this.kpis.totalEvents = promotions.reduce((sum, p) => sum + (p.Event_Count || 0), 0);
    this.kpis.actualEventSpent = promotions.reduce((sum, p) => sum + (p.Actual_Event_Spent || 0), 0);
    this.kpis.plannedEventSpent = promotions.reduce((sum, p) => sum + (p.Planned_Event_Spent || 0), 0);
    this.kpis.totalGrossProfit = promotions.reduce((sum, p) => sum + (p.Gross_Profit || 0), 0);
    this.kpis.incrementalSales = promotions.reduce((sum, p) => sum + (p.Incremental_Sales || 0), 0);

    const validROIs = promotions.filter(p => p['ROI%'] != null).map(p => p['ROI%']);
    this.kpis.avgROI = validROIs.length > 0
      ? validROIs.reduce((sum, roi) => sum + roi, 0) / validROIs.length
      : 0;

    const validUplifts = promotions.filter(p => p['Actual_Promo_Sales_Value_Uplift_%'] != null)
      .map(p => p['Actual_Promo_Sales_Value_Uplift_%']);
    this.kpis.avgSalesUplift = validUplifts.length > 0
      ? validUplifts.reduce((sum, u) => sum + u, 0) / validUplifts.length
      : 0;

    const validMargins = promotions.filter(p => p['Actual_Gross_Margin_%'] != null)
      .map(p => p['Actual_Gross_Margin_%']);
    this.kpis.avgGrossMargin = validMargins.length > 0
      ? validMargins.reduce((sum, m) => sum + m, 0) / validMargins.length
      : 0;
  }

  transformToGanttData(promotions: Promotion[]): any[] {
    return promotions
      .filter(p => p.Start_Prom && p.End_Prom && p.PromoID)
      .slice(0, 20) // Limit to 20 for better visualization
      .map(p => ({
        name: p.PromoID,
        status: p.Promotion_Status || 'UNKNOWN',
        start: this.parseDate(p.Start_Prom).getTime(),
        end: this.parseDate(p.End_Prom).getTime(),
        startDate: p.Start_Prom,
        endDate: p.End_Prom,
        duration: this.calculateDuration(p.Start_Prom, p.End_Prom)
      }))
      .sort((a, b) => a.start - b.start);
  }

  parseDate(dateStr: string): Date {
    // Handle dd-mm-yyyy format
    if (dateStr && dateStr.includes('-')) {
      const parts = dateStr.split('-');
      if (parts.length === 3) {
        return new Date(parseInt(parts[2]), parseInt(parts[1]) - 1, parseInt(parts[0]));
      }
    }
    return new Date(dateStr);
  }

  calculateDuration(start: string, end: string): number {
    const startDate = this.parseDate(start);
    const endDate = this.parseDate(end);
    return Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));
  }

  createGanttChart(data: any[]): EChartsOption {
    return {
      title: {
        text: 'Promotion Timeline',
        left: 'center',
        textStyle: {
          color: '#1e293b',
          fontSize: 20,
          fontWeight: 'bold'
        }
      },
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          const data = params.data;
          return `
            <strong>${data.name}</strong><br/>
            Status: ${data.status}<br/>
            Start: ${data.startDate}<br/>
            End: ${data.endDate}<br/>
            Duration: ${data.duration} days
          `;
        }
      },
      legend: {
        data: ['COMPLETED', 'ONGOING', 'PLANNED'],
        bottom: 10,
        textStyle: {
          color: '#64748b'
        }
      },
      grid: {
        left: '15%',
        right: '10%',
        top: '15%',
        bottom: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'time',
        axisLabel: {
          formatter: '{MMM} {dd}',
          color: '#64748b'
        },
        splitLine: {
          show: true,
          lineStyle: {
            color: '#e2e8f0'
          }
        }
      },
      yAxis: {
        type: 'category',
        data: data.map(d => d.name),
        axisLabel: {
          color: '#64748b',
          fontSize: 12
        }
      },
      series: [
        {
          name: 'COMPLETED',
          type: 'custom',
          renderItem: this.renderGanttItem.bind(this),
          encode: {
            x: [1, 2],
            y: 0
          },
          data: data.filter(d => d.status === 'COMPLETED').map(d => ({
            name: d.name,
            value: [d.name, d.start, d.end],
            itemStyle: { color: '#28a745' },
            ...d
          }))
        },
        {
          name: 'ONGOING',
          type: 'custom',
          renderItem: this.renderGanttItem.bind(this),
          encode: {
            x: [1, 2],
            y: 0
          },
          data: data.filter(d => d.status === 'ONGOING').map(d => ({
            name: d.name,
            value: [d.name, d.start, d.end],
            itemStyle: { color: '#ffc107' },
            ...d
          }))
        },
        {
          name: 'PLANNED',
          type: 'custom',
          renderItem: this.renderGanttItem.bind(this),
          encode: {
            x: [1, 2],
            y: 0
          },
          data: data.filter(d => d.status === 'PLANNED').map(d => ({
            name: d.name,
            value: [d.name, d.start, d.end],
            itemStyle: { color: '#17a2b8' },
            ...d
          }))
        }
      ]
    };
  }

  renderGanttItem(params: any, api: any): any {
    const categoryIndex = api.value(0);
    const start = api.coord([api.value(1), categoryIndex]);
    const end = api.coord([api.value(2), categoryIndex]);
    const height = api.size([0, 1])[1] * 0.6;

    return {
      type: 'rect',
      shape: {
        x: start[0],
        y: start[1] - height / 2,
        width: end[0] - start[0],
        height: height
      },
      style: api.style()
    };
  }
}

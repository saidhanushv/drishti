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
  selector: 'app-analytics-page',
  standalone: true,
  imports: [CommonModule, NgxEchartsModule],
  templateUrl: './analytics-page.component.html',
  styleUrl: './analytics-page.component.css'
})
export class AnalyticsPageComponent implements OnInit, OnDestroy {
  topCustomersChartOption: EChartsOption = {};
  roiByRegionChartOption: EChartsOption = {};
  salesTrendChartOption: EChartsOption = {};
  allPromotions: Promotion[] = [];

  // Filter state
  filters = {
    region: '',
    year: '',
    ragStatus: '',
    promotionStatus: ''
  };

  kpis = {
    totalGrossProfit: 0,
    totalSalesValue: 0,
    averageROI: 0,
    totalPromotions: 0
  };

  private destroy$ = new Subject<void>();

  constructor(
    private dataService: DataService,
    private filterService: FilterService
  ) { }

  ngOnInit(): void {
    this.loadAnalyticsData();

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
    this.filters.year = filters.year ? filters.year.toString() : '';
    this.filters.ragStatus = filters.ragStatus && filters.ragStatus.length > 0 ? filters.ragStatus[0] : '';
    this.filters.promotionStatus = filters.promotionStatus && filters.promotionStatus.length > 0 ? filters.promotionStatus[0] : '';

    if (this.allPromotions.length > 0) {
      this.applyFilters();
    }
  }

  loadAnalyticsData(): void {
    this.dataService.getAllPromotions().subscribe({
      next: (promotions) => {
        this.allPromotions = promotions;
        this.applyFilters();
      },
      error: (error) => {
        console.error('Error loading analytics data:', error);
      }
    });
  }

  applyFilters(): void {
    let filtered = [...this.allPromotions];

    if (this.filters.region) {
      filtered = filtered.filter(p => p.Region === this.filters.region);
    }
    if (this.filters.year) {
      filtered = filtered.filter(p => p.Promo_Year === Number(this.filters.year));
    }
    if (this.filters.ragStatus) {
      filtered = filtered.filter(p => p.Actual_RAG === this.filters.ragStatus);
    }
    if (this.filters.promotionStatus) {
      filtered = filtered.filter(p => p.Promotion_Status === this.filters.promotionStatus);
    }

    this.calculateKPIs(filtered);
    this.topCustomersChartOption = this.createTopCustomersChart(filtered);
    this.roiByRegionChartOption = this.createROIByRegionChart(filtered);
    this.salesTrendChartOption = this.createSalesTrendChart(filtered);
  }

  calculateKPIs(promotions: Promotion[]): void {
    this.kpis.totalPromotions = promotions.length;
    this.kpis.totalGrossProfit = promotions.reduce((sum, p) => sum + (p.Gross_Profit || 0), 0);
    this.kpis.totalSalesValue = promotions.reduce((sum, p) => sum + (p.Sales_Value || 0), 0);

    const validROIs = promotions.filter(p => p['ROI%'] != null).map(p => p['ROI%']);
    this.kpis.averageROI = validROIs.length > 0
      ? validROIs.reduce((sum, roi) => sum + roi, 0) / validROIs.length
      : 0;
  }

  createTopCustomersChart(promotions: Promotion[]): EChartsOption {
    // Group by customer and sum sales
    const customerSales = new Map<string, number>();
    promotions.forEach(p => {
      const customer = p.Channel_Customer || 'Unknown';
      const sales = p.Sales_Value || 0;
      customerSales.set(customer, (customerSales.get(customer) || 0) + sales);
    });

    // Get top 5
    const topCustomers = Array.from(customerSales.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([name, value]) => ({ name, value }));

    return {
      title: {
        text: 'Top 5 Customers by Turnover',
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
        },
        formatter: (params: any) => {
          const data = params[0];
          return `${data.name}<br/>Turnover: $${data.value.toLocaleString()}`;
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: topCustomers.map(d => d.name),
        axisLabel: {
          rotate: 45,
          color: '#64748b'
        }
      },
      yAxis: {
        type: 'value',
        name: 'Turnover ($)',
        axisLabel: {
          color: '#64748b',
          formatter: (value: number) => `$${(value / 1000).toFixed(0)}K`
        }
      },
      series: [
        {
          name: 'Turnover',
          type: 'bar',
          data: topCustomers.map(d => ({
            value: d.value,
            itemStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: '#3b82f6' }, // Blue 500
                  { offset: 1, color: '#06b6d4' }  // Cyan 500
                ]
              }
            }
          })),
          barWidth: '60%'
        }
      ]
    };
  }

  createROIByRegionChart(promotions: Promotion[]): EChartsOption {
    // Group by region and calculate average ROI
    const regionROI = new Map<string, number[]>();
    promotions.forEach(p => {
      const region = p.Region || 'Unknown';
      const roi = p['ROI%'];
      if (roi != null) {
        if (!regionROI.has(region)) {
          regionROI.set(region, []);
        }
        regionROI.get(region)!.push(roi);
      }
    });

    const roiData = Array.from(regionROI.entries()).map(([name, rois]) => ({
      name,
      value: rois.reduce((sum, r) => sum + r, 0) / rois.length
    }));

    return {
      title: {
        text: 'ROI% by Region',
        left: 'center',
        textStyle: {
          color: '#1e293b',
          fontSize: 16,
          fontWeight: 'bold'
        }
      },
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          return `${params.name}: ${params.value.toFixed(1)}%`;
        }
      },
      legend: {
        bottom: 10,
        textStyle: {
          color: '#64748b'
        }
      },
      series: [
        {
          name: 'ROI',
          type: 'pie',
          radius: '50%',
          data: roiData.map((d, i) => ({
            value: d.value,
            name: d.name,
            itemStyle: {
              color: ['#0ea5e9', '#06b6d4', '#64748b', '#94a3b8', '#cbd5e1'][i % 5]
            }
          })),
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          },
          label: {
            formatter: (params: any) => {
              return `${params.name}: ${params.value.toFixed(1)}%`;
            }
          }
        }
      ]
    };
  }

  createSalesTrendChart(promotions: Promotion[]): EChartsOption {
    // This is simplified - you might want to group by actual months from the data
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const monthlySales = new Array(12).fill(0);
    const monthlyCounts = new Array(12).fill(0);

    promotions.forEach(p => {
      if (p.Week) {
        const date = this.parseDate(p.Week);
        const month = date.getMonth();
        monthlySales[month] += p.Sales_Value || 0;
        monthlyCounts[month]++;
      }
    });

    const salesData = months.map((month, i) => ({
      month,
      value: monthlyCounts[i] > 0 ? monthlySales[i] / monthlyCounts[i] : 0
    }));

    return {
      title: {
        text: 'Average Sales Value Trend',
        left: 'center',
        textStyle: {
          color: '#1e293b',
          fontSize: 16,
          fontWeight: 'bold'
        }
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          const data = params[0];
          return `${data.name}<br/>Avg Sales: $${data.value.toLocaleString()}`;
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: salesData.map(d => d.month),
        axisLabel: {
          color: '#64748b'
        }
      },
      yAxis: {
        type: 'value',
        name: 'Sales Value ($)',
        axisLabel: {
          color: '#64748b',
          formatter: (value: number) => `$${(value / 1000).toFixed(0)}K`
        }
      },
      series: [
        {
          name: 'Sales',
          type: 'line',
          data: salesData.map(d => d.value),
          smooth: true,
          lineStyle: {
            width: 3,
            color: '#3b82f6' // Blue 500
          },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(59, 130, 246, 0.5)' }, // Blue 500
                { offset: 1, color: 'rgba(59, 130, 246, 0.0)' }
              ]
            }
          },
          itemStyle: {
            color: '#3b82f6'
          }
        }
      ]
    };
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
}

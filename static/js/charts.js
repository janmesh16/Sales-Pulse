/**
 * SalesPulse Analytics & Chart.js Engine
 * Initializes and dynamically updates 6 interactive visualizations:
 * 1. 30-Day Daily Sales & Profit Trend (Line)
 * 2. Top 5 Products by Volume / Revenue (Horizontal Bar)
 * 3. Monthly Expense Breakdown by Category (Doughnut)
 * 4. Sales Distribution by Category (Pie)
 * 5. 6-Month Revenue vs. Expenses Comparison (Grouped Bar)
 * 6. 7-Day Autoregressive Moving Average Sales Forecast (Dotted Projection)
 */

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('salesTrendChart')) {
    initSalesTrendChart();
    initTopProductsChart();
    initExpenseBreakdownChart();
    initCategorySalesChart();
    initMonthlyComparisonChart();
    initForecastChart();
  }
});

// Chart.js Color Palette
const THEME = {
  teal: '#0F766E',
  tealLight: 'rgba(15, 118, 110, 0.15)',
  indigo: '#4F46E5',
  indigoLight: 'rgba(79, 70, 229, 0.15)',
  emerald: '#10B981',
  emeraldLight: 'rgba(16, 185, 129, 0.15)',
  rose: '#F43F5E',
  roseLight: 'rgba(244, 63, 94, 0.15)',
  amber: '#F59E0B',
  amberLight: 'rgba(245, 158, 11, 0.15)',
  sky: '#0EA5E9',
  purple: '#8B5CF6',
  palette: ['#0F766E', '#4F46E5', '#0EA5E9', '#10B981', '#F59E0B', '#F43F5E', '#8B5CF6', '#64748B']
};

/** 1. 30-Day Sales & Profit Trend Line Chart **/
async function initSalesTrendChart() {
  const ctx = document.getElementById('salesTrendChart')?.getContext('2d');
  if (!ctx) return;

  try {
    const res = await fetch('/api/chart/sales-trend');
    const data = await res.json();

    new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.labels,
        datasets: [
          {
            label: 'Revenue (₹)',
            data: data.revenue,
            borderColor: THEME.teal,
            backgroundColor: THEME.tealLight,
            fill: true,
            tension: 0.35,
            borderWidth: 2.5,
            pointRadius: 2,
            pointHoverRadius: 5
          },
          {
            label: 'Gross Profit (₹)',
            data: data.profit,
            borderColor: THEME.emerald,
            backgroundColor: 'transparent',
            borderDash: [4, 4],
            tension: 0.35,
            borderWidth: 2,
            pointRadius: 2,
            pointHoverRadius: 5
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 12, font: { family: 'Inter' } } },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ₹ ${Number(ctx.raw).toLocaleString('en-IN')}`
            }
          }
        },
        scales: {
          x: { grid: { display: false } },
          y: {
            beginAtZero: true,
            grid: { color: '#F1F5F9' },
            ticks: {
              callback: (val) => '₹ ' + (val >= 1000 ? (val / 1000).toFixed(0) + 'k' : val)
            }
          }
        }
      }
    });
  } catch (e) {
    console.error('Failed to load Sales Trend chart:', e);
  }
}

/** 2. Top 5 Products Horizontal Bar Chart **/
let topProductsChartInstance = null;
async function initTopProductsChart(metric = 'qty') {
  const ctx = document.getElementById('topProductsChart')?.getContext('2d');
  if (!ctx) return;

  try {
    const res = await fetch(`/api/chart/top-products?metric=${metric}`);
    const data = await res.json();

    const chartData = metric === 'qty' ? data.quantities : data.revenues;
    const labelTitle = metric === 'qty' ? 'Units Sold' : 'Revenue (₹)';

    if (topProductsChartInstance) {
      topProductsChartInstance.destroy();
    }

    topProductsChartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.labels,
        datasets: [{
          label: labelTitle,
          data: chartData,
          backgroundColor: THEME.indigo,
          borderRadius: 6,
          barPercentage: 0.65
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => `${labelTitle}: ${metric === 'qty' ? ctx.raw : '₹ ' + Number(ctx.raw).toLocaleString('en-IN')}`
            }
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            grid: { color: '#F1F5F9' },
            ticks: {
              callback: (val) => metric === 'qty' ? val : '₹ ' + (val >= 1000 ? (val / 1000).toFixed(0) + 'k' : val)
            }
          },
          y: { grid: { display: false } }
        }
      }
    });

    // Wire Metric Switch Buttons
    document.querySelectorAll('.top-prod-metric-btn').forEach(btn => {
      btn.onclick = () => {
        document.querySelectorAll('.top-prod-metric-btn').forEach(b => b.classList.remove('active', 'btn-teal'));
        document.querySelectorAll('.top-prod-metric-btn').forEach(b => b.classList.add('btn-outline-secondary'));
        btn.classList.add('active', 'btn-teal');
        btn.classList.remove('btn-outline-secondary');
        initTopProductsChart(btn.dataset.metric);
      };
    });
  } catch (e) {
    console.error('Failed to load Top Products chart:', e);
  }
}

/** 3. Monthly Expense Breakdown Doughnut Chart **/
async function initExpenseBreakdownChart() {
  const ctx = document.getElementById('expenseBreakdownChart')?.getContext('2d');
  if (!ctx) return;

  try {
    const res = await fetch('/api/chart/expense-breakdown');
    const data = await res.json();

    new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: data.labels,
        datasets: [{
          data: data.amounts,
          backgroundColor: THEME.palette,
          borderWidth: 2,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '68%',
        plugins: {
          legend: { position: 'right', labels: { boxWidth: 12, font: { size: 11, family: 'Inter' } } },
          tooltip: {
            callbacks: {
              label: (ctx) => ` ${ctx.label}: ₹ ${Number(ctx.raw).toLocaleString('en-IN')}`
            }
          }
        }
      }
    });
  } catch (e) {
    console.error('Failed to load Expense Breakdown chart:', e);
  }
}

/** 4. Category-Wise Sales Distribution Chart **/
async function initCategorySalesChart() {
  const ctx = document.getElementById('categorySalesChart')?.getContext('2d');
  if (!ctx) return;

  try {
    const res = await fetch('/api/chart/category-sales');
    const data = await res.json();

    new Chart(ctx, {
      type: 'pie',
      data: {
        labels: data.labels,
        datasets: [{
          data: data.revenues,
          backgroundColor: THEME.palette,
          borderWidth: 2,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right', labels: { boxWidth: 12, font: { size: 11, family: 'Inter' } } },
          tooltip: {
            callbacks: {
              label: (ctx) => ` ${ctx.label}: ₹ ${Number(ctx.raw).toLocaleString('en-IN')}`
            }
          }
        }
      }
    });
  } catch (e) {
    console.error('Failed to load Category Sales chart:', e);
  }
}

/** 5. 6-Month Revenue vs Expenses Comparison Grouped Bar Chart **/
async function initMonthlyComparisonChart() {
  const ctx = document.getElementById('monthlyComparisonChart')?.getContext('2d');
  if (!ctx) return;

  try {
    const res = await fetch('/api/chart/monthly-compare');
    const data = await res.json();

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.labels,
        datasets: [
          {
            label: 'Revenue (₹)',
            data: data.revenues,
            backgroundColor: THEME.teal,
            borderRadius: 5,
            barPercentage: 0.6
          },
          {
            label: 'Expenses (₹)',
            data: data.expenses,
            backgroundColor: THEME.rose,
            borderRadius: 5,
            barPercentage: 0.6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 12, font: { family: 'Inter' } } },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ₹ ${Number(ctx.raw).toLocaleString('en-IN')}`
            }
          }
        },
        scales: {
          x: { grid: { display: false } },
          y: {
            beginAtZero: true,
            grid: { color: '#F1F5F9' },
            ticks: {
              callback: (val) => '₹ ' + (val >= 1000 ? (val / 1000).toFixed(0) + 'k' : val)
            }
          }
        }
      }
    });
  } catch (e) {
    console.error('Failed to load Monthly Comparison chart:', e);
  }
}

/** 6. 7-Day Moving Average Forecast Chart **/
async function initForecastChart() {
  const ctx = document.getElementById('forecastChart')?.getContext('2d');
  if (!ctx) return;

  try {
    const res = await fetch('/api/chart/forecast');
    const data = await res.json();

    // Combine recent historical days (last 14 days) and 7 forecast days
    const histSubsetLabels = data.historical_labels.slice(-14);
    const histSubsetData = data.historical_data.slice(-14);

    const labels = [...histSubsetLabels, ...data.forecast_labels];
    const historicalLine = [...histSubsetData, ...Array(data.forecast_labels.length).fill(null)];
    
    // Connect forecast line from last historical point
    const forecastLine = [
      ...Array(histSubsetData.length - 1).fill(null),
      histSubsetData[histSubsetData.length - 1],
      ...data.forecast_data
    ];

    new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Actual Daily Sales (₹)',
            data: historicalLine,
            borderColor: THEME.teal,
            backgroundColor: THEME.tealLight,
            fill: true,
            tension: 0.3,
            borderWidth: 2.5,
            pointRadius: 3
          },
          {
            label: '7-Day Forecast (₹ Estimate)',
            data: forecastLine,
            borderColor: THEME.amber,
            borderDash: [5, 5],
            backgroundColor: 'transparent',
            tension: 0.3,
            borderWidth: 2.5,
            pointRadius: 4,
            pointBackgroundColor: THEME.amber
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 12, font: { family: 'Inter' } } },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ₹ ${Number(ctx.raw).toLocaleString('en-IN')}`
            }
          }
        },
        scales: {
          x: { grid: { display: false } },
          y: {
            beginAtZero: true,
            grid: { color: '#F1F5F9' },
            ticks: {
              callback: (val) => '₹ ' + (val >= 1000 ? (val / 1000).toFixed(0) + 'k' : val)
            }
          }
        }
      }
    });
  } catch (e) {
    console.error('Failed to load Forecast chart:', e);
  }
}

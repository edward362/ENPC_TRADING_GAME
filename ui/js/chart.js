// js/chart.js
// Bloomberg-style price charts with enhanced styling

import { byId } from "./ui.js";
import { MAX_POINTS, HISTORY, LABELS } from "./constants.js";

// Global Chart.js instances
let chart = null;
let miniChart = null;

// The currently selected asset whose history is shown
let chartAsset = "OIL";

/**
 * Initializes the main price chart with Bloomberg styling
 * Call this once when the game starts (e.g. on GAME_STARTED).
 */
export function initChart() {
  const canvas = byId("priceChart");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");

  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: LABELS,
      datasets: [
        {
          label: chartAsset,
          data: HISTORY[chartAsset],
          borderColor: '#007aff',
          backgroundColor: 'rgba(0, 122, 255, 0.1)',
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
          tension: 0.3,
          fill: true
        }
      ]
    },
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        intersect: false,
        mode: 'index'
      },
      scales: {
        x: {
          grid: {
            color: '#1a2332',
            borderColor: '#2a3648'
          },
          ticks: {
            color: '#9aa0a6',
            maxTicksLimit: 10,
            font: {
              family: 'Consolas, Monaco, monospace',
              size: 10
            }
          }
        },
        y: {
          beginAtZero: false,
          position: 'right',
          grid: {
            color: '#1a2332',
            borderColor: '#2a3648'
          },
          ticks: {
            color: '#9aa0a6',
            font: {
              family: 'Consolas, Monaco, monospace',
              size: 11
            },
            callback: function(value) {
              return value.toFixed(2);
            }
          }
        }
      },
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          enabled: true,
          backgroundColor: '#0f1419',
          borderColor: '#ff9500',
          borderWidth: 1,
          titleColor: '#ff9500',
          bodyColor: '#e8eaed',
          titleFont: {
            family: 'Consolas, Monaco, monospace',
            size: 11,
            weight: 'bold'
          },
          bodyFont: {
            family: 'Consolas, Monaco, monospace',
            size: 11
          },
          padding: 10,
          displayColors: false,
          callbacks: {
            title: function(context) {
              return chartAsset;
            },
            label: function(context) {
              return 'Price: ' + context.parsed.y.toFixed(2);
            }
          }
        }
      }
    }
  });

  // Initialize mini chart
  initMiniChart();
}

/**
 * Initialize a mini overview chart showing all assets
 */
function initMiniChart() {
  const canvas = byId("miniChart1");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");

  // Create datasets for all assets
  const datasets = Object.keys(HISTORY).map((asset, index) => {
    const colors = ['#007aff', '#00c853', '#ff9500', '#ff3b30', '#ffcc00'];
    return {
      label: asset,
      data: HISTORY[asset],
      borderColor: colors[index % colors.length],
      borderWidth: 1,
      pointRadius: 0,
      tension: 0.3,
      fill: false
    };
  });

  miniChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: LABELS,
      datasets: datasets
    },
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: true,
      interaction: {
        intersect: false,
        mode: 'index'
      },
      scales: {
        x: {
          display: false
        },
        y: {
          display: false,
          beginAtZero: false
        }
      },
      plugins: {
        legend: {
          display: true,
          position: 'bottom',
          labels: {
            color: '#9aa0a6',
            font: {
              family: 'Consolas, Monaco, monospace',
              size: 7
            },
            boxWidth: 8,
            boxHeight: 8,
            padding: 4
          }
        },
        tooltip: {
          enabled: false
        }
      }
    }
  });
}

/**
 * Switch the chart to another asset (dropdown change).
 *
 * @param {string} newAsset - e.g. "GOLD"
 */
export function updateChartAsset(newAsset) {
  chartAsset = newAsset;

  if (!chart) return;

  // Determine color based on trend
  const data = HISTORY[chartAsset];
  const isUpTrend = data.length >= 2 && data[data.length - 1] > data[0];
  const lineColor = isUpTrend ? '#00c853' : '#ff3b30';

  chart.data.datasets[0].label = chartAsset;
  chart.data.datasets[0].data = HISTORY[chartAsset];
  chart.data.datasets[0].borderColor = lineColor;
  chart.data.datasets[0].backgroundColor = isUpTrend 
    ? 'rgba(0, 200, 83, 0.1)' 
    : 'rgba(255, 59, 48, 0.1)';
  
  chart.update('none'); // Update without animation for performance
}

/**
 * Push a new tick of prices into the history buffers,
 * and refresh the charts.
 *
 * @param {Object<string, number>} prices - map asset -> latest price
 */
export function pushTickToHistory(prices) {
  if (!prices) return;

  // Add a human-readable timestamp label
  const ts = new Date().toLocaleTimeString();
  LABELS.push(ts);
  if (LABELS.length > MAX_POINTS) LABELS.shift();

  // Update all assets with the latest prices
  Object.keys(HISTORY).forEach((asset) => {
    const arr = HISTORY[asset];
    arr.push(prices[asset] ?? null);
    if (arr.length > MAX_POINTS) arr.shift();
  });

  // Update main chart
  if (chart) {
    // Update color based on trend
    const data = HISTORY[chartAsset];
    if (data.length >= 2) {
      const isUpTrend = data[data.length - 1] > data[data.length - 2];
      const lineColor = isUpTrend ? '#00c853' : '#ff3b30';
      
      chart.data.datasets[0].borderColor = lineColor;
      chart.data.datasets[0].backgroundColor = isUpTrend 
        ? 'rgba(0, 200, 83, 0.1)' 
        : 'rgba(255, 59, 48, 0.1)';
    }
    
    chart.update('none'); // Update without animation
  }

  // Update mini chart
  if (miniChart) {
    miniChart.update('none'); // Update without animation
  }
}

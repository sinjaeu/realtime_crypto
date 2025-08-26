import React, { useEffect, useRef } from 'react';
import Chart from 'chart.js/auto';

const PriceChart = ({ 
  symbol, 
  priceHistory = [], 
  currentPrice, 
  changePercent = 0,
  height = 300 
}) => {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  useEffect(() => {
    if (!chartRef.current || !priceHistory || priceHistory.length === 0) return;

    // 기존 차트 제거
    if (chartInstance.current) {
      chartInstance.current.destroy();
    }

    const ctx = chartRef.current.getContext('2d');
    
    // 시간 라벨 생성 (최근 100개 데이터 포인트)
    const labels = priceHistory.map((_, index) => {
      const minutesAgo = (priceHistory.length - 1 - index) * 5 / 60; // 5초 간격을 분으로 변환
      return minutesAgo > 60 
        ? `${Math.floor(minutesAgo / 60)}h ${Math.floor(minutesAgo % 60)}m`
        : `${Math.floor(minutesAgo)}m`;
    });

    // 차트 색상 결정
    const isPositive = changePercent >= 0;
    const lineColor = isPositive ? '#28a745' : '#dc3545';
    const gradientColor = isPositive 
      ? 'rgba(40, 167, 69, 0.1)' 
      : 'rgba(220, 53, 69, 0.1)';

    // 그라데이션 생성
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, gradientColor);
    gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

    chartInstance.current = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: `${symbol} 가격`,
          data: priceHistory,
          borderColor: lineColor,
          backgroundColor: gradient,
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 0,
          pointHoverRadius: 6,
          pointHoverBackgroundColor: lineColor,
          pointHoverBorderColor: '#ffffff',
          pointHoverBorderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: '#ffffff',
            bodyColor: '#ffffff',
            borderColor: lineColor,
            borderWidth: 1,
            callbacks: {
              label: function(context) {
                return `$${context.parsed.y.toFixed(4)}`;
              }
            }
          }
        },
        scales: {
          x: {
            display: true,
            grid: {
              color: 'rgba(0, 0, 0, 0.1)',
              drawBorder: false
            },
            ticks: {
              maxTicksLimit: 6,
              color: '#6c757d',
              font: {
                size: 11
              }
            }
          },
          y: {
            display: true,
            grid: {
              color: 'rgba(0, 0, 0, 0.1)',
              drawBorder: false
            },
            ticks: {
              color: '#6c757d',
              font: {
                size: 11
              },
              callback: function(value) {
                return `$${value.toFixed(2)}`;
              }
            }
          }
        },
        interaction: {
          intersect: false,
          mode: 'index'
        },
        elements: {
          point: {
            hoverRadius: 8
          }
        }
      }
    });

    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy();
      }
    };
  }, [symbol, priceHistory, currentPrice, changePercent, height]);

  if (!priceHistory || priceHistory.length === 0) {
    return (
      <div className="chart-placeholder" style={{ height: `${height}px` }}>
        <div className="chart-loading">
          <div className="loading-spinner"></div>
          <p>차트 데이터 로딩 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="price-chart-container" style={{ height: `${height}px` }}>
      <canvas ref={chartRef} />
    </div>
  );
};

export default PriceChart;

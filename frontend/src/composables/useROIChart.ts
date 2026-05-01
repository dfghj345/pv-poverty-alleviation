import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import * as echarts from 'echarts';

export function useROIChart(
  getChartData: () => { years: string[]; profits: number[]; cumulative: number[] } | null
) {
  const chartRef = ref<HTMLElement | null>(null);
  let chart: echarts.ECharts | null = null;
  let stopWatch: (() => void) | null = null;
  let resizeHandler: (() => void) | null = null;
  let resizeObserver: ResizeObserver | null = null;

  function resizeChart(): void {
    requestAnimationFrame(() => {
      chart?.resize();
    });
  }

  function render(retryCount = 0): void {
    const data = getChartData();
    if (!chartRef.value) return;

    if ((chartRef.value.clientWidth === 0 || chartRef.value.clientHeight === 0) && retryCount < 5) {
      window.setTimeout(() => {
        render(retryCount + 1);
      }, 120);
      return;
    }

    if (!data) {
      chart?.clear();
      return;
    }

    try {
      if (!chart) {
        chart = echarts.init(chartRef.value, 'dark');
      }

      const compact = window.innerWidth < 768;
      chart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis', confine: true },
        legend: {
          data: ['年现金流', '累计现金流'],
          bottom: 0,
          textStyle: { fontSize: compact ? 11 : 12 },
        },
        grid: {
          top: compact ? '14%' : '15%',
          left: compact ? '12%' : '10%',
          right: compact ? '8%' : '5%',
          bottom: compact ? '20%' : '15%',
        },
        xAxis: {
          type: 'category',
          data: data.years,
          axisLabel: { fontSize: compact ? 10 : 12 },
        },
        yAxis: {
          type: 'value',
          axisLabel: { fontSize: compact ? 10 : 12 },
          splitLine: { lineStyle: { color: '#333' } },
        },
        series: [
          { name: '年现金流', type: 'bar', data: data.profits, itemStyle: { color: '#10b981' } },
          { name: '累计现金流', type: 'line', data: data.cumulative, smooth: true, itemStyle: { color: '#3b82f6' }, areaStyle: { opacity: 0.1 } }
        ]
      });
      resizeChart();
    } catch (error) {
      console.error('ROI chart render failed', error);
    }
  }

  onMounted(() => {
    stopWatch = watch(
      getChartData,
      async () => {
        await nextTick();
        render();
      },
      { immediate: true, deep: true },
    );

    resizeHandler = () => resizeChart();
    window.addEventListener('resize', resizeHandler);
    resizeObserver = new ResizeObserver(() => {
      resizeChart();
    });
    if (chartRef.value?.parentElement) {
      resizeObserver.observe(chartRef.value.parentElement);
    }
  });

  onUnmounted(() => {
    stopWatch?.();
    if (resizeHandler) {
      window.removeEventListener('resize', resizeHandler);
    }
    resizeObserver?.disconnect();
    chart?.dispose();
    chart = null;
  });

  return { chartRef, render, resize: resizeChart };
}

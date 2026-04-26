import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import * as echarts from 'echarts';

export function useROIChart(
  getChartData: () => { years: string[]; profits: number[]; cumulative: number[] } | null
) {
  const chartRef = ref<HTMLElement | null>(null);
  let chart: echarts.ECharts | null = null;
  let stopWatch: (() => void) | null = null;
  let resizeHandler: (() => void) | null = null;

  function render(): void {
    const data = getChartData();
    if (!chartRef.value) return;

    if (!data) {
      chart?.clear();
      return;
    }

    try {
      if (!chart) {
        chart = echarts.init(chartRef.value, 'dark');
      }

      chart.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis' },
        legend: { data: ['年现金流', '累计现金流'], bottom: 0 },
        grid: { top: '15%', left: '10%', right: '5%', bottom: '15%' },
        xAxis: { type: 'category', data: data.years },
        yAxis: { type: 'value', splitLine: { lineStyle: { color: '#333' } } },
        series: [
          { name: '年现金流', type: 'bar', data: data.profits, itemStyle: { color: '#10b981' } },
          { name: '累计现金流', type: 'line', data: data.cumulative, smooth: true, itemStyle: { color: '#3b82f6' }, areaStyle: { opacity: 0.1 } }
        ]
      });
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

    resizeHandler = () => chart?.resize();
    window.addEventListener('resize', resizeHandler);
  });

  onUnmounted(() => {
    stopWatch?.();
    if (resizeHandler) {
      window.removeEventListener('resize', resizeHandler);
    }
    chart?.dispose();
    chart = null;
  });

  return { chartRef, render };
}

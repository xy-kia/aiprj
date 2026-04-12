<template>
  <div class="chart-radar">
    <div ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import type { ECharts } from 'echarts'

interface Props {
  data: {
    dimensions: string[]
    scores: number[]
  }
  title?: string
  height?: number
}

const props = withDefaults(defineProps<Props>(), {
  title: '技能评估雷达图',
  height: 300
})

const chartRef = ref<HTMLDivElement>()
let chart: ECharts | null = null

const initChart = () => {
  if (!chartRef.value) return

  chart = echarts.init(chartRef.value)

  const option = {
    title: {
      text: props.title,
      left: 'center'
    },
    tooltip: {
      trigger: 'item'
    },
    radar: {
      indicator: props.data.dimensions.map((name, index) => ({
        name,
        max: 100,
        min: 0
      })),
      center: ['50%', '50%'],
      radius: '60%'
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: props.data.scores,
            name: '当前评分',
            areaStyle: {
              color: 'rgba(64, 158, 255, 0.2)'
            },
            lineStyle: {
              color: '#409eff',
              width: 2
            },
            itemStyle: {
              color: '#409eff'
            }
          }
        ]
      }
    ]
  }

  chart.setOption(option)
}

const resizeChart = () => {
  chart?.resize()
}

watch(() => props.data, () => {
  if (chart) {
    chart.dispose()
    initChart()
  }
}, { deep: true })

onMounted(() => {
  initChart()
  window.addEventListener('resize', resizeChart)
})

onUnmounted(() => {
  if (chart) {
    chart.dispose()
    chart = null
  }
  window.removeEventListener('resize', resizeChart)
})
</script>

<style scoped>
.chart-radar {
  width: 100%;
}

.chart-container {
  width: 100%;
  height: v-bind(height + 'px');
}
</style>
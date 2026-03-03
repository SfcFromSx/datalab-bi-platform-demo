import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';

interface ChartRendererProps {
  option: EChartsOption;
  height?: string;
}

export default function ChartRenderer({ option, height = '400px' }: ChartRendererProps) {
  return (
    <div style={{ height }} className="w-full">
      <ReactECharts
        option={option}
        style={{ height: '100%', width: '100%' }}
        opts={{ renderer: 'canvas' }}
        notMerge
        lazyUpdate
      />
    </div>
  );
}

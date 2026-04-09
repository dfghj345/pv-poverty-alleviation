/**
 * 格式化金额 (支持自动转换为 "万" 或 "亿" 并保留小数)
 * @param value 金额数值
 * @param decimals 保留小数位数，默认 2
 */
export const formatCurrency = (value: number, decimals: number = 2): string => {
  if (value === undefined || value === null || isNaN(value)) return '¥0.00';
  
  const absValue = Math.abs(value);
  if (absValue >= 100000000) {
    return `¥ ${(value / 100000000).toFixed(decimals)} 亿`;
  } else if (absValue >= 10000) {
    return `¥ ${(value / 10000).toFixed(decimals)} 万`;
  }
  
  // 使用浏览器内置的 Intl.NumberFormat 实现标准千分位
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(value);
};

/**
 * 格式化装机容量 (kW 自动转 MW)
 * @param kw 容量数值 (千瓦)
 */
export const formatPower = (kw: number): string => {
  if (kw === undefined || kw === null || isNaN(kw)) return '0 kW';
  
  if (kw >= 1000) {
    return `${(kw / 1000).toFixed(2)} MW`;
  }
  return `${kw.toFixed(1)} kW`;
};

/**
 * 计算净现值 (NPV) - 前端纯函数版估算
 * 公式：NPV = sum( R_t / (1 + i)^t ) - C_0
 * @param discountRate 折现率 (如 0.06)
 * @param cashFlows 现金流数组，第0项必须是初始投资(负数)，后续为每年的净现金流
 */
export const calculateNPV = (discountRate: number, cashFlows: number[]): number => {
  if (!cashFlows || cashFlows.length === 0) return 0;
  
  return cashFlows.reduce((npv, cashFlow, year) => {
    return npv + (cashFlow / Math.pow(1 + discountRate, year));
  }, 0);
};
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { getCostsApi, type CostItem } from '@/api/cost';
import { getRegionProvincesApi } from '@/api/region';

const emit = defineEmits<{
  (e: 'apply-cost', payload: { province: string | null; unit_cost_yuan_per_kw: number }): void;
}>();

const category = ref<string>('total');
const province = ref<string>('');
const provinces = ref<string[]>([]);
const limit = ref<number>(50);

const loading = ref(false);
const loadingProvinces = ref(false);
const errorMsg = ref<string | null>(null);
const rows = ref<CostItem[]>([]);

const totalShown = computed(() => rows.value.length);

async function loadProvinces(): Promise<void> {
  loadingProvinces.value = true;
  try {
    provinces.value = await getRegionProvincesApi('cost');
  } catch (e: any) {
    errorMsg.value = e?.message ?? '加载省份失败';
  } finally {
    loadingProvinces.value = false;
  }
}

async function query(): Promise<void> {
  loading.value = true;
  errorMsg.value = null;
  try {
    const data = await getCostsApi({
      category: category.value || undefined,
      province: province.value || undefined,
      limit: limit.value
    });
    rows.value = data;
  } catch (e: any) {
    errorMsg.value = e?.message ?? '查询失败';
    rows.value = [];
  } finally {
    loading.value = false;
  }
}

function apply(row: CostItem): void {
  const unit = row.unit_cost_yuan_per_kw;
  if (unit == null) {
    errorMsg.value = '该条目缺少单位造价，无法应用到测算';
    return;
  }
  emit('apply-cost', { province: row.province ?? null, unit_cost_yuan_per_kw: unit });
}

onMounted(async () => {
  await loadProvinces();
});
</script>

<template>
  <div class="bg-white dark:bg-dark-card rounded-xl p-6 shadow-md border border-gray-100 dark:border-gray-800">
    <div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-4">
      <div>
        <h3 class="text-xl font-bold text-gray-900 dark:text-dark-text">光伏成本（可应用到总投资）</h3>
        <p class="text-sm text-gray-500 dark:text-dark-text/60 mt-1">
          省份改为下拉选择，避免自由输入造成筛选误差。
        </p>
      </div>
      <div class="flex flex-wrap gap-3 items-end">
        <div>
          <label class="block text-xs text-gray-500 dark:text-dark-text/60 mb-1">类别</label>
          <select v-model="category"
                  class="w-36 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-dark-bg text-sm">
            <option value="total">综合</option>
            <option value="module">组件</option>
            <option value="inverter">逆变器</option>
            <option value="construction">施工</option>
            <option value="opex">运维</option>
          </select>
        </div>
        <div>
          <label class="block text-xs text-gray-500 dark:text-dark-text/60 mb-1">省份</label>
          <select
            v-model="province"
            class="w-36 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-dark-bg text-sm"
            :disabled="loadingProvinces"
          >
            <option value="">全部省份</option>
            <option v-for="p in provinces" :key="p" :value="p">{{ p }}</option>
          </select>
        </div>
        <div>
          <label class="block text-xs text-gray-500 dark:text-dark-text/60 mb-1">条数</label>
          <input v-model.number="limit" type="number" min="1" max="2000"
                 class="w-24 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-dark-bg text-sm" />
        </div>
        <button @click="query"
                class="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium disabled:opacity-60"
                :disabled="loading">
          {{ loading ? '查询中...' : '查询' }}
        </button>
      </div>
    </div>

    <div v-if="errorMsg" class="mb-4 text-sm text-red-600 dark:text-red-400">
      {{ errorMsg }}
    </div>

    <div class="flex items-center justify-between text-sm text-gray-600 dark:text-dark-text/70 mb-3">
      <span>当前展示：{{ totalShown }} 条</span>
      <span class="text-xs">点击“应用”会更新测算的总投资</span>
    </div>

    <div class="overflow-auto rounded-lg border border-gray-100 dark:border-gray-800">
      <table class="min-w-full text-sm">
        <thead class="bg-gray-50 dark:bg-dark-bg">
          <tr class="text-left text-gray-600 dark:text-dark-text/70">
            <th class="px-4 py-3 font-medium">名称</th>
            <th class="px-4 py-3 font-medium">省份</th>
            <th class="px-4 py-3 font-medium">单位造价(元/kW)</th>
            <th class="px-4 py-3 font-medium">单价(元/W)</th>
            <th class="px-4 py-3 font-medium">日期</th>
            <th class="px-4 py-3 font-medium">操作</th>
          </tr>
        </thead>
        <tbody class="bg-white dark:bg-dark-card">
          <tr v-for="(r, idx) in rows" :key="`${r.name}-${idx}`" class="border-t border-gray-100 dark:border-gray-800">
            <td class="px-4 py-3 text-gray-900 dark:text-dark-text">{{ r.name }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">{{ r.province ?? '全国' }}</td>
            <td class="px-4 py-3 text-gray-900 dark:text-dark-text">{{ r.unit_cost_yuan_per_kw ?? '-' }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">{{ r.component_price_yuan_per_w ?? '-' }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">{{ r.effective_date ?? '-' }}</td>
            <td class="px-4 py-3">
              <button @click="apply(r)"
                      class="px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-medium">
                应用
              </button>
            </td>
          </tr>
          <tr v-if="rows.length === 0" class="border-t border-gray-100 dark:border-gray-800">
            <td class="px-4 py-6 text-center text-gray-500 dark:text-dark-text/60" colspan="6">
              暂无数据。请先运行 data_pipeline 入库，然后点击查询。
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

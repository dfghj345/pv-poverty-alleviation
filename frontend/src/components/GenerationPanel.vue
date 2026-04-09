<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { getGenerationsApi, type GenerationItem } from '@/api/generation';
import { getRegionProvincesApi } from '@/api/region';

const province = ref<string>('');
const provinces = ref<string[]>([]);
const projectType = ref<string>('');
const limit = ref<number>(50);
const loading = ref(false);
const loadingProvinces = ref(false);
const errorMsg = ref<string | null>(null);
const rows = ref<GenerationItem[]>([]);

const totalShown = computed(() => rows.value.length);

async function loadProvinces(): Promise<void> {
  loadingProvinces.value = true;
  try {
    provinces.value = await getRegionProvincesApi('generation');
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
    const data = await getGenerationsApi({
      province: province.value || undefined,
      project_type: projectType.value.trim() || undefined,
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

onMounted(async () => {
  await loadProvinces();
});
</script>

<template>
  <div class="bg-white dark:bg-dark-card rounded-xl p-6 shadow-md border border-gray-100 dark:border-gray-800">
    <div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-4">
      <div>
        <h3 class="text-xl font-bold text-gray-900 dark:text-dark-text">历史发电/示范项目（结构化）</h3>
        <p class="text-sm text-gray-500 dark:text-dark-text/60 mt-1">
          省份筛选统一改为下拉，减少手动输入错误。
        </p>
      </div>
      <div class="flex flex-wrap gap-3 items-end">
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
          <label class="block text-xs text-gray-500 dark:text-dark-text/60 mb-1">类型</label>
          <input v-model="projectType" type="text" placeholder="如：示范项目"
                 class="w-36 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-dark-bg text-sm" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 dark:text-dark-text/60 mb-1">条数</label>
          <input v-model.number="limit" type="number" min="1" max="2000"
                 class="w-24 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-dark-bg text-sm" />
        </div>
        <button @click="query"
                class="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium disabled:opacity-60"
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
      <span class="text-xs">可按省份/类型过滤</span>
    </div>

    <div class="overflow-auto rounded-lg border border-gray-100 dark:border-gray-800">
      <table class="min-w-full text-sm">
        <thead class="bg-gray-50 dark:bg-dark-bg">
          <tr class="text-left text-gray-600 dark:text-dark-text/70">
            <th class="px-4 py-3 font-medium">项目</th>
            <th class="px-4 py-3 font-medium">省份</th>
            <th class="px-4 py-3 font-medium">容量(kW)</th>
            <th class="px-4 py-3 font-medium">年发电(kWh)</th>
            <th class="px-4 py-3 font-medium">年收益(元)</th>
            <th class="px-4 py-3 font-medium">类型</th>
            <th class="px-4 py-3 font-medium">年份</th>
          </tr>
        </thead>
        <tbody class="bg-white dark:bg-dark-card">
          <tr v-for="(r, idx) in rows" :key="`${r.project_name}-${idx}`" class="border-t border-gray-100 dark:border-gray-800">
            <td class="px-4 py-3 text-gray-900 dark:text-dark-text">{{ r.project_name }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">{{ r.province ?? '-' }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">{{ r.capacity_kw ?? '-' }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">{{ r.annual_generation_kwh ?? '-' }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">{{ r.annual_income_yuan ?? '-' }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">{{ r.project_type ?? '-' }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">{{ r.effective_date ?? '-' }}</td>
          </tr>
          <tr v-if="rows.length === 0" class="border-t border-gray-100 dark:border-gray-800">
            <td class="px-4 py-6 text-center text-gray-500 dark:text-dark-text/60" colspan="7">
              暂无数据。请先运行 data_pipeline 入库，然后点击查询。
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

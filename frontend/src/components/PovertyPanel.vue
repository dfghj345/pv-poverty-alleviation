<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { getPovertyCountiesApi, type PovertyCountyItem } from '@/api/poverty';
import { getRegionCitiesApi, getRegionProvincesApi } from '@/api/region';

const province = ref<string>('');
const city = ref<string>('');
const provinces = ref<string[]>([]);
const cities = ref<string[]>([]);

const limit = ref<number>(50);
const loading = ref(false);
const loadingProvinces = ref(false);
const loadingCities = ref(false);
const errorMsg = ref<string | null>(null);
const rows = ref<PovertyCountyItem[]>([]);

const totalShown = computed(() => rows.value.length);

async function loadProvinces(): Promise<void> {
  loadingProvinces.value = true;
  try {
    provinces.value = await getRegionProvincesApi('poverty');
  } catch (e: any) {
    errorMsg.value = e?.message ?? '加载省份失败';
  } finally {
    loadingProvinces.value = false;
  }
}

async function loadCities(nextProvince: string): Promise<void> {
  cities.value = [];
  city.value = '';
  if (!nextProvince) {
    return;
  }
  loadingCities.value = true;
  try {
    cities.value = await getRegionCitiesApi({ province: nextProvince, domain: 'poverty' });
  } catch (e: any) {
    errorMsg.value = e?.message ?? '加载城市失败';
  } finally {
    loadingCities.value = false;
  }
}

watch(province, (value) => {
  void loadCities(value);
});

async function query(): Promise<void> {
  loading.value = true;
  errorMsg.value = null;
  try {
    const data = await getPovertyCountiesApi({
      province: province.value || undefined,
      city: city.value || undefined,
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
        <h3 class="text-xl font-bold text-gray-900 dark:text-dark-text">贫困县/乡村振兴区域（基础数据）</h3>
        <p class="text-sm text-gray-500 dark:text-dark-text/60 mt-1">
          省市联动筛选，避免手工输入导致的脏数据。
        </p>
      </div>
      <div class="flex flex-wrap gap-3 items-end">
        <div>
          <label class="block text-xs text-gray-500 dark:text-dark-text/60 mb-1">省份</label>
          <select
            v-model="province"
            class="w-40 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-dark-bg text-sm"
            :disabled="loadingProvinces"
          >
            <option value="">全部省份</option>
            <option v-for="p in provinces" :key="p" :value="p">{{ p }}</option>
          </select>
        </div>

        <div>
          <label class="block text-xs text-gray-500 dark:text-dark-text/60 mb-1">城市</label>
          <select
            v-model="city"
            class="w-40 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-dark-bg text-sm"
            :disabled="!province || loadingCities"
          >
            <option value="">全部城市</option>
            <option v-for="c in cities" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>

        <div>
          <label class="block text-xs text-gray-500 dark:text-dark-text/60 mb-1">条数</label>
          <input v-model.number="limit" type="number" min="1" max="2000"
                 class="w-24 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-dark-bg text-sm" />
        </div>
        <button @click="query"
                class="px-4 py-2 rounded-lg bg-cyan-500 hover:bg-cyan-600 text-white text-sm font-medium disabled:opacity-60"
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
      <span class="text-xs">支持按省份或省市联合筛选</span>
    </div>

    <div class="overflow-auto rounded-lg border border-gray-100 dark:border-gray-800">
      <table class="min-w-full text-sm">
        <thead class="bg-gray-50 dark:bg-dark-bg">
          <tr class="text-left text-gray-600 dark:text-dark-text/70">
            <th class="px-4 py-3 font-medium">省份</th>
            <th class="px-4 py-3 font-medium">市/州</th>
            <th class="px-4 py-3 font-medium">县/区</th>
            <th class="px-4 py-3 font-medium">人口</th>
            <th class="px-4 py-3 font-medium">人均收入(元)</th>
            <th class="px-4 py-3 font-medium">标签</th>
          </tr>
        </thead>
        <tbody class="bg-white dark:bg-dark-card">
          <tr v-for="(r, idx) in rows" :key="`${r.adcode ?? ''}-${r.county}-${idx}`" class="border-t border-gray-100 dark:border-gray-800">
            <td class="px-4 py-3 text-gray-900 dark:text-dark-text">{{ r.province }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">{{ r.city ?? '-' }}</td>
            <td class="px-4 py-3 text-gray-900 dark:text-dark-text">{{ r.county }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">{{ r.population ?? '-' }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">{{ r.income_per_capita_yuan ?? '-' }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">{{ r.tags ?? '-' }}</td>
          </tr>
          <tr v-if="rows.length === 0" class="border-t border-gray-100 dark:border-gray-800">
            <td class="px-4 py-6 text-center text-gray-500 dark:text-dark-text/60" colspan="6">
              暂无数据。 
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

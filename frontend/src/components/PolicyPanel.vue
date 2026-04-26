<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { getEnergyPoliciesApi, getPoliciesApi, type EnergyPolicyItem, type PolicyTariffItem } from '@/api/policy';
import { getRegionProvincesApi } from '@/api/region';

const emit = defineEmits<{
  (e: 'apply-price', payload: { province: string; electricity_price: number }): void;
}>();

const province = ref<string>('');
const provinces = ref<string[]>([]);
const limit = ref<number>(50);
const includeSubsidy = ref<boolean>(true);

const loading = ref(false);
const loadingProvinces = ref(false);
const errorMsg = ref<string | null>(null);
const rows = ref<PolicyTariffItem[]>([]);
const energyRows = ref<EnergyPolicyItem[]>([]);

const totalShown = computed(() => rows.value.length);

function calcFinalPrice(row: PolicyTariffItem): number {
  const base = row.benchmark_price_yuan_per_kwh ?? 0;
  const sub = row.subsidy_yuan_per_kwh ?? 0;
  return includeSubsidy.value ? base + sub : base;
}

async function loadProvinces(): Promise<void> {
  loadingProvinces.value = true;
  try {
    provinces.value = await getRegionProvincesApi('policy');
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
    const data = await getPoliciesApi({
      province: province.value || undefined,
      limit: limit.value
    });
    rows.value = data;
    await loadEnergyPolicies();
  } catch (e: any) {
    errorMsg.value = e?.message ?? '查询失败';
    rows.value = [];
    energyRows.value = [];
  } finally {
    loading.value = false;
  }
}

async function loadEnergyPolicies(): Promise<void> {
  try {
    energyRows.value = await getEnergyPoliciesApi({ limit: 10 });
  } catch {
    energyRows.value = [];
  }
}

function apply(row: PolicyTariffItem): void {
  const price = calcFinalPrice(row);
  emit('apply-price', { province: row.province, electricity_price: price });
}

onMounted(async () => {
  await loadProvinces();
  await loadEnergyPolicies();
});
</script>

<template>
  <div class="bg-white dark:bg-dark-card rounded-xl p-6 shadow-md border border-gray-100 dark:border-gray-800">
    <div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-4">
      <div>
        <h3 class="text-xl font-bold text-gray-900 dark:text-dark-text">政策与电价（可应用到测算）</h3>
        <p class="text-sm text-gray-500 dark:text-dark-text/60 mt-1">
          省份改为下拉选择，避免手输造成查询失败。
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
          <label class="block text-xs text-gray-500 dark:text-dark-text/60 mb-1">条数</label>
          <input v-model.number="limit" type="number" min="1" max="2000"
                 class="w-24 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-dark-bg text-sm" />
        </div>
        <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-dark-text/80 mb-1">
          <input v-model="includeSubsidy" type="checkbox" class="accent-emerald-500" />
          补贴计入电价
        </label>
        <button @click="query"
                class="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-sm font-medium disabled:opacity-60"
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
      <span class="text-xs">点击“应用”会把电价写入收益测算表单</span>
    </div>

    <div class="overflow-auto rounded-lg border border-gray-100 dark:border-gray-800">
      <table class="min-w-full text-sm">
        <thead class="bg-gray-50 dark:bg-dark-bg">
          <tr class="text-left text-gray-600 dark:text-dark-text/70">
            <th class="px-4 py-3 font-medium">省份</th>
            <th class="px-4 py-3 font-medium">电价(元/kWh)</th>
            <th class="px-4 py-3 font-medium">补贴(元/kWh)</th>
            <th class="px-4 py-3 font-medium">日期</th>
            <th class="px-4 py-3 font-medium">来源</th>
            <th class="px-4 py-3 font-medium">操作</th>
          </tr>
        </thead>
        <tbody class="bg-white dark:bg-dark-card">
          <tr v-for="(r, idx) in rows" :key="`${r.province}-${idx}`" class="border-t border-gray-100 dark:border-gray-800">
            <td class="px-4 py-3 text-gray-900 dark:text-dark-text">{{ r.province }}</td>
            <td class="px-4 py-3 text-gray-900 dark:text-dark-text">{{ r.benchmark_price_yuan_per_kwh }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">{{ r.subsidy_yuan_per_kwh ?? '-' }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">{{ r.policy_date ?? '-' }}</td>
            <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">
              <a v-if="r.source_url" :href="r.source_url" target="_blank" class="text-emerald-600 hover:underline">链接</a>
              <span v-else>-</span>
            </td>
            <td class="px-4 py-3">
              <button @click="apply(r)"
                      class="px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-medium">
                应用
              </button>
            </td>
          </tr>
          <tr v-if="rows.length === 0" class="border-t border-gray-100 dark:border-gray-800">
            <td class="px-4 py-6 text-center text-gray-500 dark:text-dark-text/60" colspan="6">
              暂无数据。 
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="mt-5 rounded-lg border border-gray-100 dark:border-gray-800 overflow-hidden">
      <div class="px-4 py-3 bg-gray-50 dark:bg-dark-bg text-sm font-medium text-gray-700 dark:text-dark-text/80">
        国家能源局政策动态（energy_policy_table）
      </div>
      <div class="divide-y divide-gray-100 dark:divide-gray-800">
        <a
          v-for="item in energyRows"
          :key="item.url"
          :href="item.url"
          target="_blank"
          class="block px-4 py-3 hover:bg-gray-50 dark:hover:bg-dark-bg"
        >
          <div class="text-sm text-gray-900 dark:text-dark-text line-clamp-1">{{ item.title }}</div>
          <div class="mt-1 text-xs text-gray-500 dark:text-dark-text/60">
            {{ item.publish_date ?? '未知日期' }} · {{ item.source }}
          </div>
        </a>
        <div v-if="energyRows.length === 0" class="px-4 py-4 text-sm text-gray-500 dark:text-dark-text/60">
          暂无政策动态。
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { getEnergyPoliciesApi, getPoliciesApi, type EnergyPolicyItem, type PolicyTariffItem } from '@/api/policy';
import { getRegionProvincesApi } from '@/api/region';
import { useMobilePager } from '@/composables/useMobilePager';

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
const mobilePanel = ref<'form' | 'result'>('form');

const totalShown = computed(() => rows.value.length);
const hasResult = computed(() => rows.value.length > 0);
const latestEnergyRow = computed(() => energyRows.value[0] ?? null);
const {
  page: mobilePage,
  totalPages: mobileTotalPages,
  pagedItems: mobileRows,
  canPrev: canPrevMobilePage,
  canNext: canNextMobilePage,
  next: nextMobilePage,
  prev: prevMobilePage,
  onTouchStart,
  onTouchEnd,
} = useMobilePager(rows, 1);

function calcFinalPrice(row: PolicyTariffItem): number {
  const base = row.benchmark_price_yuan_per_kwh ?? 0;
  const subsidy = row.subsidy_yuan_per_kwh ?? 0;
  return includeSubsidy.value ? base + subsidy : base;
}

async function loadProvinces(): Promise<void> {
  loadingProvinces.value = true;
  try {
    provinces.value = await getRegionProvincesApi('policy');
  } catch (error: any) {
    errorMsg.value = error?.message ?? '加载省份失败';
  } finally {
    loadingProvinces.value = false;
  }
}

async function loadEnergyPolicies(): Promise<void> {
  try {
    energyRows.value = await getEnergyPoliciesApi({ limit: 10 });
  } catch {
    energyRows.value = [];
  }
}

async function query(): Promise<boolean> {
  loading.value = true;
  errorMsg.value = null;

  try {
    rows.value = await getPoliciesApi({
      province: province.value || undefined,
      limit: limit.value,
    });
    await loadEnergyPolicies();
    return true;
  } catch (error: any) {
    errorMsg.value = error?.message ?? '查询失败';
    rows.value = [];
    energyRows.value = [];
    return false;
  } finally {
    loading.value = false;
  }
}

async function handleQuery(): Promise<void> {
  const success = await query();
  if (success && window.innerWidth < 768) {
    mobilePanel.value = 'result';
  }
}

function backToFilters(): void {
  mobilePanel.value = 'form';
}

function showResults(): void {
  mobilePanel.value = 'result';
}

function apply(row: PolicyTariffItem): void {
  emit('apply-price', {
    province: row.province,
    electricity_price: calcFinalPrice(row),
  });
}

onMounted(async () => {
  await loadProvinces();
  await loadEnergyPolicies();
});
</script>

<template>
  <section class="min-w-0 apple-card overflow-hidden">
    <div
      class="flex w-[200%] transition-transform duration-300 ease-out md:block md:w-full md:transition-none"
      :class="mobilePanel === 'result' ? '-translate-x-1/2 md:translate-x-0' : 'translate-x-0'"
    >
      <div class="min-w-0 w-1/2 shrink-0 p-4 sm:p-6 md:w-full lg:p-8">
        <div class="space-y-6">
          <div>
            <h3 class="text-xl font-bold tracking-[-0.03em] text-gray-900 dark:text-dark-text lg:text-[1.9rem]">政策与电价</h3>
            <p class="apple-compact-copy mt-1 text-gray-500 dark:text-dark-text/60">
              按省份查询政策电价，并直接应用到收益测算。
            </p>
          </div>
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <div class="min-w-0">
              <label class="mb-1 block text-xs text-gray-500 dark:text-dark-text/60">省份</label>
              <select
                v-model="province"
                class="apple-input"
                :disabled="loadingProvinces"
              >
                <option value="">全部省份</option>
                <option v-for="item in provinces" :key="item" :value="item">{{ item }}</option>
              </select>
            </div>
            <div class="min-w-0">
              <label class="mb-1 block text-xs text-gray-500 dark:text-dark-text/60">条数</label>
              <input
                v-model.number="limit"
                type="number"
                min="1"
                max="2000"
                class="apple-input"
              />
            </div>
            <label class="flex min-h-[44px] items-center gap-2 rounded-[18px] border border-slate-200 bg-[#f7f7fa] px-4 py-2 text-sm text-gray-700 dark:border-gray-700 dark:bg-dark-bg dark:text-dark-text/80">
              <input v-model="includeSubsidy" type="checkbox" class="accent-emerald-500" />
              补贴计入电价
            </label>
            <button
              class="apple-pill-primary w-full self-end"
              :disabled="loading"
              @click="handleQuery"
            >
              {{ loading ? '查询中...' : '查询' }}
            </button>
          </div>
        </div>

        <div v-if="errorMsg" class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300">
          {{ errorMsg }}
        </div>


        <button
          v-if="hasResult"
          type="button"
          class="apple-pill-secondary mt-4 w-full md:hidden"
          @click="showResults"
        >
          查看查询结果
        </button>
      </div>

      <div class="min-w-0 w-1/2 shrink-0 border-l border-gray-100 p-4 dark:border-gray-800 sm:p-6 md:w-full md:border-l-0 lg:p-8">
        <div class="mb-4 flex items-center justify-between gap-3">
          <div>
            <h4 class="text-lg font-semibold text-gray-900 dark:text-dark-text">政策结果与动态</h4>
            <p class="mt-1 text-sm text-gray-500 dark:text-dark-text/60">当前展示：{{ totalShown }} 条</p>
          </div>
          <button
            type="button"
            class="apple-pill-secondary min-h-[40px] px-4 py-2 md:hidden"
            @click="backToFilters"
          >
            返回筛选
          </button>
        </div>

        <div
          class="space-y-3 md:hidden"
          @touchstart.passive="onTouchStart"
          @touchend.passive="onTouchEnd"
        >
          <div v-if="rows.length === 0" class="rounded-lg border border-dashed border-gray-200 px-4 py-6 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-dark-text/60">
            暂无数据。
          </div>
          <article
            v-for="(row, index) in mobileRows"
            :key="`mobile-${row.province}-${index}`"
            class="apple-subcard p-4"
          >
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="text-sm font-semibold text-gray-900 dark:text-dark-text">{{ row.province }}</p>
                <p class="mt-1 text-xs text-gray-500 dark:text-dark-text/60">{{ row.policy_date ?? '-' }}</p>
              </div>
              <button
                type="button"
                class="apple-pill-primary min-h-[36px] px-3 py-2 text-xs"
                @click="apply(row)"
              >
                应用
              </button>
            </div>
            <div class="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div class="rounded-[18px] bg-white px-3 py-2 dark:bg-dark-card">
                <p class="text-xs text-gray-500 dark:text-dark-text/60">电价</p>
                <p class="mt-1 font-medium text-gray-900 dark:text-dark-text">{{ row.benchmark_price_yuan_per_kwh }}</p>
              </div>
              <div class="rounded-[18px] bg-white px-3 py-2 dark:bg-dark-card">
                <p class="text-xs text-gray-500 dark:text-dark-text/60">补贴</p>
                <p class="mt-1 font-medium text-gray-900 dark:text-dark-text">{{ row.subsidy_yuan_per_kwh ?? '-' }}</p>
              </div>
            </div>
          </article>

          <div v-if="rows.length > 0" class="apple-subcard flex items-center justify-between gap-3 px-3 py-2">
            <button
              type="button"
              class="min-h-[40px] rounded-lg px-3 text-sm font-medium text-slate-700 transition disabled:opacity-40 dark:text-dark-text/80"
              :disabled="!canPrevMobilePage"
              @click="prevMobilePage"
            >
              上一条
            </button>
            <span class="text-sm text-slate-500 dark:text-dark-text/60">{{ mobilePage + 1 }} / {{ mobileTotalPages }}</span>
            <button
              type="button"
              class="min-h-[40px] rounded-lg px-3 text-sm font-medium text-slate-700 transition disabled:opacity-40 dark:text-dark-text/80"
              :disabled="!canNextMobilePage"
              @click="nextMobilePage"
            >
              下一条
            </button>
          </div>
        </div>

        <div class="touch-scroll hidden overflow-x-auto rounded-lg border border-gray-100 dark:border-gray-800 md:block">
          <table class="min-w-full text-xs sm:text-sm">
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
              <tr v-for="(row, index) in rows" :key="`${row.province}-${index}`" class="border-t border-gray-100 dark:border-gray-800">
                <td class="px-4 py-3 text-gray-900 dark:text-dark-text">{{ row.province }}</td>
                <td class="px-4 py-3 text-gray-900 dark:text-dark-text">{{ row.benchmark_price_yuan_per_kwh }}</td>
                <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">{{ row.subsidy_yuan_per_kwh ?? '-' }}</td>
                <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">{{ row.policy_date ?? '-' }}</td>
                <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">
                  <a v-if="row.source_url" :href="row.source_url" target="_blank" class="text-emerald-600 hover:underline">链接</a>
                  <span v-else>-</span>
                </td>
                <td class="px-4 py-3">
                  <button
                    type="button"
                    class="apple-pill-primary min-h-[36px] px-4 py-2 text-xs"
                    @click="apply(row)"
                  >
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

        <div
          v-if="latestEnergyRow"
          class="apple-subcard mt-5 p-4 md:hidden"
        >
          <p class="text-xs uppercase tracking-[0.16em] text-slate-400">政策动态</p>
          <a :href="latestEnergyRow.url" target="_blank" class="mt-2 block text-sm font-medium text-slate-900 dark:text-dark-text">
            {{ latestEnergyRow.title }}
          </a>
          <p class="mt-2 text-xs text-slate-500 dark:text-dark-text/60">
            {{ latestEnergyRow.publish_date ?? '未知日期' }} · {{ latestEnergyRow.source }}
          </p>
        </div>

        <div class="mt-5 hidden overflow-hidden rounded-[22px] border border-gray-100 dark:border-gray-800 md:block">
          <div class="bg-gray-50 px-4 py-3 text-sm font-medium text-gray-700 dark:bg-dark-bg dark:text-dark-text/80">
            国家能源局政策动态
          </div>
          <div class="divide-y divide-gray-100 dark:divide-gray-800">
            <a
              v-for="item in energyRows"
              :key="item.url"
              :href="item.url"
              target="_blank"
              class="block px-4 py-3 hover:bg-gray-50 dark:hover:bg-dark-bg"
            >
              <div class="line-clamp-1 text-sm text-gray-900 dark:text-dark-text">{{ item.title }}</div>
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
    </div>
  </section>
</template>

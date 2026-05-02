<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { getGenerationsApi, type GenerationItem } from '@/api/generation';
import { getRegionProvincesApi } from '@/api/region';
import { useMobilePager } from '@/composables/useMobilePager';

const province = ref<string>('');
const provinces = ref<string[]>([]);
const projectType = ref<string>('');
const limit = ref<number>(50);

const loading = ref(false);
const loadingProvinces = ref(false);
const errorMsg = ref<string | null>(null);
const rows = ref<GenerationItem[]>([]);
const mobilePanel = ref<'form' | 'result'>('form');

const totalShown = computed(() => rows.value.length);
const hasResult = computed(() => rows.value.length > 0);
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

async function loadProvinces(): Promise<void> {
  loadingProvinces.value = true;
  try {
    provinces.value = await getRegionProvincesApi('generation');
  } catch (error: any) {
    errorMsg.value = error?.message ?? '加载省份失败';
  } finally {
    loadingProvinces.value = false;
  }
}

async function query(): Promise<boolean> {
  loading.value = true;
  errorMsg.value = null;

  try {
    rows.value = await getGenerationsApi({
      province: province.value || undefined,
      project_type: projectType.value.trim() || undefined,
      limit: limit.value,
    });
    return true;
  } catch (error: any) {
    errorMsg.value = error?.message ?? '查询失败';
    rows.value = [];
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

onMounted(async () => {
  await loadProvinces();
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
            <h3 class="text-xl font-bold tracking-[-0.03em] text-slate-900 dark:text-dark-text lg:text-[1.9rem]">发电量分析</h3>
            <p class="apple-compact-copy mt-1 text-slate-500 dark:text-dark-text/60">
              按省份和项目类型筛选发电数据，并在当前卡片查看结果。
            </p>
          </div>
          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <div class="min-w-0">
              <label class="mb-1 block text-xs text-slate-500 dark:text-dark-text/60">省份</label>
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
              <label class="mb-1 block text-xs text-slate-500 dark:text-dark-text/60">类型</label>
              <input
                v-model="projectType"
                type="text"
                placeholder="如：示范项目"
                class="apple-input"
              />
            </div>
            <div class="min-w-0">
              <label class="mb-1 block text-xs text-slate-500 dark:text-dark-text/60">条数</label>
              <input
                v-model.number="limit"
                type="number"
                min="1"
                max="2000"
                class="apple-input"
              />
            </div>
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

      <div class="min-w-0 w-1/2 shrink-0 border-l border-emerald-100/80 p-4 dark:border-slate-800 sm:p-6 md:w-full md:border-l-0 lg:p-8">
        <div class="mb-4 flex items-center justify-between gap-3">
          <div>
            <h4 class="text-lg font-semibold text-slate-900 dark:text-dark-text">发电量结果</h4>
            <p class="mt-1 text-sm text-slate-500 dark:text-dark-text/60">当前展示：{{ totalShown }} 条</p>
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
          <div v-if="rows.length === 0" class="rounded-lg border border-dashed border-emerald-200/80 bg-white/70 px-4 py-6 text-center text-sm text-slate-500 dark:border-gray-700 dark:text-dark-text/60">
            暂无数据。
          </div>
          <article
            v-for="(row, index) in mobileRows"
            :key="`mobile-${row.project_name}-${index}`"
            class="apple-subcard p-4"
          >
            <p class="text-sm font-semibold text-slate-900 dark:text-dark-text">{{ row.project_name }}</p>
            <p class="mt-1 text-xs text-slate-500 dark:text-dark-text/60">{{ row.province ?? '-' }} · {{ row.project_type ?? '-' }}</p>
            <div class="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div class="panel-soft-cell">
                <p class="text-xs text-slate-500 dark:text-dark-text/60">容量</p>
                <p class="mt-1 font-medium text-slate-900 dark:text-dark-text">{{ row.capacity_kw ?? '-' }} kW</p>
              </div>
              <div class="panel-soft-cell">
                <p class="text-xs text-slate-500 dark:text-dark-text/60">年发电</p>
                <p class="mt-1 font-medium text-slate-900 dark:text-dark-text">{{ row.annual_generation_kwh ?? '-' }} kWh</p>
              </div>
              <div class="panel-soft-cell col-span-2">
                <p class="text-xs text-slate-500 dark:text-dark-text/60">年收益</p>
                <p class="mt-1 font-medium text-slate-900 dark:text-dark-text">{{ row.annual_income_yuan ?? '-' }} 元</p>
              </div>
            </div>
          </article>

          <div v-if="rows.length > 0" class="apple-subcard flex items-center justify-between gap-3 px-3 py-2">
            <button
              type="button"
              class="panel-page-btn"
              :disabled="!canPrevMobilePage"
              @click="prevMobilePage"
            >
              上一条
            </button>
            <span class="text-sm text-slate-500 dark:text-dark-text/60">{{ mobilePage + 1 }} / {{ mobileTotalPages }}</span>
            <button
              type="button"
              class="panel-page-btn"
              :disabled="!canNextMobilePage"
              @click="nextMobilePage"
            >
              下一条
            </button>
          </div>
        </div>

        <div class="panel-table-shell touch-scroll hidden overflow-x-auto md:block">
          <table class="min-w-full text-xs sm:text-sm">
            <thead class="panel-table-head">
              <tr class="text-left dark:text-dark-text/70">
                <th class="px-4 py-3 font-medium">项目</th>
                <th class="px-4 py-3 font-medium">省份</th>
                <th class="px-4 py-3 font-medium">容量(kW)</th>
                <th class="px-4 py-3 font-medium">年发电(kWh)</th>
                <th class="px-4 py-3 font-medium">年收益(元)</th>
                <th class="px-4 py-3 font-medium">类型</th>
                <th class="px-4 py-3 font-medium">年份</th>
              </tr>
            </thead>
            <tbody class="bg-white/80 dark:bg-dark-card">
              <tr v-for="(row, index) in rows" :key="`${row.project_name}-${index}`" class="border-t border-emerald-100/70 transition hover:bg-emerald-50/50 dark:border-gray-800 dark:hover:bg-slate-900/40">
                <td class="px-4 py-3 text-slate-900 dark:text-dark-text">{{ row.project_name }}</td>
                <td class="px-4 py-3 text-slate-700 dark:text-dark-text/80">{{ row.province ?? '-' }}</td>
                <td class="px-4 py-3 text-slate-700 dark:text-dark-text/80">{{ row.capacity_kw ?? '-' }}</td>
                <td class="px-4 py-3 text-slate-700 dark:text-dark-text/80">{{ row.annual_generation_kwh ?? '-' }}</td>
                <td class="px-4 py-3 text-slate-700 dark:text-dark-text/80">{{ row.annual_income_yuan ?? '-' }}</td>
                <td class="px-4 py-3 text-slate-700 dark:text-dark-text/80">{{ row.project_type ?? '-' }}</td>
                <td class="px-4 py-3 text-slate-700 dark:text-dark-text/80">{{ row.effective_date ?? '-' }}</td>
              </tr>
              <tr v-if="rows.length === 0" class="border-t border-emerald-100/70 dark:border-gray-800">
                <td class="px-4 py-6 text-center text-slate-500 dark:text-dark-text/60" colspan="7">
                  暂无数据。
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>
</template>

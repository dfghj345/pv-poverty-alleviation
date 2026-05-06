<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { getCostsApi, type CostItem } from '@/api/cost';
import { getRegionProvincesApi } from '@/api/region';
import { useMobilePager } from '@/composables/useMobilePager';
import StableQueryCard from '@/components/StableQueryCard.vue';

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
const panelSide = ref<'form' | 'result'>('form');

const totalShown = computed(() => rows.value.length);
const hasResult = computed(() => rows.value.length > 0);
const categoryLabel = computed(() => {
  const labels: Record<string, string> = {
    total: '综合',
    module: '组件',
    inverter: '逆变器',
    construction: '施工',
    opex: '运维',
  };
  return labels[category.value] ?? '全部';
});
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
    provinces.value = await getRegionProvincesApi('cost');
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
    rows.value = await getCostsApi({
      category: category.value || undefined,
      province: province.value || undefined,
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
  if (success) {
    panelSide.value = 'result';
  }
}

function backToFilters(): void {
  panelSide.value = 'form';
}

function showResults(): void {
  panelSide.value = 'result';
}

function apply(row: CostItem): void {
  const unitCost = row.unit_cost_yuan_per_kw;
  if (unitCost == null) {
    errorMsg.value = '该条目缺少单位造价，无法应用到测算';
    return;
  }

  emit('apply-cost', {
    province: row.province ?? null,
    unit_cost_yuan_per_kw: unitCost,
  });
}

onMounted(async () => {
  await loadProvinces();
});
</script>

<template>
  <StableQueryCard :active="panelSide === 'result' ? 'back' : 'front'">
    <template #front>
      <div class="business-card-scroll">
        <div>
          <h3 class="text-xl font-bold tracking-[-0.03em] text-slate-900 dark:text-dark-text lg:text-[1.9rem]">光伏成本</h3>
          <p class="apple-compact-copy mt-1 text-slate-500 dark:text-dark-text/60">
            按类别与省份筛选单位造价，并回填到收益测算。
          </p>
        </div>

        <div class="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <div class="min-w-0">
            <label class="mb-1 block text-xs text-slate-500 dark:text-dark-text/60">类别</label>
            <select
              v-model="category"
              class="apple-input"
            >
              <option value="total">综合</option>
              <option value="module">组件</option>
              <option value="inverter">逆变器</option>
              <option value="construction">施工</option>
              <option value="opex">运维</option>
            </select>
          </div>
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
            <label class="mb-1 block text-xs text-slate-500 dark:text-dark-text/60">条数</label>
            <input
              v-model.number="limit"
              type="number"
              min="1"
              max="2000"
              class="apple-input"
            />
          </div>
        </div>

        <div class="business-card-actions">
          <button
            class="apple-pill-primary"
            :disabled="loading"
            @click="handleQuery"
          >
            {{ loading ? '查询中...' : '查询' }}
          </button>
          <button
            v-if="hasResult"
            type="button"
            class="apple-pill-secondary"
            @click="showResults"
          >
            查看结果
          </button>
        </div>

        <div v-if="errorMsg" class="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300">
          {{ errorMsg }}
        </div>

        <div class="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div class="apple-subcard border-emerald-100/80 bg-emerald-50/60 p-3 sm:p-4 dark:border-emerald-800/30 dark:bg-emerald-900/12">
            <p class="text-xs text-slate-500 dark:text-dark-text/60">当前类别</p>
            <p class="mt-1 truncate text-lg font-semibold text-slate-900 dark:text-dark-text">{{ categoryLabel }}</p>
          </div>
          <div class="apple-subcard border-cyan-100/80 bg-cyan-50/60 p-3 sm:p-4 dark:border-cyan-800/30 dark:bg-cyan-900/12">
            <p class="text-xs text-slate-500 dark:text-dark-text/60">当前省份</p>
            <p class="mt-1 truncate text-lg font-semibold text-slate-900 dark:text-dark-text">{{ province || '全部' }}</p>
          </div>
          <div class="apple-subcard border-sky-100/80 bg-sky-50/60 p-3 sm:p-4 dark:border-sky-800/30 dark:bg-sky-900/12">
            <p class="text-xs text-slate-500 dark:text-dark-text/60">已加载结果</p>
            <p class="mt-1 text-lg font-semibold text-slate-900 dark:text-dark-text">{{ totalShown }} 条</p>
          </div>
        </div>
      </div>
    </template>

    <template #back>
      <div class="business-card-scroll business-card-scroll--result">
        <div class="business-result-header">
          <div>
            <h4 class="text-lg font-semibold text-slate-900 dark:text-dark-text">成本结果</h4>
            <p class="mt-1 text-sm text-slate-500 dark:text-dark-text/60">当前展示：{{ totalShown }} 条</p>
          </div>
          <div class="business-result-actions">
            <button
              type="button"
              class="apple-pill-secondary min-h-[40px] px-4 py-2"
              @click="backToFilters"
            >
              返回筛选
            </button>
          </div>
        </div>

        <div v-if="errorMsg" class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300">
          {{ errorMsg }}
        </div>

        <div class="business-result-body">
          <div
            class="space-y-3 md:hidden"
            @touchstart.passive="onTouchStart"
            @touchend.passive="onTouchEnd"
          >
            <div v-if="rows.length === 0" class="rounded-lg border border-dashed border-emerald-200/80 bg-white/70 px-4 py-6 text-center text-sm text-slate-500 dark:border-gray-700 dark:text-dark-text/60">
              暂无数据，请更换条件重试。
            </div>
            <article
              v-for="(row, index) in mobileRows"
              :key="`mobile-${row.name}-${index}`"
              class="apple-subcard p-4"
            >
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="text-sm font-semibold text-slate-900 dark:text-dark-text">{{ row.name }}</p>
                  <p class="mt-1 text-xs text-slate-500 dark:text-dark-text/60">{{ row.province ?? '全国' }}</p>
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
                <div class="panel-soft-cell">
                  <p class="text-xs text-slate-500 dark:text-dark-text/60">单位造价</p>
                  <p class="mt-1 font-medium text-slate-900 dark:text-dark-text">{{ row.unit_cost_yuan_per_kw ?? '-' }}</p>
                </div>
                <div class="panel-soft-cell">
                  <p class="text-xs text-slate-500 dark:text-dark-text/60">单价</p>
                  <p class="mt-1 font-medium text-slate-900 dark:text-dark-text">{{ row.component_price_yuan_per_w ?? '-' }}</p>
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

          <div class="panel-table-shell business-result-table hidden md:block">
            <div class="touch-scroll overflow-x-auto">
              <table class="min-w-full text-xs sm:text-sm">
                <thead class="panel-table-head">
                  <tr class="text-left dark:text-dark-text/70">
                    <th class="px-4 py-3 font-medium">名称</th>
                    <th class="px-4 py-3 font-medium">省份</th>
                    <th class="px-4 py-3 font-medium">单位造价(元/kW)</th>
                    <th class="px-4 py-3 font-medium">单价(元/W)</th>
                    <th class="px-4 py-3 font-medium">日期</th>
                    <th class="px-4 py-3 font-medium">操作</th>
                  </tr>
                </thead>
                <tbody class="bg-white/80 dark:bg-dark-card">
                  <tr v-for="(row, index) in rows" :key="`${row.name}-${index}`" class="border-t border-emerald-100/70 transition hover:bg-emerald-50/50 dark:border-gray-800 dark:hover:bg-slate-900/40">
                    <td class="px-4 py-3 text-slate-900 dark:text-dark-text">{{ row.name }}</td>
                    <td class="px-4 py-3 text-slate-700 dark:text-dark-text/80">{{ row.province ?? '全国' }}</td>
                    <td class="px-4 py-3 text-slate-900 dark:text-dark-text">{{ row.unit_cost_yuan_per_kw ?? '-' }}</td>
                    <td class="px-4 py-3 text-slate-700 dark:text-dark-text/80">{{ row.component_price_yuan_per_w ?? '-' }}</td>
                    <td class="px-4 py-3 text-slate-700 dark:text-dark-text/80">{{ row.effective_date ?? '-' }}</td>
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
                  <tr v-if="rows.length === 0" class="border-t border-emerald-100/70 dark:border-gray-800">
                    <td class="px-4 py-6 text-center text-slate-500 dark:text-dark-text/60" colspan="6">
                      暂无数据，请更换条件重试。
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </template>
  </StableQueryCard>
</template>

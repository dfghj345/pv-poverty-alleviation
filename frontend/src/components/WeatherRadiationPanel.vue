<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { getWeatherRadiationApi, type WeatherRadiationItem } from '@/api/weather';
import { getRegionCitiesApi, getRegionProvincesApi, reverseRegionByCoordinateApi } from '@/api/region';
import { useMobilePager } from '@/composables/useMobilePager';
import { useProjectStore } from '@/store/project';

const province = ref<string>('');
const city = ref<string>('');
const provinces = ref<string[]>([]);
const cities = ref<string[]>([]);

const limit = ref<number>(30);
const loading = ref(false);
const loadingProvinces = ref(false);
const loadingCities = ref(false);
const errorMsg = ref<string | null>(null);
const infoMsg = ref<string | null>(null);
const rows = ref<WeatherRadiationItem[]>([]);
const showMobileDetails = ref(false);

const projectStore = useProjectStore();

const latest = computed(() => rows.value[0] ?? null);
const summary = computed(() => {
  const annual = rows.value.find(r => r.annual_radiation_sum_kwh_m2 != null)?.annual_radiation_sum_kwh_m2 ?? null;
  const eqh = rows.value.find(r => r.equivalent_hours_h != null)?.equivalent_hours_h ?? null;
  return { annual, eqh };
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
    provinces.value = await getRegionProvincesApi('weather');
    if (!province.value && provinces.value.length > 0) {
      province.value = provinces.value[0];
    }
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
    cities.value = await getRegionCitiesApi({ province: nextProvince, domain: 'weather' });
    if (cities.value.length > 0) {
      city.value = cities.value[0];
    } else {
      infoMsg.value = `省份 ${nextProvince} 暂无可用城市数据`;
    }
  } catch (e: any) {
    errorMsg.value = e?.message ?? '加载城市失败';
  } finally {
    loadingCities.value = false;
  }
}

watch(
  province,
  (value) => {
    infoMsg.value = null;
    void loadCities(value);
  },
  { immediate: false }
);

watch(
  () => projectStore.selectedMapPoint,
  async (point) => {
    if (!point) return;
    infoMsg.value = `已从地图选点：(${point.latitude.toFixed(6)}, ${point.longitude.toFixed(6)})`;

    // 选点带有省市时直接填充，否则尝试后端反查最近城市。
    const p = point.province?.trim();
    const c = point.city?.trim();
    if (p && c) {
      if (province.value !== p) {
        province.value = p;
        await loadCities(p);
      }
      if (cities.value.includes(c)) {
        city.value = c;
      }
      return;
    }

    try {
      const resolved = await reverseRegionByCoordinateApi({ latitude: point.latitude, longitude: point.longitude });
      if (resolved?.province) {
        if (province.value !== resolved.province) {
          province.value = resolved.province;
          await loadCities(resolved.province);
        }
      }
      if (resolved?.city && cities.value.includes(resolved.city)) {
        city.value = resolved.city;
      }
    } catch {
      // reverse 失败不阻断手动选择
    }
  },
  { deep: true }
);

async function query(): Promise<void> {
  errorMsg.value = null;
  infoMsg.value = null;
  rows.value = [];
  showMobileDetails.value = false;

  if (!province.value || !city.value) {
    errorMsg.value = '请选择省份和城市后再查询';
    return;
  }

  loading.value = true;
  try {
    const data = await getWeatherRadiationApi({
      province: province.value,
      city: city.value,
      limit: limit.value
    });
    rows.value = data;
    if (data.length === 0) {
      infoMsg.value = '当前省市暂无天气辐射数据，请切换城市重试';
    }
  } catch (e: any) {
    errorMsg.value = e?.message ?? '查询失败';
    rows.value = [];
  } finally {
    loading.value = false;
  }
}

function applyToCalc(): void {
  const eqh = summary.value.eqh;
  const row = latest.value;
  if (eqh == null || !row) {
    errorMsg.value = '当前结果缺少利用小时数据，无法应用到测算';
    return;
  }

  projectStore.setAppliedWeather({
    latitude: row.latitude,
    longitude: row.longitude,
    equivalent_hours: Number(eqh),
    province: province.value,
    city: city.value,
  });
  infoMsg.value = '已应用天气利用小时到收益测算';
}

onMounted(async () => {
  await loadProvinces();
  if (province.value) {
    await loadCities(province.value);
  }
});
</script>

<template>
  <section id="weather-section" class="min-w-0 apple-card p-4 sm:p-6 lg:p-8">
    <div class="space-y-6">
      <div class="min-w-0">
        <h3 class="text-xl font-bold tracking-[-0.03em] text-gray-900 dark:text-dark-text lg:text-[1.9rem]">天气与辐射（省市查询）</h3>
        <p class="apple-compact-copy mt-2 text-gray-500 dark:text-dark-text/60">
          按省份与城市快速查询辐射和利用小时。
        </p>
      </div>

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <div class="min-w-0">
          <label class="mb-1 block text-xs text-gray-500 dark:text-dark-text/60">省份</label>
          <select
            v-model="province"
            class="apple-input"
            :disabled="loadingProvinces"
          >
            <option value="">请选择</option>
            <option v-for="p in provinces" :key="p" :value="p">{{ p }}</option>
          </select>
        </div>

        <div class="min-w-0">
          <label class="mb-1 block text-xs text-gray-500 dark:text-dark-text/60">城市</label>
          <select
            v-model="city"
            class="apple-input"
            :disabled="!province || loadingCities"
          >
            <option value="">请选择</option>
            <option v-for="c in cities" :key="c" :value="c">{{ c }}</option>
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

        <button
          @click="query"
          class="apple-pill-primary w-full self-end"
          :disabled="loading || !province || !city"
        >
          {{ loading ? '查询中...' : '查询' }}
        </button>

        <button
          @click="applyToCalc"
          class="apple-pill-secondary w-full self-end"
          :disabled="loading || rows.length === 0"
        >
          应用到测算
        </button>
      </div>
    </div>

    <div v-if="errorMsg" class="mb-4 text-sm text-red-600 dark:text-red-400">
      {{ errorMsg }}
    </div>
    <div v-if="infoMsg" class="mb-4 text-sm text-amber-600 dark:text-amber-400">
      {{ infoMsg }}
    </div>

    <div class="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
      <div class="apple-subcard p-3 sm:p-4">
        <p class="text-xs text-gray-500 dark:text-dark-text/60">最新日期</p>
        <p class="text-lg font-semibold text-gray-900 dark:text-dark-text mt-1">{{ latest?.day ?? '-' }}</p>
      </div>
      <div class="apple-subcard p-3 sm:p-4">
        <p class="text-xs text-gray-500 dark:text-dark-text/60">年辐射量 (kWh/m²)</p>
        <p class="text-lg font-semibold text-gray-900 dark:text-dark-text mt-1">{{ summary.annual ?? '-' }}</p>
      </div>
      <div class="apple-subcard p-3 sm:p-4">
        <p class="text-xs text-gray-500 dark:text-dark-text/60">等效利用小时数 (h)</p>
        <p class="text-lg font-semibold text-gray-900 dark:text-dark-text mt-1">{{ summary.eqh ?? '-' }}</p>
      </div>
    </div>

    <div class="md:hidden">
      <button
        v-if="rows.length > 0"
        type="button"
        class="apple-pill-secondary mt-4 w-full justify-center"
        @click="showMobileDetails = !showMobileDetails"
      >
        {{ showMobileDetails ? '收起详情' : '查看详情' }}
      </button>

      <div
        v-if="showMobileDetails"
        class="mt-4 space-y-3"
        @touchstart.passive="onTouchStart"
        @touchend.passive="onTouchEnd"
      >
        <article
          v-for="item in mobileRows"
          :key="`mobile-${item.day}-${item.latitude}-${item.longitude}`"
          class="apple-subcard p-4"
        >
          <div class="flex items-start justify-between gap-3">
            <div>
              <p class="text-sm font-semibold text-gray-900 dark:text-dark-text">{{ item.day }}</p>
              <p class="mt-1 text-xs text-gray-500 dark:text-dark-text/60">日辐射 {{ item.shortwave_radiation_sum_kwh_m2 }}</p>
            </div>
            <span class="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300">
              {{ item.temperature_mean_c ?? '-' }} °C
            </span>
          </div>
          <div class="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div class="rounded-[18px] bg-white px-3 py-2 dark:bg-dark-card">
              <p class="text-xs text-gray-500 dark:text-dark-text/60">降水</p>
              <p class="mt-1 font-medium text-gray-900 dark:text-dark-text">{{ item.precipitation_sum_mm ?? '-' }} mm</p>
            </div>
            <div class="rounded-[18px] bg-white px-3 py-2 dark:bg-dark-card">
              <p class="text-xs text-gray-500 dark:text-dark-text/60">风速</p>
              <p class="mt-1 font-medium text-gray-900 dark:text-dark-text">{{ item.wind_speed_mean_m_s ?? '-' }} m/s</p>
            </div>
          </div>
        </article>

        <div class="apple-subcard flex items-center justify-between gap-3 px-3 py-2">
          <button
            type="button"
            class="min-h-[40px] rounded-full px-3 text-sm font-medium text-slate-700 transition disabled:opacity-40 dark:text-dark-text/80"
            :disabled="!canPrevMobilePage"
            @click="prevMobilePage"
          >
            上一页
          </button>
          <span class="text-sm text-slate-500 dark:text-dark-text/60">{{ mobilePage + 1 }} / {{ mobileTotalPages }}</span>
          <button
            type="button"
            class="min-h-[40px] rounded-full px-3 text-sm font-medium text-slate-700 transition disabled:opacity-40 dark:text-dark-text/80"
            :disabled="!canNextMobilePage"
            @click="nextMobilePage"
          >
            下一页
          </button>
        </div>
      </div>
    </div>
    <div class="space-y-3 md:hidden">
      <div v-if="rows.length === 0" class="rounded-[22px] border border-dashed border-gray-200 px-4 py-6 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-dark-text/60">
        暂无数据。请切换省市重试。
      </div>
    </div>

    <div class="hidden overflow-hidden rounded-[24px] border border-black/[0.05] bg-[#fbfbfd] md:block dark:border-slate-800 dark:bg-slate-900/30">
      <div class="touch-scroll overflow-x-auto">
        <table class="min-w-full text-xs sm:text-sm">
          <thead class="bg-gray-50 dark:bg-dark-bg">
            <tr class="text-left text-gray-600 dark:text-dark-text/70">
              <th class="px-4 py-3 font-medium">日期</th>
              <th class="px-4 py-3 font-medium">日辐射 (kWh/m²)</th>
              <th class="px-4 py-3 font-medium">均温(°C)</th>
              <th class="px-4 py-3 font-medium">降水(mm)</th>
              <th class="px-4 py-3 font-medium">风速(m/s)</th>
            </tr>
          </thead>
          <tbody class="bg-white dark:bg-dark-card">
            <tr v-for="r in rows" :key="`${r.day}-${r.latitude}-${r.longitude}`" class="border-t border-gray-100 dark:border-gray-800">
              <td class="px-4 py-3 text-gray-900 dark:text-dark-text">{{ r.day }}</td>
              <td class="px-4 py-3 text-gray-900 dark:text-dark-text">{{ r.shortwave_radiation_sum_kwh_m2 }}</td>
              <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">{{ r.temperature_mean_c ?? '-' }}</td>
              <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">{{ r.precipitation_sum_mm ?? '-' }}</td>
              <td class="px-4 py-3 text-gray-700 dark:text-dark-text/80">{{ r.wind_speed_mean_m_s ?? '-' }}</td>
            </tr>
            <tr v-if="rows.length === 0" class="border-t border-gray-100 dark:border-gray-800">
              <td class="px-4 py-6 text-center text-gray-500 dark:text-dark-text/60" colspan="5">
                暂无数据。请切换省市重试。
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

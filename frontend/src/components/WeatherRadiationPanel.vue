<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { getWeatherRadiationApi, type WeatherRadiationItem } from '@/api/weather';
import { getRegionCitiesApi, getRegionProvincesApi, reverseRegionByCoordinateApi } from '@/api/region';
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

const projectStore = useProjectStore();

const latest = computed(() => rows.value[0] ?? null);
const summary = computed(() => {
  const annual = rows.value.find(r => r.annual_radiation_sum_kwh_m2 != null)?.annual_radiation_sum_kwh_m2 ?? null;
  const eqh = rows.value.find(r => r.equivalent_hours_h != null)?.equivalent_hours_h ?? null;
  return { annual, eqh };
});

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
  <div class="bg-white dark:bg-dark-card rounded-xl p-6 shadow-md border border-gray-100 dark:border-gray-800">
    <div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-4">
      <div>
        <h3 class="text-xl font-bold text-gray-900 dark:text-dark-text">天气与辐射（省市查询）</h3>
        <p class="text-sm text-gray-500 dark:text-dark-text/60 mt-1">
          使用省份 -> 城市联动查询，前端不再手输经纬度。
        </p>
      </div>
      <div class="flex flex-wrap gap-3 items-end">
        <div>
          <label class="block text-xs text-gray-500 dark:text-dark-text/60 mb-1">省份</label>
          <select
            v-model="province"
            class="w-32 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-dark-bg text-sm"
            :disabled="loadingProvinces"
          >
            <option value="">请选择</option>
            <option v-for="p in provinces" :key="p" :value="p">{{ p }}</option>
          </select>
        </div>

        <div>
          <label class="block text-xs text-gray-500 dark:text-dark-text/60 mb-1">城市</label>
          <select
            v-model="city"
            class="w-36 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-dark-bg text-sm"
            :disabled="!province || loadingCities"
          >
            <option value="">请选择</option>
            <option v-for="c in cities" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>

        <div>
          <label class="block text-xs text-gray-500 dark:text-dark-text/60 mb-1">条数</label>
          <input
            v-model.number="limit"
            type="number"
            min="1"
            max="2000"
            class="w-24 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-dark-bg text-sm"
          />
        </div>

        <button
          @click="query"
          class="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium disabled:opacity-60"
          :disabled="loading || !province || !city"
        >
          {{ loading ? '查询中...' : '查询' }}
        </button>
        <button
          @click="applyToCalc"
          class="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-900 text-white text-sm font-medium disabled:opacity-60"
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

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
      <div class="rounded-lg border border-gray-100 dark:border-gray-800 p-4 bg-gray-50 dark:bg-dark-bg">
        <p class="text-xs text-gray-500 dark:text-dark-text/60">最新日期</p>
        <p class="text-lg font-semibold text-gray-900 dark:text-dark-text mt-1">{{ latest?.day ?? '-' }}</p>
      </div>
      <div class="rounded-lg border border-gray-100 dark:border-gray-800 p-4 bg-gray-50 dark:bg-dark-bg">
        <p class="text-xs text-gray-500 dark:text-dark-text/60">年辐射量 (kWh/m²)</p>
        <p class="text-lg font-semibold text-gray-900 dark:text-dark-text mt-1">{{ summary.annual ?? '-' }}</p>
      </div>
      <div class="rounded-lg border border-gray-100 dark:border-gray-800 p-4 bg-gray-50 dark:bg-dark-bg">
        <p class="text-xs text-gray-500 dark:text-dark-text/60">等效利用小时数 (h)</p>
        <p class="text-lg font-semibold text-gray-900 dark:text-dark-text mt-1">{{ summary.eqh ?? '-' }}</p>
      </div>
    </div>

    <div class="overflow-auto rounded-lg border border-gray-100 dark:border-gray-800">
      <table class="min-w-full text-sm">
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
              暂无数据。请先完成数据入库，或切换省市重试。
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

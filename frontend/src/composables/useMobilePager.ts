import { computed, ref, watch, type ComputedRef, type Ref } from 'vue';

type Source<T> = Ref<T[]> | ComputedRef<T[]>;

export function useMobilePager<T>(source: Source<T>, pageSize = 1) {
  const page = ref(0);
  const touchStartX = ref(0);

  const totalPages = computed(() => {
    return Math.max(1, Math.ceil(source.value.length / pageSize));
  });

  const pagedItems = computed(() => {
    const start = page.value * pageSize;
    return source.value.slice(start, start + pageSize);
  });

  const canPrev = computed(() => page.value > 0);
  const canNext = computed(() => page.value < totalPages.value - 1);

  function reset(): void {
    page.value = 0;
  }

  function next(): void {
    if (canNext.value) {
      page.value += 1;
    }
  }

  function prev(): void {
    if (canPrev.value) {
      page.value -= 1;
    }
  }

  function onTouchStart(event: TouchEvent): void {
    touchStartX.value = event.touches[0]?.clientX ?? 0;
  }

  function onTouchEnd(event: TouchEvent): void {
    const endX = event.changedTouches[0]?.clientX ?? 0;
    const diff = endX - touchStartX.value;

    if (Math.abs(diff) < 40) {
      return;
    }

    if (diff < 0) {
      next();
      return;
    }

    prev();
  }

  watch(
    source,
    () => {
      page.value = 0;
    },
    { deep: true },
  );

  return {
    page,
    totalPages,
    pagedItems,
    canPrev,
    canNext,
    reset,
    next,
    prev,
    onTouchStart,
    onTouchEnd,
  };
}

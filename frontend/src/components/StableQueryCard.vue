<script setup lang="ts">
withDefaults(defineProps<{
  active?: 'front' | 'back';
}>(), {
  active: 'front',
});
</script>

<template>
  <section class="business-flip-card min-w-0 apple-card">
    <div class="business-flip-stage" :class="{ 'is-flipped': active === 'back' }">
      <div
        class="business-card-face business-card-front"
        :aria-hidden="active === 'back'"
        :inert="active === 'back'"
      >
        <slot name="front" />
      </div>

      <div
        class="business-card-face business-card-back"
        :aria-hidden="active === 'front'"
        :inert="active === 'front'"
      >
        <slot name="back" />
      </div>
    </div>
  </section>
</template>

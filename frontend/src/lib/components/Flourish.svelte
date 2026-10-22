<script lang="ts">
  let { untied = 0 }: { untied?: number } = $props();
</script>

<svg
  class="flourish"
  viewBox="0 0 180 36"
  fill="none"
  aria-hidden="true"
  style={`--untied:${untied}`}
>
  <path
    class="lace lace-top"
    d="M4 18c34 0 35-13 55-13 14 0 14 13 31 13s17-13 31-13c20 0 21 13 55 13"
  />
  <path
    class="lace lace-bottom"
    d="M4 18c34 0 35 13 55 13 14 0 14-13 31-13s17 13 31 13c20 0 21-13 55-13"
  />
  <circle cx="90" cy="18" r="2.5" />
</svg>

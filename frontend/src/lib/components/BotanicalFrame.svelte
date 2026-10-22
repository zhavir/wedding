<script lang="ts">
  let { footer = false }: { footer?: boolean } = $props();
  const petals = [
    [22, 3, 15, -25],
    [65, 13, 11, 40],
    [38, 24, 18, -60],
    [72, 35, 13, 15],
    [24, 46, 16, 65],
    [57, 56, 12, -35],
    [34, 67, 17, 30],
    [76, 77, 11, -65],
    [20, 87, 15, 10],
    [60, 96, 13, 55]
  ];
</script>

<div class="botanical-frame" class:footer-botanicals={footer} aria-hidden="true">
  {#each ['left', 'right'] as side (side)}
    <div class={`floral-stem floral-stem-${side}`}>
      {#each petals as [x, y, size, turn], i (y)}
        <span
          class="cherry-petal"
          style={`left:${x}%;top:${y}%;--petal-size:${size}px;--petal-turn:${turn}deg;--petal-delay:${-i * 1.7 - (side === 'right' ? 4 : 0)}s;--petal-duration:${12 + (i % 4)}s`}
        >
          <svg viewBox="0 0 24 32" fill="none">
            <path d="M12 30C4 23-2 12 3 5 6 1 10 2 12 6 14 2 18 1 21 5 26 12 20 23 12 30Z" />
            <path class="petal-vein" d="M12 27Q9 17 12 9" />
          </svg>
        </span>
      {/each}
    </div>
  {/each}
</div>

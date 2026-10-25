<script lang="ts">
  import { t } from '#lib/i18n.svelte.ts';
  import { wedding as w } from '#lib/wedding.ts';
  import StaticPicture from './StaticPicture.svelte';
  const imageCount = 5;
  let reveal = $state(50);
  let akamaruIndex = $state(1);
  let narutoIndex = $state(1);
  // Prevent repeated advances while the slider stays at an endpoint.
  let lastEndpoint: 0 | 100 | null = null;

  function updateReveal(value: number): void {
    reveal = value;
    const endpoint = value === 0 || value === 100 ? value : null;

    if (endpoint !== null && endpoint !== lastEndpoint) {
      if (endpoint === 100) {
        // Akamaru is fully visible; advance the hidden Naruto photo.
        narutoIndex = (narutoIndex % imageCount) + 1;
      } else {
        // Naruto is fully visible; advance the hidden Akamaru photo.
        akamaruIndex = (akamaruIndex % imageCount) + 1;
      }
    }

    lastEndpoint = endpoint;
  }
</script>

<section class="section dog-section" id="akamaru">
  <div>
    <div class="comparison">
      <div class="layer">
        <StaticPicture
          name={`akamaru-naruto-${narutoIndex}`}
          alt={t('Akamaru from Naruto, the inspiration for his name')}
        />
      </div>
      <div class="layer" style={`clip-path: inset(0 ${100 - reveal}% 0 0)`}>
        <StaticPicture name={`akamaru-${akamaruIndex}`} alt={t('Our dachshund Akamaru')} />
      </div>
      <span class="divider" style={`left: ${reveal}%`} aria-hidden="true"><span>↔</span></span>
      <input
        type="range"
        min="0"
        max="100"
        value={reveal}
        oninput={(event) => updateReveal(Number(event.currentTarget.value))}
        aria-label={t('Reveal the origin of Akamaru’s name')}
        aria-valuetext={t('{percent}% Akamaru, the rest his Naruto namesake', { percent: reveal })}
      />
    </div>
    <p class="comparison-caption">{t('Slide to meet the ninja behind his name.')}</p>
  </div>
  <div>
    <p class="eyebrow">{w.dog.eyebrow} · {w.dog.name}</p>
    <h2>{w.dog.title}</h2>
    <p>{w.dog.text}</p>
    <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- External Instagram profile. -->
    <a href={w.dog.instagram} target="_blank" rel="noreferrer">{w.dog.linkLabel}</a>
  </div>
</section>

<style>
  .comparison {
    position: relative;
    aspect-ratio: 4 / 5;
    overflow: hidden;
    border-radius: 48% 48% 8% 8%;
    background: #e7e7dc;
  }
  .layer {
    position: absolute;
    inset: 0;
  }
  .divider {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 3px;
    background: #fffdf7;
    pointer-events: none;
  }
  .divider span {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    border-radius: 50%;
    background: #fffdf7;
    padding: 0.6rem;
    color: #25352b;
  }
  input {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    margin: 0;
    opacity: 0;
    cursor: ew-resize;
  }
  .comparison:focus-within {
    outline: 3px solid #65705b;
    outline-offset: 5px;
  }
  .comparison-caption {
    text-align: center;
    font-style: italic;
    font-size: 0.9rem;
    margin-top: 1rem;
  }
</style>

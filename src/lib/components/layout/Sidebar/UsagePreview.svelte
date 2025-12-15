<script lang="ts">
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	dayjs.extend(relativeTime);

	const i18n = getContext<Writable<i18nType>>('i18n');

	type UsageSummary = {
		tokens?: {
			prompt?: number;
			completion?: number;
			cached?: number;
			other?: number;
			total?: number;
		};
		cost?: {
			prompt?: number;
			completion?: number;
			cached?: number;
			other?: number;
			total?: number;
			currency?: string | null;
		};
		messages?: number;
		last_activity?: number | null;
	};

	export let summary: UsageSummary | null = null;

	const palette = ['#6366F1', '#0EA5E9', '#10B981', '#A855F7'];
	const segmentConfig = [
		{ key: 'prompt', label: 'Prompt' },
		{ key: 'completion', label: 'Completion' },
		{ key: 'cached', label: 'Cached' },
		{ key: 'other', label: 'Other' }
	] as const;

	const formatNumber = (value = 0) =>
		new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(value);

	const getCurrencyFormatter = (currency: string) =>
		new Intl.NumberFormat(undefined, {
			style: 'currency',
			currency,
			maximumFractionDigits: 4
		});

	const safeTimestamp = (timestamp?: number | null) => {
		if (!timestamp) return null;
		// Accept timestamps in seconds or milliseconds
		return timestamp > 10 ** 12 ? dayjs(timestamp) : dayjs.unix(timestamp);
	};

	$: tokens = summary?.tokens ?? {
		prompt: 0,
		completion: 0,
		cached: 0,
		other: 0,
		total: 0
	};
	$: cost = summary?.cost ?? {
		prompt: 0,
		completion: 0,
		cached: 0,
		other: 0,
		total: 0,
		currency: 'USD'
	};
	$: totalTokens = tokens.total ?? 0;
	$: totalCost = cost.total ?? 0;
	$: currencyCode = (cost.currency ?? 'USD').toUpperCase();
	$: costFormatter = getCurrencyFormatter(currencyCode);
	$: perThousand = totalTokens > 0 ? (totalCost / totalTokens) * 1000 : 0;
	$: trackedMessages = summary?.messages ?? 0;
	$: lastUpdated =
		summary?.last_activity && summary.last_activity > 0
			? safeTimestamp(summary.last_activity)?.fromNow()
			: null;

	$: segments = segmentConfig
		.map((segment, index) => ({
			label: segment.label,
			value: tokens[segment.key] ?? 0,
			color: palette[index]
		}))
		.filter((segment) => segment.value > 0);

	$: gradientStyle = (() => {
		if (!totalTokens || segments.length === 0) {
			return 'background: conic-gradient(#e5e7eb 0 100%)';
		}

		let offset = 0;
		const stops = segments
			.map((segment) => {
				const slice = (segment.value / totalTokens) * 100;
				const stop = `${segment.color} ${offset}% ${offset + slice}%`;
				offset += slice;
				return stop;
			})
			.join(', ');
		return `background: conic-gradient(${stops})`;
	})();
</script>

{#if totalTokens > 0 || totalCost > 0}
	<div class="rounded-2xl border border-gray-100 dark:border-gray-800 bg-gray-50/60 dark:bg-gray-900/40 p-3">
		<div class="flex items-center gap-3">
			<div class="flex-1">
				<p class="text-[11px] uppercase tracking-wide text-gray-500 dark:text-gray-400">
					{$i18n.t('Tokens used')}
				</p>
				<p class="text-xl font-semibold text-gray-900 dark:text-white">
					{formatNumber(totalTokens)}
				</p>
				<p class="text-[12px] text-gray-500 dark:text-gray-400">
					{trackedMessages > 0
						? $i18n.t('{{count}} responses tracked', { count: trackedMessages })
						: $i18n.t('Awaiting responses')}
				</p>
			</div>

			<div class="relative size-20 shrink-0" style={gradientStyle}>
				<div class="absolute inset-3 rounded-full bg-white dark:bg-gray-900 flex flex-col items-center justify-center text-[10px] text-gray-500 dark:text-gray-400 border border-white/40 dark:border-gray-950/80">
					<span class="text-xs font-semibold text-gray-900 dark:text-white">
						{formatNumber(totalTokens)}
					</span>
					<span class="uppercase tracking-wide">
						{$i18n.t('tokens')}
					</span>
				</div>
			</div>
		</div>

		{#if segments.length > 0}
			<div class="mt-3 grid grid-cols-2 gap-2 text-[11px] leading-tight">
				{#each segments as segment}
					<div class="flex items-start gap-2">
						<span class="mt-1 inline-flex size-2.5 rounded-full" style={`background:${segment.color}`}></span>
						<div>
							<p class="font-medium text-gray-900 dark:text-white">{segment.label}</p>
							<p class="text-gray-500 dark:text-gray-400">
								{formatNumber(segment.value)} {$i18n.t('tokens')}
							</p>
						</div>
					</div>
				{/each}
			</div>
		{/if}

		<div class="mt-3 rounded-xl bg-white/70 dark:bg-gray-950/50 border border-gray-100 dark:border-gray-800 px-3 py-2 text-xs text-gray-700 dark:text-gray-300">
			<div class="flex items-baseline justify-between gap-2">
				<span>{$i18n.t('Estimated cost')}</span>
				<span class="font-semibold text-sm text-gray-900 dark:text-white">
					{totalCost ? costFormatter.format(totalCost) : '--'}
				</span>
			</div>
			<div class="flex justify-between text-[11px] text-gray-500 dark:text-gray-400 mt-1">
				<span>
					{perThousand
						? `${costFormatter.format(perThousand)} / 1K ${$i18n.t('tokens')}`
						: $i18n.t('No pricing data detected')}
				</span>
				{#if lastUpdated}
					<span>{$i18n.t('Updated {{when}}', { when: lastUpdated })}</span>
				{/if}
			</div>
		</div>
	</div>
{:else}
	<div class="rounded-2xl border border-dashed border-gray-200 dark:border-gray-800 bg-transparent px-3 py-2 text-[12px] text-gray-500 dark:text-gray-400">
		{$i18n.t('Usage metrics will appear after your next AI response.')}
	</div>
{/if}

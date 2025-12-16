<script>
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	let logs = [];
	let metrics = null;
	let circuitBreakers = {};
	let loading = true;

	// Filters
	let selectedProvider = null;
	let selectedModel = null;
	let selectedRoute = null;
	let errorsOnly = false;
	let ragUsedOnly = false;
	let timeRange = '24h';

	let providers = [];
	let models = [];
	let routes = [];

	// Pagination
	let currentPage = 0;
	let pageSize = 50;

	const fetchLogs = async () => {
		try {
			const params = new URLSearchParams({
				limit: pageSize,
				offset: currentPage * pageSize,
				errors_only: errorsOnly,
				rag_used_only: ragUsedOnly
			});

			if (selectedProvider) params.append('provider', selectedProvider);
			if (selectedModel) params.append('model_id', selectedModel);
			if (selectedRoute) params.append('route_name', selectedRoute);

			const res = await fetch(`/api/v1/observability/logs?${params}`, {
				credentials: 'include'
			});

			if (res.ok) {
				logs = await res.json();

				// Extract unique values for filters
				providers = [...new Set(logs.map(log => log.provider))];
				models = [...new Set(logs.map(log => log.model_id))];
				routes = [...new Set(logs.map(log => log.route_name))];
			} else {
				throw new Error('Failed to fetch logs');
			}
		} catch (error) {
			console.error('Error fetching logs:', error);
			toast.error('Failed to load observability logs');
		}
	};

	const fetchMetrics = async () => {
		try {
			const params = new URLSearchParams();
			if (selectedProvider) params.append('provider', selectedProvider);

			const res = await fetch(`/api/v1/observability/metrics?${params}`, {
				credentials: 'include'
			});

			if (res.ok) {
				metrics = await res.json();
			}
		} catch (error) {
			console.error('Error fetching metrics:', error);
		}
	};

	const fetchCircuitBreakers = async () => {
		try {
			const res = await fetch('/api/v1/observability/circuit-breakers', {
				credentials: 'include'
			});

			if (res.ok) {
				circuitBreakers = await res.json();
			}
		} catch (error) {
			console.error('Error fetching circuit breakers:', error);
		}
	};

	const resetCircuitBreaker = async (provider) => {
		try {
			const res = await fetch(`/api/v1/observability/circuit-breakers/${provider}/reset`, {
				method: 'POST',
				credentials: 'include'
			});

			if (res.ok) {
				toast.success(`Circuit breaker reset for ${provider}`);
				await fetchCircuitBreakers();
			} else {
				throw new Error('Failed to reset circuit breaker');
			}
		} catch (error) {
			console.error('Error resetting circuit breaker:', error);
			toast.error('Failed to reset circuit breaker');
		}
	};

	const loadData = async () => {
		loading = true;
		await Promise.all([
			fetchLogs(),
			fetchMetrics(),
			fetchCircuitBreakers()
		]);
		loading = false;
	};

	onMount(() => {
		loadData();

		// Auto-refresh every 30 seconds
		const interval = setInterval(loadData, 30000);
		return () => clearInterval(interval);
	});

	const formatLatency = (ms) => {
		if (!ms) return 'N/A';
		return `${Math.round(ms)}ms`;
	};

	const formatPercentage = (value) => {
		return `${(value * 100).toFixed(1)}%`;
	};

	const getCircuitBreakerBadgeClass = (state) => {
		switch (state) {
			case 'closed': return 'bg-green-500';
			case 'open': return 'bg-red-500';
			case 'half_open': return 'bg-yellow-500';
			default: return 'bg-gray-500';
		}
	};
</script>

<div class="flex flex-col h-full">
	<div class="mb-4">
		<div class="text-2xl font-semibold mb-2">Observability Dashboard</div>
		<div class="text-sm text-gray-500 dark:text-gray-400">
			Monitor model routing, fallbacks, and RAG performance across providers
		</div>
	</div>

	{#if loading}
		<div class="flex justify-center items-center h-64">
			<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-white"></div>
		</div>
	{:else}
		<!-- Metrics Overview -->
		{#if metrics}
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
				<div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
					<div class="text-sm text-gray-500 dark:text-gray-400">Total Requests</div>
					<div class="text-2xl font-bold">{metrics.total_requests}</div>
				</div>

				<div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
					<div class="text-sm text-gray-500 dark:text-gray-400">Error Rate</div>
					<div class="text-2xl font-bold" class:text-red-500={metrics.error_rate > 0.1}>
						{formatPercentage(metrics.error_rate)}
					</div>
				</div>

				<div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
					<div class="text-sm text-gray-500 dark:text-gray-400">Fallback Rate</div>
					<div class="text-2xl font-bold" class:text-yellow-500={metrics.fallback_rate > 0.05}>
						{formatPercentage(metrics.fallback_rate)}
					</div>
				</div>

				<div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
					<div class="text-sm text-gray-500 dark:text-gray-400">P95 Latency</div>
					<div class="text-2xl font-bold">
						{formatLatency(metrics.p95_latency_ms)}
					</div>
				</div>
			</div>

			<!-- Provider Breakdown -->
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
				<div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
					<div class="text-lg font-semibold mb-3">Provider Distribution</div>
					<div class="space-y-2">
						{#each Object.entries(metrics.provider_breakdown) as [provider, count]}
							<div class="flex justify-between items-center">
								<span class="text-sm">{provider}</span>
								<span class="text-sm font-mono">{count}</span>
							</div>
						{/each}
					</div>
				</div>

				<div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow">
					<div class="text-lg font-semibold mb-3">RAG Performance</div>
					<div class="space-y-2">
						<div class="flex justify-between items-center">
							<span class="text-sm">Hit Rate</span>
							<span class="text-sm font-mono">{formatPercentage(metrics.rag_hit_rate)}</span>
						</div>
						<div class="flex justify-between items-center">
							<span class="text-sm">Avg Latency</span>
							<span class="text-sm font-mono">{formatLatency(metrics.avg_latency_ms)}</span>
						</div>
					</div>
				</div>
			</div>
		{/if}

		<!-- Circuit Breakers -->
		{#if Object.keys(circuitBreakers).length > 0}
			<div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow mb-6">
				<div class="text-lg font-semibold mb-3">Circuit Breakers</div>
				<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
					{#each Object.entries(circuitBreakers) as [provider, breaker]}
						<div class="border dark:border-gray-700 rounded p-3">
							<div class="flex justify-between items-center mb-2">
								<span class="font-medium">{provider}</span>
								<span class="px-2 py-1 rounded text-xs text-white {getCircuitBreakerBadgeClass(breaker.state)}">
									{breaker.state.toUpperCase()}
								</span>
							</div>
							<div class="text-sm text-gray-600 dark:text-gray-400">
								Failures: {breaker.failure_count}
							</div>
							{#if breaker.state === 'open'}
								<button
									class="mt-2 px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
									on:click={() => resetCircuitBreaker(provider)}
								>
									Reset
								</button>
							{/if}
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Filters -->
		<div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow mb-4">
			<div class="text-lg font-semibold mb-3">Filters</div>
			<div class="grid grid-cols-1 md:grid-cols-5 gap-4">
				<div>
					<label class="block text-sm mb-1">Provider</label>
					<select
						bind:value={selectedProvider}
						on:change={loadData}
						class="w-full px-3 py-2 border rounded dark:bg-gray-700 dark:border-gray-600"
					>
						<option value={null}>All</option>
						{#each providers as provider}
							<option value={provider}>{provider}</option>
						{/each}
					</select>
				</div>

				<div>
					<label class="block text-sm mb-1">Model</label>
					<select
						bind:value={selectedModel}
						on:change={loadData}
						class="w-full px-3 py-2 border rounded dark:bg-gray-700 dark:border-gray-600"
					>
						<option value={null}>All</option>
						{#each models as model}
							<option value={model}>{model}</option>
						{/each}
					</select>
				</div>

				<div>
					<label class="block text-sm mb-1">Route</label>
					<select
						bind:value={selectedRoute}
						on:change={loadData}
						class="w-full px-3 py-2 border rounded dark:bg-gray-700 dark:border-gray-600"
					>
						<option value={null}>All</option>
						{#each routes as route}
							<option value={route}>{route}</option>
						{/each}
					</select>
				</div>

				<div>
					<label class="flex items-center space-x-2 mt-6">
						<input
							type="checkbox"
							bind:checked={errorsOnly}
							on:change={loadData}
							class="rounded"
						/>
						<span class="text-sm">Errors Only</span>
					</label>
				</div>

				<div>
					<label class="flex items-center space-x-2 mt-6">
						<input
							type="checkbox"
							bind:checked={ragUsedOnly}
							on:change={loadData}
							class="rounded"
						/>
						<span class="text-sm">RAG Used</span>
					</label>
				</div>
			</div>
		</div>

		<!-- Request Logs Table -->
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
			<div class="overflow-x-auto">
				<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
					<thead class="bg-gray-50 dark:bg-gray-900">
						<tr>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Timestamp</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Provider</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Route</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Latency</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tokens</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Flags</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
						{#each logs as log}
							<tr class="hover:bg-gray-50 dark:hover:bg-gray-700">
								<td class="px-4 py-3 text-sm whitespace-nowrap">
									{new Date(log.timestamp).toLocaleString()}
								</td>
								<td class="px-4 py-3 text-sm">
									<span class="font-mono text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
										{log.provider}
									</span>
								</td>
								<td class="px-4 py-3 text-sm font-mono">{log.model_id}</td>
								<td class="px-4 py-3 text-sm">{log.route_name}</td>
								<td class="px-4 py-3 text-sm">{formatLatency(log.total_latency_ms)}</td>
								<td class="px-4 py-3 text-sm">
									{#if log.tokens_in && log.tokens_out}
										{log.tokens_in} / {log.tokens_out}
									{:else}
										N/A
									{/if}
								</td>
								<td class="px-4 py-3 text-sm">
									{#if log.error_type}
										<span class="px-2 py-1 bg-red-500 text-white rounded text-xs">
											Error
										</span>
									{:else}
										<span class="px-2 py-1 bg-green-500 text-white rounded text-xs">
											Success
										</span>
									{/if}
								</td>
								<td class="px-4 py-3 text-sm">
									<div class="flex gap-1">
										{#if log.fallback_used}
											<span class="px-2 py-1 bg-yellow-500 text-white rounded text-xs">
												Fallback
											</span>
										{/if}
										{#if log.rag_used}
											<span class="px-2 py-1 bg-blue-500 text-white rounded text-xs">
												RAG
											</span>
										{/if}
									</div>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>

			<!-- Pagination -->
			<div class="flex justify-between items-center px-4 py-3 bg-gray-50 dark:bg-gray-900">
				<button
					on:click={() => { currentPage = Math.max(0, currentPage - 1); loadData(); }}
					disabled={currentPage === 0}
					class="px-4 py-2 border rounded disabled:opacity-50 disabled:cursor-not-allowed"
				>
					Previous
				</button>
				<span class="text-sm">Page {currentPage + 1}</span>
				<button
					on:click={() => { currentPage++; loadData(); }}
					disabled={logs.length < pageSize}
					class="px-4 py-2 border rounded disabled:opacity-50 disabled:cursor-not-allowed"
				>
					Next
				</button>
			</div>
		</div>
	{/if}
</div>

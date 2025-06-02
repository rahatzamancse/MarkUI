<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { MarkUIAPI } from '$lib/api';
	import type { SystemStatus } from '$lib/types';
	import { Cpu, Zap, ZapOff, Monitor, Clock } from 'lucide-svelte';

	let systemStatus: SystemStatus | null = null;
	let loading = true;
	let error: string | null = null;
	let interval: number | null = null;

	function formatBytes(bytes: number): string {
		if (bytes === 0) return '0 B';
		const k = 1024;
		const sizes = ['B', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
	}

	function formatMemoryUsage(allocated: number, total: number): string {
		const percentage = ((allocated / total) * 100).toFixed(1);
		return `${formatBytes(allocated)} / ${formatBytes(total)} (${percentage}%)`;
	}

	async function fetchSystemStatus() {
		try {
			loading = true;
			error = null;
			systemStatus = await MarkUIAPI.getSystemStatus();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to fetch system status';
			console.error('Error fetching system status:', err);
		} finally {
			loading = false;
		}
	}

	onMount(async () => {
		await fetchSystemStatus();
		// Update every 30 seconds
		interval = setInterval(fetchSystemStatus, 30000);
	});

	onDestroy(() => {
		if (interval) {
			clearInterval(interval);
		}
	});
</script>

<div class="flex items-center space-x-2 text-sm">
	{#if loading}
		<div class="flex items-center text-gray-500 dark:text-gray-400">
			<Monitor class="w-4 h-4 mr-1 animate-pulse" />
			<span>Loading...</span>
		</div>
	{:else if error}
		<div class="flex items-center text-red-500" title="Error: {error}">
			<ZapOff class="w-4 h-4 mr-1" />
			<span>GPU Status Error</span>
		</div>
	{:else if systemStatus}
		{#if systemStatus.gpu.available}
			<div class="flex items-center text-green-600 dark:text-green-400" title="GPU acceleration enabled">
				<Zap class="w-4 h-4 mr-1" />
				<span class="font-medium">GPU</span>
				{#if systemStatus.gpu.devices.length > 0}
					<span class="text-gray-500 dark:text-gray-400 ml-1">
						({systemStatus.gpu.devices[0].name})
					</span>
				{/if}
			</div>
		{:else}
			<div class="flex items-center text-orange-500 dark:text-orange-400" title="CPU processing only">
				<Cpu class="w-4 h-4 mr-1" />
				<span>CPU Only</span>
			</div>
		{/if}
		
		<!-- Detailed GPU info on hover -->
		{#if systemStatus.gpu.available && systemStatus.gpu.devices.length > 0}
			<div class="relative group">
				<button class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
					<Monitor class="w-4 h-4" />
				</button>
				
				<!-- Tooltip with detailed info -->
				<div class="absolute top-6 left-0 z-50 hidden group-hover:block bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3 min-w-[300px]">
					<div class="space-y-2">
						<div class="font-semibold text-sm text-gray-900 dark:text-gray-100">
							GPU Status
						</div>
						
						{#each systemStatus.gpu.devices as device, i}
							<div class="border-t border-gray-200 dark:border-gray-600 pt-2 text-xs">
								<div class="font-medium text-gray-800 dark:text-gray-200">
									Device {device.id}: {device.name}
									{#if device.is_current}
										<span class="text-green-600 dark:text-green-400">(Active)</span>
									{/if}
								</div>
								<div class="text-gray-600 dark:text-gray-400 mt-1">
									Memory: {formatMemoryUsage(device.memory_allocated, device.memory_total)}
								</div>
								<div class="text-gray-600 dark:text-gray-400">
									Cached: {formatBytes(device.memory_cached)}
								</div>
							</div>
						{/each}
						
						<div class="border-t border-gray-200 dark:border-gray-600 pt-2 text-xs">
							<div class="text-gray-600 dark:text-gray-400">
								Torch Device: <span class="font-mono">{systemStatus.gpu.torch_device}</span>
							</div>
							<div class="text-gray-500 dark:text-gray-500 flex items-center mt-1">
								<Clock class="w-3 h-3 mr-1" />
								Last updated: {new Date(systemStatus.timestamp * 1000).toLocaleTimeString()}
							</div>
						</div>
					</div>
				</div>
			</div>
		{/if}
	{/if}
</div> 
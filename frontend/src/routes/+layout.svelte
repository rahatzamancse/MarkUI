<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { theme, isDarkMode, error, isLoading, actions } from '$lib/stores';
	import GPUStatus from '$lib/components/GPUStatus.svelte';
	import { 
		Moon, 
		Sun, 
		AlertCircle, 
		X,
		Loader2
	} from 'lucide-svelte';
	interface Props {
		children?: import('svelte').Snippet;
	}

	let { children }: Props = $props();

	// Apply theme to document
	$effect(() => {
		if (typeof document !== 'undefined') {
			console.log('Applying theme to document:', $isDarkMode ? 'dark' : 'light');
			if ($isDarkMode) {
				document.documentElement.classList.add('dark');
				console.log('Added dark class to document');
			} else {
				document.documentElement.classList.remove('dark');
				console.log('Removed dark class from document');
			}
		}
	});

	// Ensure theme is applied on mount
	onMount(() => {
		console.log('Layout mounted, current theme:', $theme);
		// Force theme application on mount
		if ($isDarkMode) {
			document.documentElement.classList.add('dark');
		} else {
			document.documentElement.classList.remove('dark');
		}
	});
</script>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
	<!-- Navigation -->
	<nav class="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
			<div class="flex justify-between h-16">
				<!-- Logo as home link -->
				<div class="flex items-center">
					<a 
						href="/" 
						class="text-xl font-bold text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors duration-200"
					>
						MarkUI
					</a>
				</div>

				<!-- Theme toggle -->
				<div class="flex items-center space-x-4">
					{#if $isLoading}
						<div class="flex items-center text-sm text-gray-500 dark:text-gray-400">
							<Loader2 class="w-4 h-4 mr-2 animate-spin" />
							Loading...
						</div>
					{/if}
					
					<!-- GPU Status -->
					<GPUStatus />
					
					<button
						onclick={() => actions.toggleTheme()}
						class="p-2 rounded-md text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors duration-200"
						title="Toggle theme"
					>
						{#if $isDarkMode}
							<Sun class="w-5 h-5" />
						{:else}
							<Moon class="w-5 h-5" />
						{/if}
					</button>
				</div>
			</div>
		</div>
	</nav>

	<!-- Error notification -->
	{#if $error}
		<div class="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-400 p-4">
			<div class="flex">
				<div class="flex-shrink-0">
					<AlertCircle class="h-5 w-5 text-red-400" />
				</div>
				<div class="ml-3 flex-1">
					<p class="text-sm text-red-700 dark:text-red-300">
						{$error}
					</p>
				</div>
				<div class="ml-auto pl-3">
					<div class="-mx-1.5 -my-1.5">
						<button
							onclick={() => actions.clearError()}
							class="inline-flex rounded-md p-1.5 text-red-500 hover:bg-red-100 dark:hover:bg-red-900/40 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-red-50 focus:ring-red-600"
						>
							<X class="h-4 w-4" />
						</button>
					</div>
				</div>
			</div>
		</div>
	{/if}

	<!-- Main content -->
	<main class="flex-1">
		{@render children?.()}
	</main>
</div>

<style>
	:global(html) {
		scroll-behavior: smooth;
	}
	
	:global(.dark) {
		color-scheme: dark;
	}
</style>

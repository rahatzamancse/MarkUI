<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { 
		ArrowLeft,
		Play,
		Square,
		CheckSquare,
		Download,
		Eye,
		Settings,
		Loader2,
		FileText,
		Code,
		Globe,
		Brain,
		Scan,
		Scissors,
		Type,
		Calculator,
		Image,
		BookOpen
	} from 'lucide-svelte';
	import { 
		currentPDF, 
		selectedPages, 
		conversionOptions, 
		isLoading, 
		actions,
		llmServices,
		configuredLLMServices,
		ollamaModels,
		currentResult,
		hasSelectedPages
	} from '$lib/stores';
	import { MarkUIAPI } from '$lib/api';
	import { OutputFormat, ConversionStatus } from '$lib/types';
	import type { ConversionJob } from '$lib/types';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';

	let previewImages: string[] = $state([]);
	let loadingPreview = $state(false);
	let currentJob: ConversionJob | null = $state(null);
	let conversionInProgress = $state(false);
	let showResult = $state(false);

	// Ollama models state for conversion page
	let loadingOllamaModelsForConversion = $state(false);

	onMount(async () => {
		if (!$currentPDF) {
			goto('/');
			return;
		}

		await loadPreviewImages();
		actions.loadConfiguredLLMServices();
		actions.loadConversionDefaults();
		
		// Select all pages by default
		selectAllPages();
	});

	async function loadPreviewImages() {
		if (!$currentPDF) return;
		
		try {
			loadingPreview = true;
			const response = await MarkUIAPI.getPDFPreview($currentPDF.id);
			previewImages = response.preview_images;
		} catch (error) {
			actions.setError(`Failed to load preview: ${error}`);
		} finally {
			loadingPreview = false;
		}
	}

	function togglePageSelection(pageNumber: number) {
		actions.togglePage(pageNumber);
	}

	function selectAllPages() {
		if (!$currentPDF) return;
		actions.selectAllPages($currentPDF.total_pages);
	}

	function clearSelection() {
		actions.clearSelectedPages();
	}

	async function startConversion() {
		if (!$currentPDF) return;

		const selectedPagesArray = $hasSelectedPages ? Array.from($selectedPages) : undefined;

		const jobData = {
			pdf_document_id: $currentPDF.id,
			output_format: $conversionOptions.output_format,
			selected_pages: selectedPagesArray,
			use_llm: $conversionOptions.use_llm,
			force_ocr: $conversionOptions.force_ocr,
			strip_existing_ocr: $conversionOptions.strip_existing_ocr,
			format_lines: $conversionOptions.format_lines,
			redo_inline_math: $conversionOptions.redo_inline_math,
			disable_image_extraction: $conversionOptions.disable_image_extraction,
			paginate_output: $conversionOptions.paginate_output,
			llm_service: $conversionOptions.llm_service,
			llm_model: $conversionOptions.llm_model
		};

		try {
			conversionInProgress = true;
			currentJob = await MarkUIAPI.createConversionJob(jobData);
			
			// Poll for completion
			await pollJobStatus();
		} catch (error) {
			actions.setError(`Conversion failed: ${error}`);
			conversionInProgress = false;
		}
	}

	async function pollJobStatus() {
		if (!currentJob) return;

		const pollInterval = setInterval(async () => {
			try {
				const updatedJob = await MarkUIAPI.getConversionJob(currentJob!.id);
				currentJob = updatedJob;

				if (updatedJob.status === ConversionStatus.COMPLETED) {
					clearInterval(pollInterval);
					conversionInProgress = false;
					await loadResult();
				} else if (updatedJob.status === ConversionStatus.FAILED) {
					clearInterval(pollInterval);
					conversionInProgress = false;
					actions.setError(`Conversion failed: ${updatedJob.error_message}`);
				}
			} catch (error) {
				clearInterval(pollInterval);
				conversionInProgress = false;
				actions.setError(`Failed to check job status: ${error}`);
			}
		}, 2000);
	}

	async function loadResult() {
		if (!currentJob) return;

		try {
			const result = await MarkUIAPI.getConversionResult(currentJob.id);
			currentResult.set(result);
			showResult = true;
		} catch (error) {
			actions.setError(`Failed to load result: ${error}`);
		}
	}

	async function downloadResult() {
		if (!currentJob) return;

		try {
			const blob = await MarkUIAPI.downloadConversionResult(currentJob.id);
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `markui_conversion.zip`;
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			URL.revokeObjectURL(url);
		} catch (error) {
			actions.setError(`Download failed: ${error}`);
		}
	}

	function renderContent(content: string, format: OutputFormat): string {
		if (format === OutputFormat.MARKDOWN) {
			// Process markdown content to resolve image paths
			let processedContent = content;
			
			// If we have a current job, resolve relative image paths to absolute URLs
			if (currentJob && currentJob.id) {
				// Replace relative image paths with absolute URLs
				// Pattern matches: ![alt text](image_name.ext) or ![](image_name.ext)
				processedContent = processedContent.replace(
					/!\[([^\]]*)\]\(([^)]+)\)/g,
					(match, altText, imagePath) => {
						// Check if it's already an absolute URL
						if (imagePath.startsWith('http') || imagePath.startsWith('/')) {
							return match;
						}
						
						// Convert relative path to absolute URL pointing to backend
						const absoluteUrl = `http://localhost:8000/output/job_${currentJob!.id}/${imagePath}`;
						return `![${altText}](${absoluteUrl})`;
					}
				);
			}
			
			const htmlContent = marked.parse(processedContent, { async: false }) as string;
			return DOMPurify.sanitize(htmlContent);
		} else if (format === OutputFormat.HTML) {
			return DOMPurify.sanitize(content);
		} else {
			// JSON - pretty print
			try {
				const parsed = JSON.parse(content);
				return `<pre><code>${JSON.stringify(parsed, null, 2)}</code></pre>`;
			} catch {
				return `<pre><code>${content}</code></pre>`;
			}
		}
	}



	async function loadOllamaModelsForService() {
		if (!$conversionOptions.llm_service || !$conversionOptions.llm_service.includes('ollama')) {
			return;
		}

		// Get the Ollama base URL from user settings
		try {
			loadingOllamaModelsForConversion = true;
			const settings = await MarkUIAPI.getUserSettings();
			if (settings.ollama_base_url) {
				await actions.loadOllamaModels(settings.ollama_base_url);
			}
		} catch (error) {
			console.error('Failed to load Ollama models for conversion:', error);
		} finally {
			loadingOllamaModelsForConversion = false;
		}
	}
	// Reactive statements
	let outputFormatIcon = $derived($conversionOptions.output_format === OutputFormat.MARKDOWN ? FileText :
		$conversionOptions.output_format === OutputFormat.JSON ? Code : Globe);
	// Load Ollama models when service changes to Ollama
	$effect(() => {
		if ($conversionOptions.llm_service && $conversionOptions.llm_service.includes('ollama')) {
			loadOllamaModelsForService();
		}
	});
</script>

{#if !$currentPDF}
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<div class="text-center">
			<p class="text-gray-500 dark:text-gray-400">No PDF selected. Please go back and select a PDF.</p>
			<button
				onclick={() => goto('/')}
				class="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
			>
				<ArrowLeft class="w-4 h-4 mr-2" />
				Go Back
			</button>
		</div>
	</div>
{:else}
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Header -->
		<div class="flex items-center justify-between mb-8">
			<div class="flex items-center space-x-4">
				<button
					onclick={() => goto('/')}
					class="p-2 rounded-md text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
				>
					<ArrowLeft class="w-5 h-5" />
				</button>
				<div>
					<h1 class="text-2xl font-bold text-gray-900 dark:text-white">
						Convert PDF
					</h1>
					<p class="text-gray-600 dark:text-gray-400">
						{$currentPDF.original_filename} • {$currentPDF.total_pages} pages
					</p>
				</div>
			</div>

			{#if showResult && currentJob}
				<button
					onclick={downloadResult}
					class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700"
				>
					<Download class="w-4 h-4 mr-2" />
					Download ZIP
				</button>
			{/if}
		</div>

		{#if showResult && $currentResult}
			<!-- Result Display -->
			<div class="bg-white dark:bg-gray-800 shadow rounded-lg mb-8">
				<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
					<h2 class="text-lg font-medium text-gray-900 dark:text-white">
						Conversion Result
					</h2>
				</div>
				<div class="p-6">
					<div class="prose dark:prose-invert max-w-none">
						{@html renderContent($currentResult.content || '', $currentResult.job.output_format)}
					</div>
				</div>
			</div>
		{:else}
			<div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
				<!-- PDF Preview -->
				<div class="lg:col-span-2">
					<div class="bg-white dark:bg-gray-800 shadow rounded-lg">
						<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
							<div class="flex items-center justify-between">
								<h2 class="text-lg font-medium text-gray-900 dark:text-white">
									PDF Preview
								</h2>
								<div class="flex items-center space-x-2">
									<button
										onclick={selectAllPages}
										class="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
									>
										Select All
									</button>
									<button
										onclick={clearSelection}
										class="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
									>
										Clear
									</button>
								</div>
							</div>
							<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
								{$selectedPages.size} of {$currentPDF.total_pages} pages selected
							</p>
						</div>

						{#if loadingPreview}
							<div class="p-8 text-center">
								<Loader2 class="w-8 h-8 animate-spin mx-auto mb-4 text-blue-600" />
								<p class="text-gray-500 dark:text-gray-400">Loading preview...</p>
							</div>
						{:else}
							<div class="p-6">
								<div class="grid grid-cols-2 md:grid-cols-3 gap-4">
									{#each previewImages as imageUrl, index}
										{@const pageNumber = index + 1}
										{@const isSelected = $selectedPages.has(pageNumber)}
										<div class="relative">
											<button
												onclick={() => togglePageSelection(pageNumber)}
												class="block w-full rounded-lg overflow-hidden border-2 transition-all duration-200 {isSelected
													? 'border-blue-500 ring-2 ring-blue-200 dark:ring-blue-800'
													: 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'}"
											>
												<img
													src={imageUrl}
													alt="Page {pageNumber}"
													class="w-full h-auto"
													loading="lazy"
												/>
												<div class="absolute top-2 left-2 bg-white dark:bg-gray-800 rounded px-2 py-1 text-xs font-medium text-gray-900 dark:text-white shadow">
													{pageNumber}
												</div>
												{#if isSelected}
													<div class="absolute top-2 right-2 bg-blue-600 rounded-full p-1">
														<CheckSquare class="w-4 h-4 text-white" />
													</div>
												{:else}
													<div class="absolute top-2 right-2 bg-gray-600 bg-opacity-50 rounded-full p-1">
														<Square class="w-4 h-4 text-white" />
													</div>
												{/if}
											</button>
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				</div>

				<!-- Conversion Options -->
				<div class="space-y-6">
					<!-- Output Format -->
					<div class="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
						<h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">
							Output Format
						</h3>
						<div class="space-y-3">
							{#each Object.values(OutputFormat) as format}
								<label class="flex items-center">
									<input
										type="radio"
										bind:group={$conversionOptions.output_format}
										value={format}
										class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-600"
									/>
									<span class="ml-3 text-sm text-gray-700 dark:text-gray-300 capitalize">
										{format}
									</span>
								</label>
							{/each}
						</div>
					</div>

					<!-- Marker Options -->
					<div class="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
						<h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">
							Conversion Options
						</h3>
						<div class="space-y-4">
							<label class="flex items-start">
								<input
									type="checkbox"
									bind:checked={$conversionOptions.use_llm}
									class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-600 mt-0.5"
								/>
								<div class="ml-3">
									<div class="flex items-center">
										<Brain class="w-4 h-4 mr-2 text-purple-500" />
										<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Use LLM</span>
									</div>
									<p class="text-xs text-gray-500 dark:text-gray-400">
										Enhance accuracy with AI models
									</p>
								</div>
							</label>

							<label class="flex items-start">
								<input
									type="checkbox"
									bind:checked={$conversionOptions.force_ocr}
									class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-600 mt-0.5"
								/>
								<div class="ml-3">
									<div class="flex items-center">
										<Scan class="w-4 h-4 mr-2 text-green-500" />
										<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Force OCR</span>
									</div>
									<p class="text-xs text-gray-500 dark:text-gray-400">
										Force OCR on all text
									</p>
								</div>
							</label>

							<label class="flex items-start">
								<input
									type="checkbox"
									bind:checked={$conversionOptions.strip_existing_ocr}
									class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-600 mt-0.5"
								/>
								<div class="ml-3">
									<div class="flex items-center">
										<Scissors class="w-4 h-4 mr-2 text-red-500" />
										<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Strip Existing OCR</span>
									</div>
									<p class="text-xs text-gray-500 dark:text-gray-400">
										Remove existing OCR text
									</p>
								</div>
							</label>

							<label class="flex items-start">
								<input
									type="checkbox"
									bind:checked={$conversionOptions.format_lines}
									class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-600 mt-0.5"
								/>
								<div class="ml-3">
									<div class="flex items-center">
										<Type class="w-4 h-4 mr-2 text-blue-500" />
										<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Format Lines</span>
									</div>
									<p class="text-xs text-gray-500 dark:text-gray-400">
										Reformat lines using OCR
									</p>
								</div>
							</label>

							<label class="flex items-start">
								<input
									type="checkbox"
									bind:checked={$conversionOptions.redo_inline_math}
									class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-600 mt-0.5"
								/>
								<div class="ml-3">
									<div class="flex items-center">
										<Calculator class="w-4 h-4 mr-2 text-orange-500" />
										<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Redo Inline Math</span>
									</div>
									<p class="text-xs text-gray-500 dark:text-gray-400">
										Enhanced math conversion
									</p>
								</div>
							</label>

							<label class="flex items-start">
								<input
									type="checkbox"
									bind:checked={$conversionOptions.disable_image_extraction}
									class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-600 mt-0.5"
								/>
								<div class="ml-3">
									<div class="flex items-center">
										<Image class="w-4 h-4 mr-2 text-gray-500" />
										<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Disable Image Extraction</span>
									</div>
									<p class="text-xs text-gray-500 dark:text-gray-400">
										Skip image extraction
									</p>
								</div>
							</label>

							<label class="flex items-start">
								<input
									type="checkbox"
									bind:checked={$conversionOptions.paginate_output}
									class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-600 mt-0.5"
								/>
								<div class="ml-3">
									<div class="flex items-center">
										<BookOpen class="w-4 h-4 mr-2 text-indigo-500" />
										<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Paginate Output</span>
									</div>
									<p class="text-xs text-gray-500 dark:text-gray-400">
										Add page breaks
									</p>
								</div>
							</label>
						</div>
					</div>

					<!-- LLM Service Selection -->
					{#if $conversionOptions.use_llm}
						<div class="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
							<h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">
								LLM Service
							</h3>
							{#if $configuredLLMServices.length === 0}
								<div class="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md">
									<div class="flex">
										<div class="flex-shrink-0">
											<svg class="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
												<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
											</svg>
										</div>
										<div class="ml-3">
											<h3 class="text-sm font-medium text-yellow-800 dark:text-yellow-200">
												No LLM Services Configured
											</h3>
											<div class="mt-2 text-sm text-yellow-700 dark:text-yellow-300">
												<p>You need to configure at least one LLM service in Settings to use AI enhancement.</p>
											</div>
											<div class="mt-4">
												<div class="-mx-2 -my-1.5 flex">
													<a
														href="/settings"
														class="bg-yellow-50 dark:bg-yellow-900/20 px-2 py-1.5 rounded-md text-sm font-medium text-yellow-800 dark:text-yellow-200 hover:bg-yellow-100 dark:hover:bg-yellow-900/30 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-yellow-50 focus:ring-yellow-600"
													>
														Go to Settings
													</a>
												</div>
											</div>
										</div>
									</div>
								</div>
							{:else}
								<div class="space-y-3">
									<select
										bind:value={$conversionOptions.llm_service}
										class="block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500"
									>
										<option value="">Select a service</option>
										{#each $configuredLLMServices as service}
											<option value={service.name}>{service.display_name}</option>
										{/each}
									</select>
									
									{#if $conversionOptions.llm_service}
										{#if $conversionOptions.llm_service.includes('ollama') && $ollamaModels.length > 0}
											<select
												bind:value={$conversionOptions.llm_model}
												class="block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500"
											>
												<option value="">Select a model</option>
												{#each $ollamaModels as model}
													<option value={model}>{model}</option>
												{/each}
											</select>
											{#if loadingOllamaModelsForConversion}
												<p class="mt-1 text-xs text-gray-500 dark:text-gray-400 flex items-center">
													<Loader2 class="w-3 h-3 mr-1 animate-spin" />
													Loading models...
												</p>
											{/if}
										{:else}
											<input
												type="text"
												bind:value={$conversionOptions.llm_model}
												placeholder="Model name (optional)"
												class="block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500"
											/>
										{/if}
									{/if}
								</div>
							{/if}
						</div>
					{/if}

					<!-- Convert Button -->
					<button
						onclick={startConversion}
						disabled={conversionInProgress || !$currentPDF}
						class="w-full flex items-center justify-center px-4 py-3 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
					>
						{#if conversionInProgress}
							<Loader2 class="w-4 h-4 mr-2 animate-spin" />
							Converting...
						{:else}
							<Play class="w-4 h-4 mr-2" />
							Start Conversion
						{/if}
					</button>

					{#if currentJob && conversionInProgress}
						<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
							<div class="flex items-center">
								<Loader2 class="w-5 h-5 animate-spin text-blue-600 mr-3" />
								<div>
									<p class="text-sm font-medium text-blue-800 dark:text-blue-200">
										Conversion in progress...
									</p>
									<p class="text-xs text-blue-600 dark:text-blue-300">
										Progress: {currentJob.progress}%
									</p>
								</div>
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</div>
{/if} 
<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	import { 
		Play, 
		Download, 
		ChevronLeft, 
		Eye, 
		CheckSquare, 
		Square,
		Loader2,
		Brain,
		Scan,
		Type,
		Calculator,
		Image,
		FileText,
		Scissors,
		Key,
		Server,
		TestTube,
		Check,
		AlertCircle,
		EyeOff,
		RefreshCw,
		Copy
	} from 'lucide-svelte';
	import { 
		currentPDF, 
		selectedPages, 
		conversionOptions,
		llmConfig,
		actions, 
		currentResult,
		isLoading,
		canStartConversion
	} from '$lib/stores';
	import { MarkUIAPI } from '$lib/api';
	import { OutputFormat, ConversionStatus, type ConversionJobCreate } from '$lib/types';
	import JsonViewer from '$lib/components/JsonViewer.svelte';

	let previewImages: string[] = $state([]);
	let loadingPreview = $state(false);
	let converting = $state(false);
	let jobId: number | null = $state(null);
	let showApiKeys: Record<string, boolean> = $state({
		gemini: false,
		openai: false,
		claude: false
	});
	let testingServices: Record<string, boolean> = $state({});
	let testResults: Record<string, { success: boolean; message: string; response_time_ms?: number }> = $state({});
	let rawJsonCopied = $state(false);

	// Recursively parse JSON strings that might contain nested JSON
	function deepParseJson(obj: any): any {
		if (typeof obj === 'string') {
			// Try to parse the string as JSON
			try {
				const parsed = JSON.parse(obj);
				// If successful, recursively parse the result
				return deepParseJson(parsed);
			} catch (e) {
				// If parsing fails, return the original string
				return obj;
			}
		} else if (Array.isArray(obj)) {
			// Recursively parse array elements
			return obj.map(item => deepParseJson(item));
		} else if (obj !== null && typeof obj === 'object') {
			// Recursively parse object properties
			const result: any = {};
			for (const [key, value] of Object.entries(obj)) {
				result[key] = deepParseJson(value);
			}
			return result;
		}
		// Return primitive values as-is
		return obj;
	}

	// Parse JSON content safely
	let parsedJsonContent = $derived((() => {
		if ($currentResult?.job.output_format === 'json' && $currentResult?.content) {
			try {
				// First, try to parse the content directly
				let parsed = JSON.parse($currentResult.content);
				
				// Apply deep parsing to handle nested JSON strings
				parsed = deepParseJson(parsed);
				
				return parsed;
			} catch (error) {
				console.error('Failed to parse JSON:', error);
				console.log('Raw content:', $currentResult.content);
				return null;
			}
		}
		return null;
	})());

	// Configure marked for better rendering
	marked.setOptions({
		breaks: true,
		gfm: true
	});

	// Redirect if no PDF selected
	$effect(() => {
		if (!$currentPDF) {
			goto('/');
		}
	});

	// Load preview images when PDF changes
	$effect(() => {
		if ($currentPDF) {
			loadPreviewImages();
			
			// Ensure all pages are selected by default if none are selected
			if ($selectedPages.size === 0) {
				actions.selectAllPages($currentPDF.total_pages);
			}
		}
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
		if ($currentPDF) {
			actions.selectAllPages($currentPDF.total_pages);
		}
	}

	function clearSelection() {
		actions.clearSelectedPages();
	}

	function toggleApiKeyVisibility(service: string) {
		showApiKeys[service] = !showApiKeys[service];
	}

	async function testServiceConnection(serviceName: string) {
		testingServices[serviceName] = true;
		delete testResults[serviceName];
		
		try {
			const testRequest = {
				service_name: serviceName,
				gemini_api_key: $llmConfig.gemini_api_key || undefined,
				openai_api_key: $llmConfig.openai_api_key || undefined,
				claude_api_key: $llmConfig.claude_api_key || undefined,
				ollama_base_url: $llmConfig.ollama_base_url || undefined,
				ollama_model: $llmConfig.ollama_model || undefined,
				openai_model: $llmConfig.openai_model || undefined,
				openai_base_url: $llmConfig.openai_base_url || undefined,
				claude_model_name: $llmConfig.claude_model_name || undefined,
				vertex_project_id: $llmConfig.vertex_project_id || undefined
			};

			const result = await MarkUIAPI.testLLMServiceConnection(testRequest);
			testResults[serviceName] = {
				success: result.success,
				message: result.message,
				response_time_ms: result.response_time_ms
			};
		} catch (error) {
			testResults[serviceName] = {
				success: false,
				message: `Test failed: ${error}`
			};
		} finally {
			testingServices[serviceName] = false;
		}
	}

	function updateLLMService(serviceName: string) {
		actions.updateConversionOption('llm_service', serviceName);
		actions.updateLLMConfig('default_llm_service', serviceName);
	}

	async function startConversion() {
		if (!$currentPDF) return;

		try {
			converting = true;
			currentResult.set(null);

			// Prepare conversion job data
			const jobData: ConversionJobCreate = {
				pdf_document_id: $currentPDF.id,
				output_format: $conversionOptions.output_format,
				selected_pages: $selectedPages.size > 0 ? Array.from($selectedPages) : undefined,
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

			// Create conversion job
			const job = await MarkUIAPI.createConversionJob(jobData);
			jobId = job.id;

			// Poll for completion
			await pollConversionStatus(job.id);
		} catch (error) {
			actions.setError(`Conversion failed: ${error}`);
		} finally {
			converting = false;
		}
	}

	async function pollConversionStatus(jobId: number) {
		const maxAttempts = 120; // 2 minutes with 1-second intervals
		let attempts = 0;

		while (attempts < maxAttempts) {
			try {
				const job = await MarkUIAPI.getConversionJob(jobId);
				
				if (job.status === ConversionStatus.COMPLETED) {
					// Get the result
					const result = await MarkUIAPI.getConversionResult(jobId);
					currentResult.set(result);
					break;
				} else if (job.status === ConversionStatus.FAILED) {
					throw new Error(job.error_message || 'Conversion failed');
				}

				await new Promise(resolve => setTimeout(resolve, 1000));
				attempts++;
			} catch (error) {
				throw error;
			}
		}

		if (attempts >= maxAttempts) {
			throw new Error('Conversion timed out');
		}
	}

	async function downloadResult() {
		if (!jobId) return;

		try {
			const blob = await MarkUIAPI.downloadConversionResult(jobId);
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `conversion_job_${jobId}.zip`;
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			URL.revokeObjectURL(url);
		} catch (error) {
			actions.setError(`Download failed: ${error}`);
		}
	}

	function renderContent(content: string, format: OutputFormat, images?: string[]): string {
		if (format === 'html') {
			// For HTML, apply image replacement and then sanitize
			let htmlContent = content;
			
			// Replace image sources with actual extracted image URLs
			if (images && images.length > 0) {
				// Create a map of image filenames to URLs
				const imageMap = new Map<string, string>();
				images.forEach(url => {
					const filename = url.split('/').pop();
					if (filename) {
						imageMap.set(filename, url);
					}
				});
				
				// Replace img src attributes in the HTML
				htmlContent = htmlContent.replace(/<img([^>]*?)src=["']([^"']*?)["']([^>]*?)>/g, (match, before, src, after) => {
					// Extract filename from src
					const srcFilename = src.split('/').pop();
					
					// If we have a matching extracted image, use its URL
					if (srcFilename && imageMap.has(srcFilename)) {
						const actualUrl = imageMap.get(srcFilename);
						return `<img${before}src="${actualUrl}"${after}>`;
					}
					
					// If src looks like a placeholder or relative path, try to match by index
					if (src.includes('image') || src.startsWith('./') || src.startsWith('../') || !src.startsWith('http')) {
						// Try to extract image number from src or alt text
						const imageNumberMatch = match.match(/(?:image[_\s]*(\d+)|(\d+))/i);
						if (imageNumberMatch) {
							const imageIndex = parseInt(imageNumberMatch[1] || imageNumberMatch[2]) - 1;
							if (imageIndex >= 0 && imageIndex < images.length) {
								return `<img${before}src="${images[imageIndex]}"${after}>`;
							}
						}
						
						// Fallback: use first available image if only one
						if (images.length === 1) {
							return `<img${before}src="${images[0]}"${after}>`;
						}
					}
					
					// Return original if no match found
					return match;
				});
			}
			
			return DOMPurify.sanitize(htmlContent);
		} else if (format === 'markdown') {
			// For markdown, parse to HTML and sanitize
			let htmlContent = marked.parse(content) as string;
			
			// Replace image sources with actual extracted image URLs
			if (images && images.length > 0) {
				// Create a map of image filenames to URLs
				const imageMap = new Map<string, string>();
				images.forEach(url => {
					const filename = url.split('/').pop();
					if (filename) {
						imageMap.set(filename, url);
					}
				});
				
				// Replace img src attributes in the HTML
				htmlContent = htmlContent.replace(/<img([^>]*?)src=["']([^"']*?)["']([^>]*?)>/g, (match, before, src, after) => {
					// Extract filename from src
					const srcFilename = src.split('/').pop();
					
					// If we have a matching extracted image, use its URL
					if (srcFilename && imageMap.has(srcFilename)) {
						const actualUrl = imageMap.get(srcFilename);
						return `<img${before}src="${actualUrl}"${after}>`;
					}
					
					// If src looks like a placeholder or relative path, try to match by index
					if (src.includes('image') || src.startsWith('./') || src.startsWith('../') || !src.startsWith('http')) {
						// Try to extract image number from src or alt text
						const imageNumberMatch = match.match(/(?:image[_\s]*(\d+)|(\d+))/i);
						if (imageNumberMatch) {
							const imageIndex = parseInt(imageNumberMatch[1] || imageNumberMatch[2]) - 1;
							if (imageIndex >= 0 && imageIndex < images.length) {
								return `<img${before}src="${images[imageIndex]}"${after}>`;
							}
						}
						
						// Fallback: use first available image if only one
						if (images.length === 1) {
							return `<img${before}src="${images[0]}"${after}>`;
						}
					}
					
					// Return original if no match found
					return match;
				});
			}
			
			return DOMPurify.sanitize(htmlContent);
		} else {
			// For JSON and other formats, render as preformatted text
			const escapedContent = content
				.replace(/&/g, '&amp;')
				.replace(/</g, '&lt;')
				.replace(/>/g, '&gt;')
				.replace(/"/g, '&quot;')
				.replace(/'/g, '&#39;');
			return `<pre class="whitespace-pre-wrap font-mono text-sm bg-gray-50 dark:bg-gray-900 p-4 rounded-lg overflow-x-auto">${escapedContent}</pre>`;
		}
	}

	function goBack() {
		// If we're viewing results, just clear the result and stay on convert page
		if ($currentResult) {
			currentResult.set(null);
			jobId = null;
			converting = false;
		} else {
			// If we're not viewing results, go back to homepage
			actions.clearCurrentPDF();
			goto('/');
		}
	}

	async function copyRawJson() {
		try {
			const textToCopy = parsedJsonContent ? JSON.stringify(parsedJsonContent, null, 2) : ($currentResult?.content || '');
			await navigator.clipboard.writeText(textToCopy);
			rawJsonCopied = true;
			setTimeout(() => {
				rawJsonCopied = false;
			}, 2000);
		} catch (error) {
			console.error('Failed to copy to clipboard:', error);
		}
	}
</script>

{#if !$currentPDF}
	<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<div class="text-center">
			<p class="text-gray-500 dark:text-gray-400">No PDF selected. Redirecting...</p>
		</div>
	</div>
{:else}
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Header -->
		<div class="mb-8">
			<div class="flex items-center justify-between">
				<div class="flex items-center space-x-4">
					<button
						onclick={goBack}
						class="flex items-center text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition-colors duration-200"
					>
						<ChevronLeft class="w-5 h-5 mr-1" />
						{$currentResult ? 'Back to Convert' : 'Back to Upload'}
					</button>
					<div>
						<h1 class="text-3xl font-bold text-gray-900 dark:text-white">
							Convert PDF
						</h1>
						<p class="text-gray-600 dark:text-gray-400">
							{$currentPDF.original_filename} • {$currentPDF.total_pages} pages
						</p>
					</div>
				</div>
				
				{#if !converting && !$currentResult}
					<button
						onclick={startConversion}
						disabled={!$canStartConversion}
						class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
					>
						<Play class="w-5 h-5 mr-2" />
						Start Conversion
					</button>
				{:else if converting}
					<div class="flex items-center text-blue-600 dark:text-blue-400">
						<Loader2 class="w-5 h-5 mr-2 animate-spin" />
						Converting...
					</div>
				{:else if $currentResult}
					<div class="flex items-center space-x-3">
						<button
							onclick={() => {
								currentResult.set(null);
								jobId = null;
								converting = false;
							}}
							class="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200"
						>
							<RefreshCw class="w-4 h-4 mr-2" />
							New Conversion
						</button>
						<button
							onclick={downloadResult}
							class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors duration-200"
						>
							<Download class="w-5 h-5 mr-2" />
							Download Result
						</button>
					</div>
				{/if}
			</div>
		</div>

		{#if $currentResult}
			<!-- Conversion Result -->
			<div class="bg-white dark:bg-gray-800 shadow rounded-lg mb-8">
				<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
					<div class="flex items-center justify-between">
						<h2 class="text-lg font-medium text-gray-900 dark:text-white flex items-center">
							<Check class="w-5 h-5 mr-2 text-green-500" />
							Conversion Complete
						</h2>
						<div class="text-sm text-gray-500 dark:text-gray-400">
							Format: {$currentResult.job.output_format.toUpperCase()}
							{#if $currentResult.images && $currentResult.images.length > 0}
								• {$currentResult.images.length} images extracted
							{/if}
						</div>
					</div>
				</div>
				
				<!-- Content Display -->
				<div class="p-6">
					{#if $currentResult.job.output_format === 'markdown'}
						<div class="prose prose-lg dark:prose-invert max-w-none prose-headings:text-gray-900 dark:prose-headings:text-white prose-p:text-gray-700 dark:prose-p:text-gray-300 prose-a:text-blue-600 dark:prose-a:text-blue-400 prose-code:text-pink-600 dark:prose-code:text-pink-400 prose-pre:bg-gray-100 dark:prose-pre:bg-gray-800">
							{@html renderContent($currentResult.content || '', $currentResult.job.output_format, $currentResult.images)}
						</div>
					{:else if $currentResult.job.output_format === 'html'}
						<div class="prose prose-lg dark:prose-invert max-w-none">
							{@html renderContent($currentResult.content || '', $currentResult.job.output_format, $currentResult.images)}
						</div>
					{:else if $currentResult.job.output_format === 'json'}
						<!-- JSON format with beautiful tree viewer -->
						<div class="bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
							<div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
								<h3 class="text-sm font-medium text-gray-700 dark:text-gray-300">JSON Output</h3>
								<button
									onclick={copyRawJson}
									class="inline-flex items-center px-2 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
									title="Copy formatted JSON"
								>
									{#if rawJsonCopied}
										<Check class="w-3 h-3 mr-1 text-green-500" />
										Copied!
									{:else}
										<Copy class="w-3 h-3 mr-1" />
										Copy Raw
									{/if}
								</button>
							</div>
							<div class="p-4 max-h-96 overflow-auto">
								{#if parsedJsonContent}
									<JsonViewer data={parsedJsonContent} expanded={true} />
								{:else}
									<!-- Fallback to plain text if JSON parsing fails -->
									<div class="max-w-none">
										{@html renderContent($currentResult.content || '', $currentResult.job.output_format, $currentResult.images)}
									</div>
								{/if}
							</div>
						</div>
					{:else}
						<!-- Other formats -->
						<div class="max-w-none">
							{@html renderContent($currentResult.content || '', $currentResult.job.output_format, $currentResult.images)}
						</div>
					{/if}
				</div>

				<!-- Extracted Images -->
				{#if $currentResult.images && $currentResult.images.length > 0}
					<div class="border-t border-gray-200 dark:border-gray-700">
						<div class="px-6 py-4">
							<h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4 flex items-center">
								<Image class="w-5 h-5 mr-2 text-blue-500" />
								Extracted Images ({$currentResult.images.length})
							</h3>
							<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
								{#each $currentResult.images as imageUrl, index}
									<div class="relative group">
										<img
											src={imageUrl}
											alt="Extracted image {index + 1}"
											class="w-full h-auto rounded-lg border border-gray-200 dark:border-gray-600 hover:border-blue-500 dark:hover:border-blue-400 transition-colors duration-200"
											loading="lazy"
										/>
										<div class="absolute top-2 left-2 bg-black bg-opacity-50 text-white text-xs px-2 py-1 rounded">
											{index + 1}
										</div>
										<!-- Download individual image -->
										<a
											href={imageUrl}
											download="extracted_image_{index + 1}"
											class="absolute top-2 right-2 bg-black bg-opacity-50 hover:bg-opacity-70 text-white p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200"
											title="Download image"
										>
											<Download class="w-4 h-4" />
										</a>
									</div>
								{/each}
							</div>
						</div>
					</div>
				{/if}
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
									{#if $selectedPages.size === $currentPDF.total_pages}
										<button
											onclick={clearSelection}
											class="text-sm text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300"
										>
											Deselect All
										</button>
									{:else}
										<button
											onclick={selectAllPages}
											class="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
										>
											Select All
										</button>
										{#if $selectedPages.size > 0}
											<button
												onclick={clearSelection}
												class="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
											>
												Clear Selection
											</button>
										{/if}
									{/if}
								</div>
							</div>
							<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
								{#if $selectedPages.size === $currentPDF.total_pages}
									All {$currentPDF.total_pages} pages selected
								{:else if $selectedPages.size === 0}
									No pages selected
								{:else}
									{$selectedPages.size} of {$currentPDF.total_pages} pages selected
								{/if}
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
													: 'border-gray-200 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'}"
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
										class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-200 dark:border-gray-600"
									/>
									<span class="ml-3 text-sm text-gray-700 dark:text-gray-300 capitalize">
										{format}
									</span>
								</label>
							{/each}
						</div>
					</div>

					<!-- LLM Configuration -->
					<div class="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
						<h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4 flex items-center">
							<Brain class="w-5 h-5 mr-2 text-purple-500" />
							LLM Configuration
						</h3>
						
						<div class="space-y-4">
							<!-- Use LLM Toggle -->
							<label class="flex items-start">
								<input
									type="checkbox"
									bind:checked={$conversionOptions.use_llm}
									class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-200 dark:border-gray-600 mt-0.5"
								/>
								<div class="ml-3">
									<div class="flex items-center">
										<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Use LLM Enhancement</span>
									</div>
									<p class="text-xs text-gray-500 dark:text-gray-400">
										Enhance accuracy with AI models
									</p>
								</div>
							</label>

							{#if $conversionOptions.use_llm}
								<!-- LLM Service Selection -->
								<div>
									<label for="llm-service" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										LLM Service
									</label>
									<select
										id="llm-service"
										bind:value={$llmConfig.default_llm_service}
										onchange={(e) => updateLLMService(e.currentTarget.value)}
										class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
									>
										<option value="">Select a service...</option>
										<option value="marker.services.gemini.GoogleGeminiService">Google Gemini</option>
										<option value="marker.services.openai.OpenAIService">OpenAI</option>
										<option value="marker.services.claude.ClaudeService">Anthropic Claude</option>
										<option value="marker.services.ollama.OllamaService">Ollama (Local)</option>
										<option value="marker.services.vertex.GoogleVertexService">Google Vertex AI</option>
									</select>
								</div>

								<!-- API Keys based on selected service -->
								{#if $llmConfig.default_llm_service === 'marker.services.gemini.GoogleGeminiService'}
									<div>
										<div class="flex items-center justify-between mb-2">
											<label for="gemini-key" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
												Gemini API Key
											</label>
											<button
												type="button"
												onclick={() => testServiceConnection('marker.services.gemini.GoogleGeminiService')}
												disabled={testingServices['marker.services.gemini.GoogleGeminiService'] || !$llmConfig.gemini_api_key}
												class="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30"
											>
												{#if testingServices['marker.services.gemini.GoogleGeminiService']}
													<Loader2 class="w-3 h-3 mr-1 animate-spin" />
													Testing...
												{:else}
													<TestTube class="w-3 h-3 mr-1" />
													Test
												{/if}
											</button>
										</div>
										<div class="relative">
											<input
												id="gemini-key"
												type={showApiKeys.gemini ? 'text' : 'password'}
												bind:value={$llmConfig.gemini_api_key}
												placeholder="Enter your Gemini API key"
												class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 pr-10 text-sm"
											/>
											<button
												type="button"
												onclick={() => toggleApiKeyVisibility('gemini')}
												class="absolute inset-y-0 right-0 pr-3 flex items-center"
											>
												{#if showApiKeys.gemini}
													<EyeOff class="h-4 w-4 text-gray-400" />
												{:else}
													<Eye class="h-4 w-4 text-gray-400" />
												{/if}
											</button>
										</div>
										{#if testResults['marker.services.gemini.GoogleGeminiService']}
											<div class="mt-2 p-2 rounded-md {testResults['marker.services.gemini.GoogleGeminiService'].success ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'}">
												<div class="flex items-center">
													{#if testResults['marker.services.gemini.GoogleGeminiService'].success}
														<Check class="w-4 h-4 text-green-600 dark:text-green-400 mr-2" />
													{:else}
														<AlertCircle class="w-4 h-4 text-red-600 dark:text-red-400 mr-2" />
													{/if}
													<span class="text-sm {testResults['marker.services.gemini.GoogleGeminiService'].success ? 'text-green-800 dark:text-green-300' : 'text-red-800 dark:text-red-300'}">
														{testResults['marker.services.gemini.GoogleGeminiService'].message}
													</span>
												</div>
											</div>
										{/if}
									</div>
								{:else if $llmConfig.default_llm_service === 'marker.services.openai.OpenAIService'}
									<div>
										<div class="flex items-center justify-between mb-2">
											<label for="openai-key" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
												OpenAI API Key
											</label>
											<button
												type="button"
												onclick={() => testServiceConnection('marker.services.openai.OpenAIService')}
												disabled={testingServices['marker.services.openai.OpenAIService'] || !$llmConfig.openai_api_key}
												class="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30"
											>
												{#if testingServices['marker.services.openai.OpenAIService']}
													<Loader2 class="w-3 h-3 mr-1 animate-spin" />
													Testing...
												{:else}
													<TestTube class="w-3 h-3 mr-1" />
													Test
												{/if}
											</button>
										</div>
										<div class="relative">
											<input
												id="openai-key"
												type={showApiKeys.openai ? 'text' : 'password'}
												bind:value={$llmConfig.openai_api_key}
												placeholder="Enter your OpenAI API key"
												class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 pr-10 text-sm"
											/>
											<button
												type="button"
												onclick={() => toggleApiKeyVisibility('openai')}
												class="absolute inset-y-0 right-0 pr-3 flex items-center"
											>
												{#if showApiKeys.openai}
													<EyeOff class="h-4 w-4 text-gray-400" />
												{:else}
													<Eye class="h-4 w-4 text-gray-400" />
												{/if}
											</button>
										</div>
										<div class="mt-2 grid grid-cols-1 md:grid-cols-2 gap-4">
											<div>
												<label for="openai-model" class="block text-xs font-medium text-gray-700 dark:text-gray-300">
													Model
												</label>
												<input
													id="openai-model"
													type="text"
													bind:value={$llmConfig.openai_model}
													placeholder="gpt-4o"
													class="mt-1 block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
												/>
											</div>
											<div>
												<label for="openai-base-url" class="block text-xs font-medium text-gray-700 dark:text-gray-300">
													Base URL (optional)
												</label>
												<input
													id="openai-base-url"
													type="text"
													bind:value={$llmConfig.openai_base_url}
													placeholder="https://api.openai.com/v1"
													class="mt-1 block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
												/>
											</div>
										</div>
										{#if testResults['marker.services.openai.OpenAIService']}
											<div class="mt-2 p-2 rounded-md {testResults['marker.services.openai.OpenAIService'].success ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'}">
												<div class="flex items-center">
													{#if testResults['marker.services.openai.OpenAIService'].success}
														<Check class="w-4 h-4 text-green-600 dark:text-green-400 mr-2" />
													{:else}
														<AlertCircle class="w-4 h-4 text-red-600 dark:text-red-400 mr-2" />
													{/if}
													<span class="text-sm {testResults['marker.services.openai.OpenAIService'].success ? 'text-green-800 dark:text-green-300' : 'text-red-800 dark:text-red-300'}">
														{testResults['marker.services.openai.OpenAIService'].message}
													</span>
												</div>
											</div>
										{/if}
									</div>
								{:else if $llmConfig.default_llm_service === 'marker.services.claude.ClaudeService'}
									<div>
										<div class="flex items-center justify-between mb-2">
											<label for="claude-key" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
												Claude API Key
											</label>
											<button
												type="button"
												onclick={() => testServiceConnection('marker.services.claude.ClaudeService')}
												disabled={testingServices['marker.services.claude.ClaudeService'] || !$llmConfig.claude_api_key}
												class="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30"
											>
												{#if testingServices['marker.services.claude.ClaudeService']}
													<Loader2 class="w-3 h-3 mr-1 animate-spin" />
													Testing...
												{:else}
													<TestTube class="w-3 h-3 mr-1" />
													Test
												{/if}
											</button>
										</div>
										<div class="relative">
											<input
												id="claude-key"
												type={showApiKeys.claude ? 'text' : 'password'}
												bind:value={$llmConfig.claude_api_key}
												placeholder="Enter your Claude API key"
												class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 pr-10 text-sm"
											/>
											<button
												type="button"
												onclick={() => toggleApiKeyVisibility('claude')}
												class="absolute inset-y-0 right-0 pr-3 flex items-center"
											>
												{#if showApiKeys.claude}
													<EyeOff class="h-4 w-4 text-gray-400" />
												{:else}
													<Eye class="h-4 w-4 text-gray-400" />
												{/if}
											</button>
										</div>
										<div class="mt-2">
											<label for="claude-model" class="block text-xs font-medium text-gray-700 dark:text-gray-300">
												Model
											</label>
											<input
												id="claude-model"
												type="text"
												bind:value={$llmConfig.claude_model_name}
												placeholder="claude-3-sonnet-20240229"
												class="mt-1 block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
											/>
										</div>
										{#if testResults['marker.services.claude.ClaudeService']}
											<div class="mt-2 p-2 rounded-md {testResults['marker.services.claude.ClaudeService'].success ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'}">
												<div class="flex items-center">
													{#if testResults['marker.services.claude.ClaudeService'].success}
														<Check class="w-4 h-4 text-green-600 dark:text-green-400 mr-2" />
													{:else}
														<AlertCircle class="w-4 h-4 text-red-600 dark:text-red-400 mr-2" />
													{/if}
													<span class="text-sm {testResults['marker.services.claude.ClaudeService'].success ? 'text-green-800 dark:text-green-300' : 'text-red-800 dark:text-red-300'}">
														{testResults['marker.services.claude.ClaudeService'].message}
													</span>
												</div>
											</div>
										{/if}
									</div>
								{:else if $llmConfig.default_llm_service === 'marker.services.ollama.OllamaService'}
									<div>
										<div class="flex items-center justify-between mb-2">
											<label for="ollama-url" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
												Ollama Configuration
											</label>
											<button
												type="button"
												onclick={() => testServiceConnection('marker.services.ollama.OllamaService')}
												disabled={testingServices['marker.services.ollama.OllamaService']}
												class="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30"
											>
												{#if testingServices['marker.services.ollama.OllamaService']}
													<Loader2 class="w-3 h-3 mr-1 animate-spin" />
													Testing...
												{:else}
													<TestTube class="w-3 h-3 mr-1" />
													Test
												{/if}
											</button>
										</div>
										<div class="space-y-2">
											<div>
												<label for="ollama-url" class="block text-xs font-medium text-gray-700 dark:text-gray-300">
													Base URL
												</label>
												<input
													id="ollama-url"
													type="text"
													bind:value={$llmConfig.ollama_base_url}
													placeholder="http://localhost:11434"
													class="mt-1 block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
												/>
											</div>
											<div>
												<label for="ollama-model" class="block text-xs font-medium text-gray-700 dark:text-gray-300">
													Model
												</label>
												<input
													id="ollama-model"
													type="text"
													bind:value={$llmConfig.ollama_model}
													placeholder="llama3.2:latest"
													class="mt-1 block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
												/>
											</div>
										</div>
										{#if testResults['marker.services.ollama.OllamaService']}
											<div class="mt-2 p-2 rounded-md {testResults['marker.services.ollama.OllamaService'].success ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'}">
												<div class="flex items-center">
													{#if testResults['marker.services.ollama.OllamaService'].success}
														<Check class="w-4 h-4 text-green-600 dark:text-green-400 mr-2" />
													{:else}
														<AlertCircle class="w-4 h-4 text-red-600 dark:text-red-400 mr-2" />
													{/if}
													<span class="text-sm {testResults['marker.services.ollama.OllamaService'].success ? 'text-green-800 dark:text-green-300' : 'text-red-800 dark:text-red-300'}">
														{testResults['marker.services.ollama.OllamaService'].message}
													</span>
												</div>
											</div>
										{/if}
									</div>
								{:else if $llmConfig.default_llm_service === 'marker.services.vertex.GoogleVertexService'}
									<div>
										<div class="flex items-center justify-between mb-2">
											<label for="vertex-project" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
												Vertex AI Configuration
											</label>
											<button
												type="button"
												onclick={() => testServiceConnection('marker.services.vertex.GoogleVertexService')}
												disabled={testingServices['marker.services.vertex.GoogleVertexService'] || !$llmConfig.vertex_project_id}
												class="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30"
											>
												{#if testingServices['marker.services.vertex.GoogleVertexService']}
													<Loader2 class="w-3 h-3 mr-1 animate-spin" />
													Testing...
												{:else}
													<TestTube class="w-3 h-3 mr-1" />
													Test
												{/if}
											</button>
										</div>
										<div>
											<label for="vertex-project" class="block text-xs font-medium text-gray-700 dark:text-gray-300">
												Project ID
											</label>
											<input
												id="vertex-project"
												type="text"
												bind:value={$llmConfig.vertex_project_id}
												placeholder="your-gcp-project-id"
												class="mt-1 block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
											/>
											<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
												Requires Google Cloud authentication to be configured on the server
											</p>
										</div>
										{#if testResults['marker.services.vertex.GoogleVertexService']}
											<div class="mt-2 p-2 rounded-md {testResults['marker.services.vertex.GoogleVertexService'].success ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'}">
												<div class="flex items-center">
													{#if testResults['marker.services.vertex.GoogleVertexService'].success}
														<Check class="w-4 h-4 text-green-600 dark:text-green-400 mr-2" />
													{:else}
														<AlertCircle class="w-4 h-4 text-red-600 dark:text-red-400 mr-2" />
													{/if}
													<span class="text-sm {testResults['marker.services.vertex.GoogleVertexService'].success ? 'text-green-800 dark:text-green-300' : 'text-red-800 dark:text-red-300'}">
														{testResults['marker.services.vertex.GoogleVertexService'].message}
													</span>
												</div>
											</div>
										{/if}
									</div>
								{/if}
							{/if}
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
									bind:checked={$conversionOptions.force_ocr}
									class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-200 dark:border-gray-600 mt-0.5"
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
									class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-200 dark:border-gray-600 mt-0.5"
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
									class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-200 dark:border-gray-600 mt-0.5"
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
									class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-200 dark:border-gray-600 mt-0.5"
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
									class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-200 dark:border-gray-600 mt-0.5"
								/>
								<div class="ml-3">
									<div class="flex items-center">
										<Image class="w-4 h-4 mr-2 text-indigo-500" />
										<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Disable Image Extraction</span>
									</div>
									<p class="text-xs text-gray-500 dark:text-gray-400">
										Skip extracting images
									</p>
								</div>
							</label>

							<label class="flex items-start">
								<input
									type="checkbox"
									bind:checked={$conversionOptions.paginate_output}
									class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-200 dark:border-gray-600 mt-0.5"
								/>
								<div class="ml-3">
									<div class="flex items-center">
										<FileText class="w-4 h-4 mr-2 text-teal-500" />
										<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Paginate Output</span>
									</div>
									<p class="text-xs text-gray-500 dark:text-gray-400">
										Include page breaks in output
									</p>
								</div>
							</label>
						</div>
					</div>
				</div>
			</div>
		{/if}
	</div>
{/if}

<style>
	/* Custom styles for better markdown rendering */
	:global(.prose table) {
		border-collapse: collapse;
		border: 1px solid rgb(229 231 235);
	}
	
	:global(.dark .prose table) {
		border-color: rgb(55 65 81);
	}
	
	:global(.prose th) {
		border: 1px solid rgb(229 231 235);
		background-color: rgb(249 250 251);
		padding: 0.5rem 1rem;
		font-weight: 600;
	}
	
	:global(.dark .prose th) {
		border-color: rgb(55 65 81);
		background-color: rgb(55 65 81);
	}
	
	:global(.prose td) {
		border: 1px solid rgb(229 231 235);
		padding: 0.5rem 1rem;
	}
	
	:global(.dark .prose td) {
		border-color: rgb(55 65 81);
	}
	
	:global(.prose blockquote) {
		border-left: 4px solid rgb(59 130 246);
		background-color: rgb(239 246 255);
		padding-left: 1rem;
		padding-top: 0.5rem;
		padding-bottom: 0.5rem;
		margin: 1rem 0;
	}
	
	:global(.dark .prose blockquote) {
		background-color: rgb(30 58 138 / 0.2);
	}
	
	:global(.prose code:not(pre code)) {
		background-color: rgb(243 244 246);
		padding: 0.125rem 0.25rem;
		border-radius: 0.25rem;
		font-size: 0.875rem;
	}
	
	:global(.dark .prose code:not(pre code)) {
		background-color: rgb(31 41 55);
	}
	
	:global(.prose pre) {
		background-color: rgb(243 244 246);
		border: 1px solid rgb(229 231 235);
		border-radius: 0.5rem;
		padding: 1rem;
		overflow-x: auto;
	}
	
	:global(.dark .prose pre) {
		background-color: rgb(31 41 55);
		border-color: rgb(55 65 81);
	}
	
	:global(.prose pre code) {
		background-color: transparent;
		padding: 0;
	}
	
	/* Math expressions styling */
	:global(.prose .math) {
		font-family: ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace;
		color: rgb(147 51 234);
	}
	
	:global(.dark .prose .math) {
		color: rgb(196 181 253);
	}
	
	/* Image styling within prose */
	:global(.prose img) {
		border-radius: 0.5rem;
		border: 1px solid rgb(229 231 235);
		max-width: 100%;
		height: auto;
	}
	
	:global(.dark .prose img) {
		border-color: rgb(75 85 99);
	}
	
	/* List styling */
	:global(.prose ul) {
		list-style-type: disc;
		padding-left: 1.5rem;
	}
	
	:global(.prose ol) {
		list-style-type: decimal;
		padding-left: 1.5rem;
	}
	
	/* Link styling */
	:global(.prose a) {
		color: rgb(37 99 235);
		text-decoration: underline;
	}
	
	:global(.dark .prose a) {
		color: rgb(96 165 250);
	}
	
	:global(.prose a:hover) {
		color: rgb(29 78 216);
	}
	
	:global(.dark .prose a:hover) {
		color: rgb(147 197 253);
	}
</style> 
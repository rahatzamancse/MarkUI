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
		Copy,
		ChevronDown,
		ChevronUp,
		Info
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
	import { OutputFormat, ConversionStatus, type ConversionJobCreate, type ServerConfigResponse } from '$lib/types';
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
	let currentPDFId: number | null = $state(null);
	let serverConfig: ServerConfigResponse | null = $state(null);
	let loadingServerConfig = $state(false);
	let advancedOptionsExpanded = $state(false);
	
	// Track which API keys are from environment variables (pre-populated and hidden)
	let envApiKeys = $state({
		gemini: false,
		openai: false,
		claude: false
	});

	// Load server configuration on mount
	onMount(async () => {
		try {
			loadingServerConfig = true;
			serverConfig = await MarkUIAPI.getServerConfig();
			
			// Pre-populate API keys from environment variables
			if (serverConfig.has_gemini_api_key) {
				actions.updateLLMConfig('gemini_api_key', '••••••••••••••••'); // Placeholder for hidden key
				envApiKeys.gemini = true;
			}
			
			if (serverConfig.has_openai_api_key) {
				actions.updateLLMConfig('openai_api_key', '••••••••••••••••'); // Placeholder for hidden key
				envApiKeys.openai = true;
			}
			
			if (serverConfig.has_claude_api_key) {
				actions.updateLLMConfig('claude_api_key', '••••••••••••••••'); // Placeholder for hidden key
				envApiKeys.claude = true;
			}
			
			// Pre-populate default configurations
			if (serverConfig.default_openai_model) {
				actions.updateLLMConfig('openai_model', serverConfig.default_openai_model);
			}
			
			if (serverConfig.default_openai_base_url) {
				actions.updateLLMConfig('openai_base_url', serverConfig.default_openai_base_url);
			}
			
			if (serverConfig.default_claude_model_name) {
				actions.updateLLMConfig('claude_model_name', serverConfig.default_claude_model_name);
			}
			
			if (serverConfig.default_ollama_base_url) {
				actions.updateLLMConfig('ollama_base_url', serverConfig.default_ollama_base_url);
			}
			
			if (serverConfig.default_ollama_model) {
				actions.updateLLMConfig('ollama_model', serverConfig.default_ollama_model);
			}
			
			if (serverConfig.default_vertex_project_id) {
				actions.updateLLMConfig('vertex_project_id', serverConfig.default_vertex_project_id);
			}
			
		} catch (error) {
			console.error('Failed to load server configuration:', error);
		} finally {
			loadingServerConfig = false;
		}
	});

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
		if ($currentPDF && $currentPDF.id !== currentPDFId) {
			currentPDFId = $currentPDF.id;
			loadPreviewImages();
			
			// Ensure all pages are selected by default if none are selected
			if ($selectedPages.size === 0) {
				actions.selectAllPages($currentPDF.total_pages);
			}
		} else if (!$currentPDF) {
			currentPDFId = null;
			previewImages = [];
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

	function restoreEnvironmentCredentials(service: string) {
		if (service === 'gemini' && serverConfig?.has_gemini_api_key) {
			envApiKeys.gemini = true;
			actions.updateLLMConfig('gemini_api_key', '••••••••••••••••');
		} else if (service === 'openai' && serverConfig?.has_openai_api_key) {
			envApiKeys.openai = true;
			actions.updateLLMConfig('openai_api_key', '••••••••••••••••');
		} else if (service === 'claude' && serverConfig?.has_claude_api_key) {
			envApiKeys.claude = true;
			actions.updateLLMConfig('claude_api_key', '••••••••••••••••');
		}
	}

	async function testServiceConnection(serviceName: string) {
		testingServices[serviceName] = true;
		delete testResults[serviceName];
		
		try {
			const testRequest: any = {
				service_name: serviceName,
				ollama_base_url: $llmConfig.ollama_base_url || undefined,
				ollama_model: $llmConfig.ollama_model || undefined,
				openai_model: $llmConfig.openai_model || undefined,
				openai_base_url: $llmConfig.openai_base_url || undefined,
				claude_model_name: $llmConfig.claude_model_name || undefined,
				vertex_project_id: $llmConfig.vertex_project_id || undefined
			};

			// Only include API keys if they're not from environment variables and have values
			if (!envApiKeys.gemini && $llmConfig.gemini_api_key) {
				testRequest.gemini_api_key = $llmConfig.gemini_api_key;
			}
			if (!envApiKeys.openai && $llmConfig.openai_api_key) {
				testRequest.openai_api_key = $llmConfig.openai_api_key;
			}
			if (!envApiKeys.claude && $llmConfig.claude_api_key) {
				testRequest.claude_api_key = $llmConfig.claude_api_key;
			}

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
				llm_model: $conversionOptions.llm_model,
				
				// Performance & Quality Options
				lowres_image_dpi: $conversionOptions.lowres_image_dpi,
				highres_image_dpi: $conversionOptions.highres_image_dpi,
				layout_batch_size: $conversionOptions.layout_batch_size,
				detection_batch_size: $conversionOptions.detection_batch_size,
				recognition_batch_size: $conversionOptions.recognition_batch_size,
				
				// OCR & Text Processing Options
				languages: $conversionOptions.languages ? $conversionOptions.languages.split(',').map(lang => lang.trim()).filter(lang => lang.length > 0) : undefined,
				ocr_task_name: $conversionOptions.ocr_task_name,
				disable_ocr_math: $conversionOptions.disable_ocr_math,
				keep_chars: $conversionOptions.keep_chars,
				
				// Layout & Structure Options
				force_layout_block: $conversionOptions.force_layout_block,
				column_gap_ratio: $conversionOptions.column_gap_ratio,
				gap_threshold: $conversionOptions.gap_threshold,
				list_gap_threshold: $conversionOptions.list_gap_threshold,
				
				// Table Processing Options
				detect_boxes: $conversionOptions.detect_boxes,
				table_rec_batch_size: $conversionOptions.table_rec_batch_size,
				max_table_rows: $conversionOptions.max_table_rows,
				max_rows_per_batch: $conversionOptions.max_rows_per_batch,
				
				// Section & Header Processing
				level_count: $conversionOptions.level_count,
				merge_threshold: $conversionOptions.merge_threshold,
				default_level: $conversionOptions.default_level,
				
				// Advanced Processing Options
				min_equation_height: $conversionOptions.min_equation_height,
				equation_batch_size: $conversionOptions.equation_batch_size,
				inlinemath_min_ratio: $conversionOptions.inlinemath_min_ratio,
				
				// Output Control Options
				page_separator: $conversionOptions.page_separator,
				extract_images: $conversionOptions.extract_images,
				
				// Debug Options
				debug: $conversionOptions.debug,
				debug_layout_images: $conversionOptions.debug_layout_images,
				debug_pdf_images: $conversionOptions.debug_pdf_images,
				debug_json: $conversionOptions.debug_json,
				debug_data_folder: $conversionOptions.debug_data_folder,
				
				// LLM Processing Options
				max_concurrency: $conversionOptions.max_concurrency,
				confidence_threshold: $conversionOptions.confidence_threshold
			};

			// Only include API keys if they're not from environment variables and have values
			if (!envApiKeys.gemini && $llmConfig.gemini_api_key) {
				jobData.gemini_api_key = $llmConfig.gemini_api_key;
			}
			if (!envApiKeys.openai && $llmConfig.openai_api_key) {
				jobData.openai_api_key = $llmConfig.openai_api_key;
			}
			if (!envApiKeys.claude && $llmConfig.claude_api_key) {
				jobData.claude_api_key = $llmConfig.claude_api_key;
			}

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
		if (!content || content.trim() === '') {
			return '<div class="text-gray-500 dark:text-gray-400 italic">No content available</div>';
		}
		
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
											<div class="flex items-center">
												<label for="gemini-key" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
													Gemini API Key
													{#if envApiKeys.gemini}
														<span class="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400">
															<Server class="w-3 h-3 mr-1" />
															From Environment
														</span>
													{/if}
												</label>
												{#if serverConfig?.has_gemini_api_key && !envApiKeys.gemini}
													<button
														type="button"
														onclick={() => restoreEnvironmentCredentials('gemini')}
														class="ml-3 inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded-md text-green-700 bg-green-100 hover:bg-green-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 dark:bg-green-900/20 dark:text-green-400 dark:hover:bg-green-900/30 transition-colors duration-200 cursor-pointer"
														title="Use environment variable"
													>
														<Server class="w-3 h-3 mr-1" />
														From Environment
													</button>
												{:else if serverConfig?.has_gemini_api_key === false}
													<button
														type="button"
														disabled
														class="ml-3 inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded-md text-red-700 bg-red-100 dark:bg-red-900/20 dark:text-red-400 opacity-50 cursor-not-allowed"
														title="No environment variable configured"
													>
														<Server class="w-3 h-3 mr-1" />
														From Environment
													</button>
												{/if}
											</div>
											<button
												type="button"
												onclick={() => testServiceConnection('marker.services.gemini.GoogleGeminiService')}
												disabled={testingServices['marker.services.gemini.GoogleGeminiService'] || !$llmConfig.gemini_api_key}
												class="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30 transition-colors duration-200 cursor-pointer"
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
												placeholder={envApiKeys.gemini ? "Using environment variable (hidden)" : "Enter your Gemini API key"}
												readonly={envApiKeys.gemini}
												class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 pr-10 text-sm {envApiKeys.gemini ? 'bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400' : ''}"
												onfocus={(e) => {
													if (envApiKeys.gemini) {
														// Clear the placeholder and allow editing
														envApiKeys.gemini = false;
														actions.updateLLMConfig('gemini_api_key', '');
														e.currentTarget.placeholder = "Enter your Gemini API key";
														e.currentTarget.classList.remove('bg-gray-50', 'dark:bg-gray-800', 'text-gray-500', 'dark:text-gray-400');
														e.currentTarget.readOnly = false;
													}
												}}
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
										{#if envApiKeys.gemini}
											<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
												Using API key from server environment variables. Click the field to override with your own key.
											</p>
										{/if}
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
											<div class="flex items-center">
												<label for="openai-key" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
													OpenAI API Key
													{#if envApiKeys.openai}
														<span class="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400">
															<Server class="w-3 h-3 mr-1" />
															From Environment
														</span>
													{/if}
												</label>
												{#if serverConfig?.has_openai_api_key && !envApiKeys.openai}
													<button
														type="button"
														onclick={() => restoreEnvironmentCredentials('openai')}
														class="ml-3 inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded-md text-green-700 bg-green-100 hover:bg-green-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 dark:bg-green-900/20 dark:text-green-400 dark:hover:bg-green-900/30 transition-colors duration-200 cursor-pointer"
														title="Use environment variable"
													>
														<Server class="w-3 h-3 mr-1" />
														From Environment
													</button>
												{:else if serverConfig?.has_openai_api_key === false}
													<button
														type="button"
														disabled
														class="ml-3 inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded-md text-red-700 bg-red-100 dark:bg-red-900/20 dark:text-red-400 opacity-50 cursor-not-allowed"
														title="No environment variable configured"
													>
														<Server class="w-3 h-3 mr-1" />
														From Environment
													</button>
												{/if}
											</div>
											<button
												type="button"
												onclick={() => testServiceConnection('marker.services.openai.OpenAIService')}
												disabled={testingServices['marker.services.openai.OpenAIService'] || !$llmConfig.openai_api_key}
												class="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30 transition-colors duration-200 cursor-pointer"
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
												placeholder={envApiKeys.openai ? "Using environment variable (hidden)" : "Enter your OpenAI API key"}
												readonly={envApiKeys.openai}
												class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 pr-10 text-sm {envApiKeys.openai ? 'bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400' : ''}"
												onfocus={(e) => {
													if (envApiKeys.openai) {
														// Clear the placeholder and allow editing
														envApiKeys.openai = false;
														actions.updateLLMConfig('openai_api_key', '');
														e.currentTarget.placeholder = "Enter your OpenAI API key";
														e.currentTarget.classList.remove('bg-gray-50', 'dark:bg-gray-800', 'text-gray-500', 'dark:text-gray-400');
														e.currentTarget.readOnly = false;
													}
												}}
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
										{#if envApiKeys.openai}
											<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
												Using API key from server environment variables. Click the field to override with your own key.
											</p>
										{/if}
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
											<div class="flex items-center">
												<label for="claude-key" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
													Claude API Key
													{#if envApiKeys.claude}
														<span class="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400">
															<Server class="w-3 h-3 mr-1" />
															From Environment
														</span>
													{/if}
												</label>
												{#if serverConfig?.has_claude_api_key && !envApiKeys.claude}
													<button
														type="button"
														onclick={() => restoreEnvironmentCredentials('claude')}
														class="ml-3 inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded-md text-green-700 bg-green-100 hover:bg-green-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 dark:bg-green-900/20 dark:text-green-400 dark:hover:bg-green-900/30 transition-colors duration-200 cursor-pointer"
														title="Use environment variable"
													>
														<Server class="w-3 h-3 mr-1" />
														From Environment
													</button>
												{:else if serverConfig?.has_claude_api_key === false}
													<button
														type="button"
														disabled
														class="ml-3 inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded-md text-red-700 bg-red-100 dark:bg-red-900/20 dark:text-red-400 opacity-50 cursor-not-allowed"
														title="No environment variable configured"
													>
														<Server class="w-3 h-3 mr-1" />
														From Environment
													</button>
												{/if}
											</div>
											<button
												type="button"
												onclick={() => testServiceConnection('marker.services.claude.ClaudeService')}
												disabled={testingServices['marker.services.claude.ClaudeService'] || !$llmConfig.claude_api_key}
												class="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30 transition-colors duration-200 cursor-pointer"
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
												placeholder={envApiKeys.claude ? "Using environment variable (hidden)" : "Enter your Claude API key"}
												readonly={envApiKeys.claude}
												class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 pr-10 text-sm {envApiKeys.claude ? 'bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400' : ''}"
												onfocus={(e) => {
													if (envApiKeys.claude) {
														// Clear the placeholder and allow editing
														envApiKeys.claude = false;
														actions.updateLLMConfig('claude_api_key', '');
														e.currentTarget.placeholder = "Enter your Claude API key";
														e.currentTarget.classList.remove('bg-gray-50', 'dark:bg-gray-800', 'text-gray-500', 'dark:text-gray-400');
														e.currentTarget.readOnly = false;
													}
												}}
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
										{#if envApiKeys.claude}
											<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
												Using API key from server environment variables. Click the field to override with your own key.
											</p>
										{/if}
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
												class="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30 transition-colors duration-200 cursor-pointer"
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
												class="inline-flex items-center px-2 py-1 border border-transparent text-xs font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30 transition-colors duration-200 cursor-pointer"
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

					<!-- Advanced Options -->
					<div class="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
						<button
							type="button"
							onclick={() => advancedOptionsExpanded = !advancedOptionsExpanded}
							class="w-full flex items-center justify-between text-lg font-medium text-gray-900 dark:text-white mb-4 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
						>
							<span>Advanced Options</span>
							{#if advancedOptionsExpanded}
								<ChevronUp class="w-5 h-5" />
							{:else}
								<ChevronDown class="w-5 h-5" />
							{/if}
						</button>
						
						{#if advancedOptionsExpanded}
							<!-- Performance & Quality -->
							<div class="mb-6">
								<h4 class="text-md font-medium text-gray-800 dark:text-gray-200 mb-3">Performance & Quality</h4>
								<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
									<div>
										<label for="lowres-dpi" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											Low-res DPI
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													DPI for layout and line detection (50-300)
												</div>
											</div>
										</label>
										<input
											id="lowres-dpi"
											type="number"
											bind:value={$conversionOptions.lowres_image_dpi}
											placeholder="96"
											min="50"
											max="300"
											class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
										/>
									</div>
									<div>
										<label for="highres-dpi" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											High-res DPI
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													DPI for OCR processing (100-600)
												</div>
											</div>
										</label>
										<input
											id="highres-dpi"
											type="number"
											bind:value={$conversionOptions.highres_image_dpi}
											placeholder="192"
											min="100"
											max="600"
											class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
										/>
									</div>
									<div>
										<label for="layout-batch" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											Layout Batch
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Batch size for layout model (1-32)
												</div>
											</div>
										</label>
										<input
											id="layout-batch"
											type="number"
											bind:value={$conversionOptions.layout_batch_size}
											placeholder="Auto"
											min="1"
											max="32"
											class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
										/>
									</div>
									<div>
										<label for="recognition-batch" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											Recognition Batch
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Batch size for recognition model (1-32)
												</div>
											</div>
										</label>
										<input
											id="recognition-batch"
											type="number"
											bind:value={$conversionOptions.recognition_batch_size}
											placeholder="Auto"
											min="1"
											max="32"
											class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
										/>
									</div>
								</div>
							</div>

							<!-- OCR & Text Processing -->
							<div class="mb-6">
								<h4 class="text-md font-medium text-gray-800 dark:text-gray-200 mb-3">OCR & Text Processing</h4>
								<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
									<div>
										<label for="languages" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											Languages
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Comma-separated language codes (e.g., en,fr,de)
												</div>
											</div>
										</label>
										<input
											id="languages"
											type="text"
											bind:value={$conversionOptions.languages}
											placeholder="en,fr,de"
											class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
										/>
									</div>
									<div>
										<label for="ocr-task" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											OCR Mode
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													OCR processing mode with or without bounding boxes
												</div>
											</div>
										</label>
										<select
											id="ocr-task"
											bind:value={$conversionOptions.ocr_task_name}
											class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
										>
											<option value="">Default</option>
											<option value="ocr_with_boxes">With boxes</option>
											<option value="ocr_without_boxes">Without boxes</option>
										</select>
									</div>
									<div class="flex items-center">
										<input
											id="disable-ocr-math"
											type="checkbox"
											bind:checked={$conversionOptions.disable_ocr_math}
											class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-200 dark:border-gray-600"
										/>
										<label for="disable-ocr-math" class="flex items-center ml-2 text-sm text-gray-700 dark:text-gray-300">
											Disable OCR Math
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Disable inline math recognition in OCR
												</div>
											</div>
										</label>
									</div>
									<div class="flex items-center">
										<input
											id="keep-chars"
											type="checkbox"
											bind:checked={$conversionOptions.keep_chars}
											class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-200 dark:border-gray-600"
										/>
										<label for="keep-chars" class="flex items-center ml-2 text-sm text-gray-700 dark:text-gray-300">
											Keep Characters
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Keep individual character information
												</div>
											</div>
										</label>
									</div>
								</div>
							</div>

							<!-- Layout & Structure -->
							<div class="mb-6">
								<h4 class="text-md font-medium text-gray-800 dark:text-gray-200 mb-3">Layout & Structure</h4>
								<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
									<div>
										<label for="force-layout" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											Force Layout
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Force every page to be treated as specific block type
												</div>
											</div>
										</label>
										<select
											id="force-layout"
											bind:value={$conversionOptions.force_layout_block}
											class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
										>
											<option value="">Auto-detect</option>
											<option value="Table">Table</option>
											<option value="Text">Text</option>
											<option value="Figure">Figure</option>
										</select>
									</div>
									<div>
										<label for="column-gap" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											Column Gap
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Minimum ratio of page width to column gap (0-1)
												</div>
											</div>
										</label>
										<input
											id="column-gap"
											type="number"
											bind:value={$conversionOptions.column_gap_ratio}
											placeholder="0.02"
											min="0"
											max="1"
											step="0.01"
											class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
										/>
									</div>
									<div>
										<label for="gap-threshold" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											Block Gap
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Minimum gap between blocks for grouping (0-1)
												</div>
											</div>
										</label>
										<input
											id="gap-threshold"
											type="number"
											bind:value={$conversionOptions.gap_threshold}
											placeholder="0.05"
											min="0"
											max="1"
											step="0.01"
											class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
										/>
									</div>
									<div>
										<label for="list-gap" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											List Gap
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Minimum gap between list items (0-1)
												</div>
											</div>
										</label>
										<input
											id="list-gap"
											type="number"
											bind:value={$conversionOptions.list_gap_threshold}
											placeholder="0.1"
											min="0"
											max="1"
											step="0.01"
											class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
										/>
									</div>
								</div>
							</div>

							<!-- Table Processing -->
							<div class="mb-6">
								<h4 class="text-md font-medium text-gray-800 dark:text-gray-200 mb-3">Table Processing</h4>
								<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
									<div class="flex items-center">
										<input
											id="detect-boxes"
											type="checkbox"
											bind:checked={$conversionOptions.detect_boxes}
											class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-200 dark:border-gray-600"
										/>
										<label for="detect-boxes" class="flex items-center ml-2 text-sm text-gray-700 dark:text-gray-300">
											Detect Boxes
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Detect table boxes for recognition
												</div>
											</div>
										</label>
									</div>
									<div>
										<label for="table-batch" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											Table Batch
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Batch size for table recognition (1-32)
												</div>
											</div>
										</label>
										<input
											id="table-batch"
											type="number"
											bind:value={$conversionOptions.table_rec_batch_size}
											placeholder="Auto"
											min="1"
											max="32"
											class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
										/>
									</div>
									<div>
										<label for="max-table-rows" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											Max Rows (LLM)
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Maximum table rows to process with LLM (1-500)
												</div>
											</div>
										</label>
										<input
											id="max-table-rows"
											type="number"
											bind:value={$conversionOptions.max_table_rows}
											placeholder="175"
											min="1"
											max="500"
											class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
										/>
									</div>
									<div>
										<label for="rows-per-batch" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											Rows per Batch
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Chunk tables with more rows than this (1-200)
												</div>
											</div>
										</label>
										<input
											id="rows-per-batch"
											type="number"
											bind:value={$conversionOptions.max_rows_per_batch}
											placeholder="60"
											min="1"
											max="200"
											class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
										/>
									</div>
								</div>
							</div>

							<!-- Section Headers -->
							<div class="mb-6">
								<h4 class="text-md font-medium text-gray-800 dark:text-gray-200 mb-3">Section Headers</h4>
								<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
									<div>
										<label for="level-count" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											Heading Levels
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Number of heading levels to use (1-10)
												</div>
											</div>
										</label>
										<input
											id="level-count"
											type="number"
											bind:value={$conversionOptions.level_count}
											placeholder="4"
											min="1"
											max="10"
											class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
										/>
									</div>
									<div>
										<label for="merge-threshold" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											Merge Threshold
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Minimum gap between headings for grouping (0-1)
												</div>
											</div>
										</label>
										<input
											id="merge-threshold"
											type="number"
											bind:value={$conversionOptions.merge_threshold}
											placeholder="0.25"
											min="0"
											max="1"
											step="0.01"
											class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
										/>
									</div>
									<div>
										<label for="default-level" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											Default Level
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Default heading level if none detected (1-6)
												</div>
											</div>
										</label>
										<input
											id="default-level"
											type="number"
											bind:value={$conversionOptions.default_level}
											placeholder="2"
											min="1"
											max="6"
											class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
										/>
									</div>
								</div>
							</div>

							<!-- Math & Equations -->
							<div class="mb-6">
								<h4 class="text-md font-medium text-gray-800 dark:text-gray-200 mb-3">Math & Equations</h4>
								<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
									<div>
										<label for="min-equation-height" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											Min Equation Height
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Minimum equation height ratio for processing (0-1)
												</div>
											</div>
										</label>
										<input
											id="min-equation-height"
											type="number"
											bind:value={$conversionOptions.min_equation_height}
											placeholder="0.06"
											min="0"
											max="1"
											step="0.01"
											class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
										/>
									</div>
									<div>
										<label for="equation-batch" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											Equation Batch
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Batch size for equation processing (1-32)
												</div>
											</div>
										</label>
										<input
											id="equation-batch"
											type="number"
											bind:value={$conversionOptions.equation_batch_size}
											placeholder="Auto"
											min="1"
											max="32"
											class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
										/>
									</div>
									<div>
										<label for="inlinemath-ratio" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											Inline Math Ratio
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Ratio threshold for assuming everything has math (0-1)
												</div>
											</div>
										</label>
										<input
											id="inlinemath-ratio"
											type="number"
											bind:value={$conversionOptions.inlinemath_min_ratio}
											placeholder="0.4"
											min="0"
											max="1"
											step="0.01"
											class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
										/>
									</div>
								</div>
							</div>

							<!-- Output Control -->
							<div class="mb-6">
								<h4 class="text-md font-medium text-gray-800 dark:text-gray-200 mb-3">Output Control</h4>
								<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
									<div>
										<label for="page-separator" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
											Page Separator
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Custom separator to use between pages
												</div>
											</div>
										</label>
										<input
											id="page-separator"
											type="text"
											bind:value={$conversionOptions.page_separator}
											placeholder="Default"
											class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
										/>
									</div>
									<div class="flex items-center">
										<input
											id="extract-images"
											type="checkbox"
											bind:checked={$conversionOptions.extract_images}
											class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-200 dark:border-gray-600"
										/>
										<label for="extract-images" class="flex items-center ml-2 text-sm text-gray-700 dark:text-gray-300">
											Extract Images
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Extract images from document
												</div>
											</div>
										</label>
									</div>
								</div>
							</div>

							<!-- LLM Processing -->
							{#if $conversionOptions.use_llm}
								<div class="mb-6">
									<h4 class="text-md font-medium text-gray-800 dark:text-gray-200 mb-3">LLM Processing</h4>
									<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
										<div>
											<label for="max-concurrency" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
												Max Concurrency
												<div class="relative group ml-1">
													<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
													<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
														Maximum concurrent LLM requests (1-20)
													</div>
												</div>
											</label>
											<input
												id="max-concurrency"
												type="number"
												bind:value={$conversionOptions.max_concurrency}
												placeholder="3"
												min="1"
												max="20"
												class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
											/>
										</div>
										<div>
											<label for="confidence-threshold" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
												Confidence Threshold
												<div class="relative group ml-1">
													<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
													<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
														Confidence threshold for relabeling (0-1)
													</div>
												</div>
											</label>
											<input
												id="confidence-threshold"
												type="number"
												bind:value={$conversionOptions.confidence_threshold}
												placeholder="0.7"
												min="0"
												max="1"
												step="0.01"
												class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
											/>
										</div>
									</div>
								</div>
							{/if}

							<!-- Debug Options -->
							<div>
								<h4 class="text-md font-medium text-gray-800 dark:text-gray-200 mb-3">Debug Options</h4>
								<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
									<div class="flex items-center">
										<input
											id="debug"
											type="checkbox"
											bind:checked={$conversionOptions.debug}
											class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-200 dark:border-gray-600"
										/>
										<label for="debug" class="flex items-center ml-2 text-sm text-gray-700 dark:text-gray-300">
											Debug Mode
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Enable debug mode for troubleshooting
												</div>
											</div>
										</label>
									</div>
									<div class="flex items-center">
										<input
											id="debug-layout"
											type="checkbox"
											bind:checked={$conversionOptions.debug_layout_images}
											class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-200 dark:border-gray-600"
										/>
										<label for="debug-layout" class="flex items-center ml-2 text-sm text-gray-700 dark:text-gray-300">
											Layout Images
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Save layout debug images
												</div>
											</div>
										</label>
									</div>
									<div class="flex items-center">
										<input
											id="debug-pdf"
											type="checkbox"
											bind:checked={$conversionOptions.debug_pdf_images}
											class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-200 dark:border-gray-600"
										/>
										<label for="debug-pdf" class="flex items-center ml-2 text-sm text-gray-700 dark:text-gray-300">
											PDF Images
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Save PDF debug images
												</div>
											</div>
										</label>
									</div>
									<div class="flex items-center">
										<input
											id="debug-json"
											type="checkbox"
											bind:checked={$conversionOptions.debug_json}
											class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-200 dark:border-gray-600"
										/>
										<label for="debug-json" class="flex items-center ml-2 text-sm text-gray-700 dark:text-gray-300">
											JSON Data
											<div class="relative group ml-1">
												<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
												<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
													Save debug JSON data
												</div>
											</div>
										</label>
									</div>
									{#if $conversionOptions.debug}
										<div class="md:col-span-2">
											<label for="debug-folder" class="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
												Debug Folder
												<div class="relative group ml-1">
													<Info class="w-3 h-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-help" />
													<div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-10">
														Folder to save debug data
													</div>
												</div>
											</label>
											<input
												id="debug-folder"
												type="text"
												bind:value={$conversionOptions.debug_data_folder}
												placeholder="debug_data"
												class="block w-full rounded-md border-gray-200 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
											/>
										</div>
									{/if}
								</div>
							</div>
						{/if}
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
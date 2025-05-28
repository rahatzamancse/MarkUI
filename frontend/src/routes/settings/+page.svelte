<script lang="ts">
	import { onMount } from 'svelte';
	import { 
		Save, 
		Moon, 
		Sun, 
		Key, 
		Server, 
		Brain,
		Eye,
		EyeOff,
		Check,
		AlertCircle,
		Info,
		TestTube,
		Loader2,
		RefreshCw
	} from 'lucide-svelte';
	import { 
		userSettings, 
		theme, 
		isDarkMode, 
		llmServices, 
		configuredLLMServices,
		ollamaModels,
		isLoading, 
		actions 
	} from '$lib/stores';
	import type { UserSettingsUpdate, LLMServiceInfo, LLMServiceTestRequest } from '$lib/types';

	let formData: UserSettingsUpdate = $state({
		theme: 'light',
		default_llm_service: '',
		gemini_api_key: '',
		openai_api_key: '',
		claude_api_key: '',
		ollama_base_url: 'http://localhost:11434',
		ollama_model: 'llama3.2:latest',
		openai_model: 'gpt-4o',
		openai_base_url: '',
		claude_model_name: 'claude-3-sonnet-20240229',
		vertex_project_id: '',
		default_output_format: 'markdown',
		default_use_llm: false,
		default_force_ocr: false,
		default_format_lines: false
	});

	let showApiKeys: Record<string, boolean> = $state({
		gemini: false,
		openai: false,
		claude: false
	});

	let saving = $state(false);
	let saveSuccess = $state(false);

	// Test connection state
	let testingServices: Record<string, boolean> = $state({});
	let testResults: Record<string, { success: boolean; message: string; response_time_ms?: number }> = $state({});

	// Ollama models state
	let loadingOllamaModels = $state(false);
	let ollamaModelsError: string | null = $state(null);

	// Reactive statement to update formData when userSettings changes
	$effect(() => {
		if ($userSettings) {
			formData = {
				theme: $theme,
				default_llm_service: $userSettings.default_llm_service || '',
				gemini_api_key: '',
				openai_api_key: '',
				claude_api_key: '',
				ollama_base_url: $userSettings.ollama_base_url || 'http://localhost:11434',
				ollama_model: $userSettings.ollama_model || 'llama3.2:latest',
				openai_model: $userSettings.openai_model || 'gpt-4o',
				openai_base_url: $userSettings.openai_base_url || '',
				claude_model_name: $userSettings.claude_model_name || 'claude-3-sonnet-20240229',
				vertex_project_id: $userSettings.vertex_project_id || '',
				default_output_format: $userSettings.default_output_format,
				default_use_llm: $userSettings.default_use_llm,
				default_force_ocr: $userSettings.default_force_ocr,
				default_format_lines: $userSettings.default_format_lines
			};
		}
	});

	// Handle theme changes immediately
	function handleThemeChange(newTheme: 'light' | 'dark') {
		theme.set(newTheme);
		formData.theme = newTheme;
	}

	onMount(() => {
		// Initial load is handled by the reactive statement above
		// No need to duplicate the logic here
	});

	async function saveSettings(event: SubmitEvent) {
		event.preventDefault();
		
		try {
			saving = true;
			
			// Only include non-empty API keys and exclude theme (handled locally)
			const updateData: UserSettingsUpdate = { ...formData };
			delete updateData.theme; // Remove theme from backend updates
			if (!updateData.gemini_api_key) delete updateData.gemini_api_key;
			if (!updateData.openai_api_key) delete updateData.openai_api_key;
			if (!updateData.claude_api_key) delete updateData.claude_api_key;

			await actions.updateSettings(updateData);
			
			// Reload configured services after saving
			await actions.loadConfiguredLLMServices();
			
			saveSuccess = true;
			setTimeout(() => {
				saveSuccess = false;
			}, 3000);
		} catch (error) {
			actions.setError(`Failed to save settings: ${error}`);
		} finally {
			saving = false;
		}
	}

	function toggleApiKeyVisibility(service: string) {
		showApiKeys[service] = !showApiKeys[service];
	}

	function getServiceInfo(serviceName: string): LLMServiceInfo | undefined {
		return $llmServices.find(s => s.name === serviceName);
	}

	async function testServiceConnection(serviceName: string) {
		testingServices[serviceName] = true;
		delete testResults[serviceName];
		
		try {
			const testRequest: LLMServiceTestRequest = {
				service_name: serviceName,
				// Include current form values for testing
				gemini_api_key: formData.gemini_api_key || undefined,
				openai_api_key: formData.openai_api_key || undefined,
				claude_api_key: formData.claude_api_key || undefined,
				ollama_base_url: formData.ollama_base_url || undefined,
				ollama_model: formData.ollama_model || undefined,
				openai_model: formData.openai_model || undefined,
				openai_base_url: formData.openai_base_url || undefined,
				claude_model_name: formData.claude_model_name || undefined,
				vertex_project_id: formData.vertex_project_id || undefined
			};

			const result = await actions.testLLMServiceConnection(testRequest);
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

	// Reactive statements
	let selectedServiceInfo = $derived(formData.default_llm_service ? getServiceInfo(formData.default_llm_service) : null);

	async function fetchOllamaModels() {
		if (!formData.ollama_base_url) {
			ollamaModels.set([]);
			return;
		}

		try {
			loadingOllamaModels = true;
			ollamaModelsError = null;
			console.log('Fetching Ollama models from:', formData.ollama_base_url);
			await actions.loadOllamaModels(formData.ollama_base_url);
			
			// Force reactivity by accessing the store value
			const currentModels = $ollamaModels;
			console.log('Loaded models:', currentModels);
			console.log('Current formData.ollama_model:', formData.ollama_model);
			
			// Auto-select first model if needed
			if (currentModels.length > 0 && (!formData.ollama_model || !currentModels.includes(formData.ollama_model))) {
				console.log('Auto-selecting first model in function:', currentModels[0]);
				formData.ollama_model = currentModels[0];
			}
		} catch (error) {
			ollamaModelsError = `Failed to fetch models: ${error}`;
			console.error('Error fetching Ollama models:', error);
		} finally {
			loadingOllamaModels = false;
		}
	}
</script>

<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
	<!-- Header -->
	<div class="mb-8">
		<h1 class="text-3xl font-bold text-gray-900 dark:text-white">Settings</h1>
		<p class="mt-2 text-gray-600 dark:text-gray-400">
			Configure your preferences, API keys, and default conversion options
		</p>
	</div>

	<form onsubmit={saveSettings} class="space-y-8">
		<!-- Theme Settings -->
		<div class="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
			<h2 class="text-lg font-medium text-gray-900 dark:text-white mb-4 flex items-center">
				{#if $isDarkMode}
					<Moon class="w-5 h-5 mr-2" />
				{:else}
					<Sun class="w-5 h-5 mr-2" />
				{/if}
				Appearance
			</h2>
			
			<div class="space-y-4">
				<div>
					<label class="text-sm font-medium text-gray-700 dark:text-gray-300">Theme</label>
					<div class="mt-2 space-y-2">
						<label class="flex items-center">
							<input
								type="radio"
								checked={$theme === 'light'}
								value="light"
								onchange={() => handleThemeChange('light')}
								class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-600"
							/>
							<Sun class="w-4 h-4 ml-3 mr-2 text-yellow-500" />
							<span class="text-sm text-gray-700 dark:text-gray-300">Light</span>
						</label>
						<label class="flex items-center">
							<input
								type="radio"
								checked={$theme === 'dark'}
								value="dark"
								onchange={() => handleThemeChange('dark')}
								class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-600"
							/>
							<Moon class="w-4 h-4 ml-3 mr-2 text-blue-500" />
							<span class="text-sm text-gray-700 dark:text-gray-300">Dark</span>
						</label>
					</div>
				</div>
			</div>
		</div>

		<!-- LLM Services -->
		<div class="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
			<h2 class="text-lg font-medium text-gray-900 dark:text-white mb-4 flex items-center">
				<Brain class="w-5 h-5 mr-2 text-purple-500" />
				LLM Services
			</h2>

			<div class="space-y-6">
				<!-- Default LLM Service -->
				<div>
					<label for="default-llm" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
						Default LLM Service
					</label>
					<select
						id="default-llm"
						bind:value={formData.default_llm_service}
						class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500"
					>
						<option value="">None</option>
						{#each $configuredLLMServices as service}
							<option value={service.name}>{service.display_name}</option>
						{/each}
					</select>
					{#if selectedServiceInfo}
						<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
							{selectedServiceInfo.description}
						</p>
					{/if}
					{#if $configuredLLMServices.length === 0}
						<p class="mt-1 text-xs text-yellow-600 dark:text-yellow-400">
							No LLM services configured. Configure API keys or local services below to enable LLM functionality.
						</p>
					{/if}
				</div>

				<!-- API Keys -->
				<div class="space-y-4">
					<h3 class="text-md font-medium text-gray-900 dark:text-white flex items-center">
						<Key class="w-4 h-4 mr-2" />
						API Keys
					</h3>

					<!-- Gemini API Key -->
					<div>
						<div class="flex items-center justify-between">
							<label for="gemini-key" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
								Google Gemini API Key
								{#if $userSettings?.has_gemini_api_key}
									<span class="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400">
										<Check class="w-3 h-3 mr-1" />
										Configured
									</span>
								{/if}
							</label>
							<button
								type="button"
								onclick={() => testServiceConnection('marker.services.gemini.GoogleGeminiService')}
								disabled={testingServices['marker.services.gemini.GoogleGeminiService'] || (!formData.gemini_api_key && !$userSettings?.has_gemini_api_key)}
								class="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30"
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
						<div class="mt-1 relative">
							<input
								id="gemini-key"
								type={showApiKeys.gemini ? 'text' : 'password'}
								bind:value={formData.gemini_api_key}
								placeholder={$userSettings?.has_gemini_api_key ? '••••••••••••••••' : 'Enter your Gemini API key'}
								class="block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 pr-10"
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
									{#if testResults['marker.services.gemini.GoogleGeminiService'].response_time_ms}
										<span class="ml-2 text-xs text-gray-500 dark:text-gray-400">
											({testResults['marker.services.gemini.GoogleGeminiService'].response_time_ms}ms)
										</span>
									{/if}
								</div>
							</div>
						{/if}
					</div>

					<!-- OpenAI API Key -->
					<div>
						<div class="flex items-center justify-between">
							<label for="openai-key" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
								OpenAI API Key
								{#if $userSettings?.has_openai_api_key}
									<span class="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400">
										<Check class="w-3 h-3 mr-1" />
										Configured
									</span>
								{/if}
							</label>
							<button
								type="button"
								onclick={() => testServiceConnection('marker.services.openai.OpenAIService')}
								disabled={testingServices['marker.services.openai.OpenAIService'] || (!formData.openai_api_key && !$userSettings?.has_openai_api_key)}
								class="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30"
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
						<div class="mt-1 relative">
							<input
								id="openai-key"
								type={showApiKeys.openai ? 'text' : 'password'}
								bind:value={formData.openai_api_key}
								placeholder={$userSettings?.has_openai_api_key ? '••••••••••••••••' : 'Enter your OpenAI API key'}
								class="block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 pr-10"
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
									{#if testResults['marker.services.openai.OpenAIService'].response_time_ms}
										<span class="ml-2 text-xs text-gray-500 dark:text-gray-400">
											({testResults['marker.services.openai.OpenAIService'].response_time_ms}ms)
										</span>
									{/if}
								</div>
							</div>
						{/if}
						<div class="mt-2 grid grid-cols-1 md:grid-cols-2 gap-4">
							<div>
								<label for="openai-model" class="block text-xs font-medium text-gray-700 dark:text-gray-300">
									Default Model
								</label>
								<input
									id="openai-model"
									type="text"
									bind:value={formData.openai_model}
									placeholder="gpt-4o"
									class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
								/>
							</div>
							<div>
								<label for="openai-base-url" class="block text-xs font-medium text-gray-700 dark:text-gray-300">
									Base URL (optional)
								</label>
								<input
									id="openai-base-url"
									type="text"
									bind:value={formData.openai_base_url}
									placeholder="https://api.openai.com/v1"
									class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
								/>
							</div>
						</div>
					</div>

					<!-- Claude API Key -->
					<div>
						<div class="flex items-center justify-between">
							<label for="claude-key" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
								Anthropic Claude API Key
								{#if $userSettings?.has_claude_api_key}
									<span class="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400">
										<Check class="w-3 h-3 mr-1" />
										Configured
									</span>
								{/if}
							</label>
							<button
								type="button"
								onclick={() => testServiceConnection('marker.services.claude.ClaudeService')}
								disabled={testingServices['marker.services.claude.ClaudeService'] || (!formData.claude_api_key && !$userSettings?.has_claude_api_key)}
								class="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30"
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
						<div class="mt-1 relative">
							<input
								id="claude-key"
								type={showApiKeys.claude ? 'text' : 'password'}
								bind:value={formData.claude_api_key}
								placeholder={$userSettings?.has_claude_api_key ? '••••••••••••••••' : 'Enter your Claude API key'}
								class="block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 pr-10"
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
									{#if testResults['marker.services.claude.ClaudeService'].response_time_ms}
										<span class="ml-2 text-xs text-gray-500 dark:text-gray-400">
											({testResults['marker.services.claude.ClaudeService'].response_time_ms}ms)
										</span>
									{/if}
								</div>
							</div>
						{/if}
						<div class="mt-2">
							<label for="claude-model" class="block text-xs font-medium text-gray-700 dark:text-gray-300">
								Default Model
							</label>
							<input
								id="claude-model"
								type="text"
								bind:value={formData.claude_model_name}
								placeholder="claude-3-sonnet-20240229"
								class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
							/>
						</div>
					</div>
				</div>

				<!-- Ollama Settings -->
				<div class="border-t border-gray-200 dark:border-gray-700 pt-4">
					<div class="flex items-center justify-between mb-4">
						<h3 class="text-md font-medium text-gray-900 dark:text-white flex items-center">
							<Server class="w-4 h-4 mr-2" />
							Ollama (Local LLM)
						</h3>
						<button
							type="button"
							onclick={() => testServiceConnection('marker.services.ollama.OllamaService')}
							disabled={testingServices['marker.services.ollama.OllamaService']}
							class="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30"
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
					{#if testResults['marker.services.ollama.OllamaService']}
						<div class="mb-4 p-2 rounded-md {testResults['marker.services.ollama.OllamaService'].success ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'}">
							<div class="flex items-center">
								{#if testResults['marker.services.ollama.OllamaService'].success}
									<Check class="w-4 h-4 text-green-600 dark:text-green-400 mr-2" />
								{:else}
									<AlertCircle class="w-4 h-4 text-red-600 dark:text-red-400 mr-2" />
								{/if}
								<span class="text-sm {testResults['marker.services.ollama.OllamaService'].success ? 'text-green-800 dark:text-green-300' : 'text-red-800 dark:text-red-300'}">
									{testResults['marker.services.ollama.OllamaService'].message}
								</span>
								{#if testResults['marker.services.ollama.OllamaService'].response_time_ms}
									<span class="ml-2 text-xs text-gray-500 dark:text-gray-400">
										({testResults['marker.services.ollama.OllamaService'].response_time_ms}ms)
									</span>
								{/if}
							</div>
						</div>
					{/if}
					<div class="space-y-4">
						<div class="flex gap-4 items-end">
							<div class="flex-1">
								<label for="ollama-url" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
									Base URL
								</label>
								<input
									id="ollama-url"
									type="text"
									bind:value={formData.ollama_base_url}
									placeholder="http://localhost:11434"
									class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500"
								/>
							</div>
							<button
								type="button"
								onclick={fetchOllamaModels}
								disabled={loadingOllamaModels || !formData.ollama_base_url}
								title="Load Models"
								class="w-10 h-10 border border-gray-300 dark:border-gray-600 shadow-sm text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
							>
								{#if loadingOllamaModels}
									<Loader2 class="w-4 h-4 animate-spin" />
								{:else}
									<RefreshCw class="w-4 h-4" />
								{/if}
							</button>
						</div>
						<div>
							<label for="ollama-model" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
								Default Model
							</label>
							{#if $ollamaModels.length > 0}
								<select
									id="ollama-model"
									bind:value={formData.ollama_model}
									class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500"
								>
									{#each $ollamaModels as model}
										<option value={model}>{model}</option>
									{/each}
								</select>
							{:else}
								<input
									id="ollama-model"
									type="text"
									bind:value={formData.ollama_model}
									placeholder="Use refresh button to fetch available models"
									disabled={true}
									class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
								/>
							{/if}
						</div>
					</div>
					{#if ollamaModelsError}
						<p class="mt-2 text-xs text-red-600 dark:text-red-400">
							{ollamaModelsError}
						</p>
					{:else if !formData.ollama_base_url}
						<p class="mt-2 text-xs text-gray-500 dark:text-gray-400">
							Enter a base URL first, then use refresh button
						</p>
					{:else if $ollamaModels.length === 0 && !loadingOllamaModels}
						<p class="mt-2 text-xs text-gray-500 dark:text-gray-400">
							Use refresh button to fetch available models
						</p>
					{/if}
				</div>

				<!-- Vertex AI Settings -->
				<div class="border-t border-gray-200 dark:border-gray-700 pt-4">
					<div class="flex items-center justify-between mb-4">
						<h3 class="text-md font-medium text-gray-900 dark:text-white flex items-center">
							<Server class="w-4 h-4 mr-2" />
							Google Vertex AI
						</h3>
						<button
							type="button"
							onclick={() => testServiceConnection('marker.services.vertex.GoogleVertexService')}
							disabled={testingServices['marker.services.vertex.GoogleVertexService'] || !formData.vertex_project_id}
							class="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30"
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
					{#if testResults['marker.services.vertex.GoogleVertexService']}
						<div class="mb-4 p-2 rounded-md {testResults['marker.services.vertex.GoogleVertexService'].success ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'}">
							<div class="flex items-center">
								{#if testResults['marker.services.vertex.GoogleVertexService'].success}
									<Check class="w-4 h-4 text-green-600 dark:text-green-400 mr-2" />
								{:else}
									<AlertCircle class="w-4 h-4 text-red-600 dark:text-red-400 mr-2" />
								{/if}
								<span class="text-sm {testResults['marker.services.vertex.GoogleVertexService'].success ? 'text-green-800 dark:text-green-300' : 'text-red-800 dark:text-red-300'}">
									{testResults['marker.services.vertex.GoogleVertexService'].message}
								</span>
								{#if testResults['marker.services.vertex.GoogleVertexService'].response_time_ms}
									<span class="ml-2 text-xs text-gray-500 dark:text-gray-400">
										({testResults['marker.services.vertex.GoogleVertexService'].response_time_ms}ms)
									</span>
								{/if}
							</div>
						</div>
					{/if}
					<div>
						<label for="vertex-project" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
							Project ID
						</label>
						<input
							id="vertex-project"
							type="text"
							bind:value={formData.vertex_project_id}
							placeholder="your-gcp-project-id"
							class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500"
						/>
						<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
							Requires Google Cloud authentication to be configured on the server
						</p>
					</div>
				</div>
			</div>
		</div>

		<!-- Default Conversion Settings -->
		<div class="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
			<h2 class="text-lg font-medium text-gray-900 dark:text-white mb-4 flex items-center">
				<Info class="w-5 h-5 mr-2 text-blue-500" />
				Default Conversion Settings
			</h2>

			<div class="space-y-4">
				<div>
					<label for="default-format" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
						Default Output Format
					</label>
					<select
						id="default-format"
						bind:value={formData.default_output_format}
						class="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 shadow-sm focus:border-blue-500 focus:ring-blue-500"
					>
						<option value="markdown">Markdown</option>
						<option value="json">JSON</option>
						<option value="html">HTML</option>
					</select>
				</div>

				<div class="space-y-3">
					<label class="flex items-center">
						<input
							type="checkbox"
							bind:checked={formData.default_use_llm}
							class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-600"
						/>
						<span class="ml-3 text-sm text-gray-700 dark:text-gray-300">Use LLM by default</span>
					</label>

					<label class="flex items-center">
						<input
							type="checkbox"
							bind:checked={formData.default_force_ocr}
							class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-600"
						/>
						<span class="ml-3 text-sm text-gray-700 dark:text-gray-300">Force OCR by default</span>
					</label>

					<label class="flex items-center">
						<input
							type="checkbox"
							bind:checked={formData.default_format_lines}
							class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-600"
						/>
						<span class="ml-3 text-sm text-gray-700 dark:text-gray-300">Format lines by default</span>
					</label>
				</div>
			</div>
		</div>

		<!-- Save Button -->
		<div class="flex items-center justify-between">
			<div class="flex items-center">
				{#if saveSuccess}
					<div class="flex items-center text-green-600 dark:text-green-400">
						<Check class="w-4 h-4 mr-2" />
						<span class="text-sm">Settings saved successfully!</span>
					</div>
				{/if}
			</div>
			
			<button
				type="submit"
				disabled={saving || $isLoading}
				class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
			>
				{#if saving}
					<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
					Saving...
				{:else}
					<Save class="w-4 h-4 mr-2" />
					Save Settings
				{/if}
			</button>
		</div>
	</form>
</div> 
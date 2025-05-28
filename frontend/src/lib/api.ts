import type {
	PDFUploadResponse,
	PDFListResponse,
	PDFDocument,
	ConversionJobCreate,
	ConversionJob,
	ConversionJobListResponse,
	ConversionResult,
	UserSettings,
	UserSettingsUpdate,
	LLMServicesResponse,
	LLMServiceTestRequest,
	LLMServiceTestResponse
} from './types';

const API_BASE_URL = 'http://localhost:8000/api/v1';

class APIError extends Error {
	constructor(
		message: string,
		public status: number,
		public response?: Response
	) {
		super(message);
		this.name = 'APIError';
	}
}

async function handleResponse<T>(response: Response): Promise<T> {
	if (!response.ok) {
		const errorText = await response.text();
		let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
		
		try {
			const errorData = JSON.parse(errorText);
			errorMessage = errorData.detail || errorMessage;
		} catch {
			// If not JSON, use the text as is
			errorMessage = errorText || errorMessage;
		}
		
		throw new APIError(errorMessage, response.status, response);
	}
	
	return response.json();
}

export class MarkUIAPI {
	// Health Check
	static async healthCheck(): Promise<{ status: string; app_name: string; version: string }> {
		const response = await fetch(`${API_BASE_URL}/health`);
		return handleResponse(response);
	}

	// PDF Management
	static async uploadPDF(file: File): Promise<PDFUploadResponse> {
		const formData = new FormData();
		formData.append('file', file);

		const response = await fetch(`${API_BASE_URL}/pdf/upload`, {
			method: 'POST',
			body: formData
		});

		return handleResponse(response);
	}

	static async listPDFs(page = 1, perPage = 10): Promise<PDFListResponse> {
		const response = await fetch(`${API_BASE_URL}/pdf/list?page=${page}&per_page=${perPage}`);
		return handleResponse(response);
	}

	static async getPDF(pdfId: number): Promise<PDFDocument> {
		const response = await fetch(`${API_BASE_URL}/pdf/${pdfId}`);
		return handleResponse(response);
	}

	static async deletePDF(pdfId: number): Promise<{ message: string }> {
		const response = await fetch(`${API_BASE_URL}/pdf/${pdfId}`, {
			method: 'DELETE'
		});
		return handleResponse(response);
	}

	static async getPDFPreview(pdfId: number): Promise<{ preview_images: string[] }> {
		const response = await fetch(`${API_BASE_URL}/pdf/${pdfId}/preview`);
		const result = await handleResponse<{ preview_images: string[] }>(response);
		
		// Convert relative paths to absolute URLs
		result.preview_images = result.preview_images.map(path => {
			if (path.startsWith('/')) {
				return `http://localhost:8000${path}`;
			}
			return path;
		});
		
		return result;
	}

	// Conversion Jobs
	static async createConversionJob(jobData: ConversionJobCreate): Promise<ConversionJob> {
		const response = await fetch(`${API_BASE_URL}/conversion/jobs`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(jobData)
		});

		return handleResponse(response);
	}

	static async listConversionJobs(
		page = 1,
		perPage = 10,
		status?: string
	): Promise<ConversionJobListResponse> {
		const params = new URLSearchParams({
			page: page.toString(),
			per_page: perPage.toString()
		});

		if (status) {
			params.append('status', status);
		}

		const response = await fetch(`${API_BASE_URL}/conversion/jobs?${params}`);
		return handleResponse(response);
	}

	static async getConversionJob(jobId: number): Promise<ConversionJob> {
		const response = await fetch(`${API_BASE_URL}/conversion/jobs/${jobId}`);
		return handleResponse(response);
	}

	static async getConversionResult(jobId: number): Promise<ConversionResult> {
		const response = await fetch(`${API_BASE_URL}/conversion/jobs/${jobId}/result`);
		return handleResponse(response);
	}

	static async downloadConversionResult(jobId: number): Promise<Blob> {
		const response = await fetch(`${API_BASE_URL}/conversion/jobs/${jobId}/download`);
		
		if (!response.ok) {
			throw new APIError(`Download failed: ${response.statusText}`, response.status, response);
		}
		
		return response.blob();
	}

	static async deleteConversionJob(jobId: number): Promise<{ message: string }> {
		const response = await fetch(`${API_BASE_URL}/conversion/jobs/${jobId}`, {
			method: 'DELETE'
		});
		return handleResponse(response);
	}

	// Settings
	static async getUserSettings(): Promise<UserSettings> {
		const response = await fetch(`${API_BASE_URL}/settings/user`);
		return handleResponse(response);
	}

	static async updateUserSettings(settings: UserSettingsUpdate): Promise<UserSettings> {
		const response = await fetch(`${API_BASE_URL}/settings/user`, {
			method: 'PUT',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(settings)
		});

		return handleResponse(response);
	}

	static async getLLMServices(): Promise<LLMServicesResponse> {
		const response = await fetch(`${API_BASE_URL}/settings/llm-services`);
		return handleResponse(response);
	}

	static async getConfiguredLLMServices(): Promise<LLMServicesResponse> {
		const response = await fetch(`${API_BASE_URL}/settings/llm-services/configured`);
		return handleResponse(response);
	}

	static async testLLMServiceConnection(testRequest: LLMServiceTestRequest): Promise<LLMServiceTestResponse> {
		const response = await fetch(`${API_BASE_URL}/settings/llm-services/test`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(testRequest)
		});
		return handleResponse(response);
	}

	static async getOllamaModels(baseUrl: string = 'http://localhost:11434'): Promise<{ models: string[] }> {
		const params = new URLSearchParams({ base_url: baseUrl });
		const response = await fetch(`${API_BASE_URL}/settings/ollama/models?${params}`);
		return handleResponse(response);
	}

	static async getConversionDefaults(): Promise<{
		output_format: string;
		use_llm: boolean;
		force_ocr: boolean;
		format_lines: boolean;
		llm_service: string | null;
		disable_image_extraction: boolean;
		strip_existing_ocr: boolean;
		redo_inline_math: boolean;
		paginate_output: boolean;
	}> {
		const response = await fetch(`${API_BASE_URL}/conversion/defaults`);
		return handleResponse(response);
	}
}

// Utility functions for file handling
export function formatFileSize(bytes: number): string {
	if (bytes === 0) return '0 Bytes';
	
	const k = 1024;
	const sizes = ['Bytes', 'KB', 'MB', 'GB'];
	const i = Math.floor(Math.log(bytes) / Math.log(k));
	
	return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function formatDate(dateString: string): string {
	return new Date(dateString).toLocaleString();
}

export { APIError }; 
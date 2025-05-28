import type {
	PDFUploadResponse,
	PDFDocument,
	ConversionJobCreate,
	ConversionJob,
	ConversionJobListResponse,
	ConversionResult,
	LLMServiceTestRequest,
	LLMServiceTestResponse
} from './types';

const API_BASE_URL = 'http://localhost:8000/api/v1';

async function handleResponse<T = any>(response: Response): Promise<T> {
	if (!response.ok) {
		let errorMessage: string;
		try {
			const errorData = await response.json();
			errorMessage = errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`;
		} catch {
			errorMessage = `HTTP ${response.status}: ${response.statusText}`;
		}
		throw new Error(errorMessage);
	}

	const contentType = response.headers.get('content-type');
	if (contentType && contentType.includes('application/json')) {
		return response.json();
	}
	
	// For blob responses (downloads)
	return response.blob() as unknown as T;
}

export class MarkUIAPI {
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

	// Conversion Management
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

	static async getConversionJob(jobId: number): Promise<ConversionJob> {
		const response = await fetch(`${API_BASE_URL}/conversion/jobs/${jobId}`);
		return handleResponse(response);
	}

	static async getConversionJobs(): Promise<ConversionJobListResponse> {
		const response = await fetch(`${API_BASE_URL}/conversion/jobs`);
		return handleResponse(response);
	}

	static async getConversionResult(jobId: number): Promise<ConversionResult> {
		const response = await fetch(`${API_BASE_URL}/conversion/jobs/${jobId}/result`);
		const result = await handleResponse<ConversionResult>(response);
		
		// Convert relative image paths to absolute URLs
		if (result.images) {
			result.images = result.images.map(path => {
				if (path.startsWith('/')) {
					return `http://localhost:8000${path}`;
				}
				return path;
			});
		}
		
		return result;
	}

	static async downloadConversionResult(jobId: number): Promise<Blob> {
		const response = await fetch(`${API_BASE_URL}/conversion/jobs/${jobId}/download`);
		return handleResponse<Blob>(response);
	}

	// LLM Service Testing
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
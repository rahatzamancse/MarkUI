// API Types based on backend schemas

export interface PDFDocument {
	id: number;
	filename: string;
	original_filename: string;
	file_size: number;
	total_pages: number;
	metadata?: Record<string, any>;
	created_at: string;
}

export interface PDFUploadResponse extends PDFDocument {
	preview_images: string[];
}

export enum ConversionStatus {
	PENDING = 'pending',
	PROCESSING = 'processing',
	COMPLETED = 'completed',
	FAILED = 'failed'
}

export enum OutputFormat {
	MARKDOWN = 'markdown',
	JSON = 'json',
	HTML = 'html'
}

export interface ConversionJobCreate {
	pdf_document_id: number;
	output_format: OutputFormat;
	selected_pages?: number[];
	use_llm: boolean;
	force_ocr: boolean;
	strip_existing_ocr: boolean;
	format_lines: boolean;
	redo_inline_math: boolean;
	disable_image_extraction: boolean;
	paginate_output: boolean;
	llm_service?: string;
	llm_model?: string;
}

export interface ConversionJob {
	id: number;
	pdf_document_id: number;
	status: ConversionStatus;
	output_format: OutputFormat;
	selected_pages?: number[];
	progress: number;
	error_message?: string;
	created_at: string;
	started_at?: string;
	completed_at?: string;
	use_llm: boolean;
	force_ocr: boolean;
	strip_existing_ocr: boolean;
	format_lines: boolean;
	redo_inline_math: boolean;
	disable_image_extraction: boolean;
	paginate_output: boolean;
	llm_service?: string;
	llm_model?: string;
}

export interface ConversionJobListResponse {
	jobs: ConversionJob[];
	total: number;
	page: number;
	per_page: number;
	pages: number;
}

export interface ConversionResult {
	job: ConversionJob;
	content?: string;
	images?: string[];
}

export interface LLMServiceTestRequest {
	service_name: string;
	gemini_api_key?: string;
	openai_api_key?: string;
	claude_api_key?: string;
	ollama_base_url?: string;
	ollama_model?: string;
	openai_model?: string;
	openai_base_url?: string;
	claude_model_name?: string;
	vertex_project_id?: string;
}

export interface LLMServiceTestResponse {
	success: boolean;
	message: string;
	response_time_ms?: number;
}

// UI State Types
export interface AppState {
	theme: 'light' | 'dark';
	currentPDF?: PDFDocument;
	selectedPages: Set<number>;
	conversionOptions: ConversionJobCreate;
	isLoading: boolean;
	error?: string;
}

export interface PagePreview {
	pageNumber: number;
	imageUrl: string;
	selected: boolean;
} 
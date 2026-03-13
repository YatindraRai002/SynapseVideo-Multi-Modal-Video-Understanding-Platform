export interface SearchResult {
    video_id: string;
    video_title: string;
    timestamp: number;
    end_time: number | null;
    transcript_snippet: string | null;
    frame_path: string | null;
    frame_caption: string | null;
    score: number;
    match_type: "transcript" | "frame" | "both";
}

export interface SearchResponse {
    query: string;
    results: SearchResult[];
    generated_answer?: string | null;
    total_results: number;
    latency_ms: number;
}

export interface Video {
    id: string;
    title: string;
    source_url: string | null;
    file_path: string | null;
    duration_seconds: number | null;
    status: string;
    processing_progress: number;
    created_at: string;
}

export interface VideoListResponse {
    videos: Video[];
    total: number;
}

export interface TranslateRequest {
    text: string;
    source_lang: string;
    target_lang: string;
}

export interface TranslateResponse {
    original_text: string;
    translated_text: string;
    source_lang: string;
    target_lang: string;
}

import { SearchResponse, VideoListResponse, Video, TranslateResponse } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8888/api/v1";
export const BACKEND_BASE = API_BASE.replace(/\/api\/v1\/?$/, "") || "http://localhost:8888";

// Search status (diagnostic: Qdrant + video statuses)
export async function getSearchStatus(): Promise<{
    qdrant_connected: boolean;
    transcript_embeddings: number;
    frame_embeddings: number;
    videos: { id: string; title: string; status: string; processing_progress: number }[];
    hint: string;
}> {
    const response = await fetch(`${API_BASE}/search/status`);
    if (!response.ok) throw new Error("Failed to get status");
    return response.json();
}

// Search videos
export async function searchVideos(
    query: string,
    searchType: string = "hybrid",
    limit: number = 20
): Promise<SearchResponse> {
    const params = new URLSearchParams({
        q: query,
        search_type: searchType,
        limit: limit.toString(),
    });

    const response = await fetch(`${API_BASE}/search?${params}`);

    if (!response.ok) {
        throw new Error("Search failed");
    }

    return response.json();
}

// Get all videos
export async function getVideos(skip: number = 0, limit: number = 20): Promise<VideoListResponse> {
    const params = new URLSearchParams({
        skip: skip.toString(),
        limit: limit.toString(),
    });

    const response = await fetch(`${API_BASE}/videos?${params}`);

    if (!response.ok) {
        throw new Error("Failed to fetch videos");
    }

    return response.json();
}

// Get single video
export async function getVideo(videoId: string): Promise<Video> {
    const response = await fetch(`${API_BASE}/videos/${videoId}`);

    if (!response.ok) {
        throw new Error("Video not found");
    }

    return response.json();
}

// Upload video
export async function uploadVideo(
    file: File,
    title?: string,
    onProgress?: (progress: number) => void
): Promise<Video> {
    return new Promise((resolve, reject) => {
        const formData = new FormData();
        formData.append("file", file);
        if (title) {
            formData.append("title", title);
        }

        const xhr = new XMLHttpRequest();

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable && onProgress) {
                const progress = (e.loaded / e.total) * 100;
                onProgress(progress);
            }
        };

        xhr.onload = () => {
            if (xhr.status === 200) {
                resolve(JSON.parse(xhr.responseText));
            } else {
                reject(new Error("Upload failed"));
            }
        };

        xhr.onerror = () => reject(new Error("Upload failed"));

        xhr.open("POST", `${API_BASE}/videos/upload`);
        xhr.send(formData);
    });
}

// Upload video from URL (YouTube, Vimeo, etc.)
export async function uploadVideoFromUrl(url: string, title?: string): Promise<Video> {
    const response = await fetch(`${API_BASE}/videos/url`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ url, title }),
    });

    if (!response.ok) {
        throw new Error("Failed to submit URL");
    }

    return response.json();
}

// Voice to text
export async function voiceToText(audioBlob: Blob): Promise<string> {
    const formData = new FormData();
    formData.append("audio", audioBlob, "voice_query.webm");

    const response = await fetch(`${API_BASE}/asr/voice-to-text`, {
        method: "POST",
        body: formData,
    });

    if (!response.ok) {
        throw new Error("Voice recognition failed");
    }

    const data = await response.json();
    return data.text;
}

// Translate text
export async function translateText(
    text: string,
    sourceLang: string = "en",
    targetLang: string = "hi"
): Promise<TranslateResponse> {
    const response = await fetch(`${API_BASE}/translate/translate`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            text,
            source_lang: sourceLang,
            target_lang: targetLang,
        }),
    });

    if (!response.ok) {
        throw new Error("Translation failed");
    }

    return response.json();
}

// Retry processing for a failed video
export async function retryVideo(videoId: string): Promise<Video> {
    const response = await fetch(`${API_BASE}/videos/${videoId}/retry`, { method: "POST" });
    if (!response.ok) throw new Error("Retry failed");
    return response.json();
}

// Get video processing status
export async function getVideoStatus(videoId: string): Promise<{
    id: string;
    status: string;
    progress: number;
    error_message: string | null;
}> {
    const response = await fetch(`${API_BASE}/videos/${videoId}/status`);

    if (!response.ok) {
        throw new Error("Failed to get status");
    }

    return response.json();
}

// Format timestamp
export function formatTimestamp(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
}

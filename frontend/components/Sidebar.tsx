"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Video, Plus, Settings, User, PlayCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import UploadModal from "./UploadModal";
import { Video as VideoType } from "@/lib/types";
import { API_BASE } from "@/lib/api";

export default function Sidebar() {
    const [isUploadOpen, setIsUploadOpen] = useState(false);
    const [videos, setVideos] = useState<VideoType[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchVideos = async () => {
        try {
            const res = await fetch(`${API_BASE}/videos/?limit=20`);
            if (res.ok) {
                const data = await res.json();
                setVideos(data.videos);
            }
        } catch (error) {
            console.error("Failed to fetch videos:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchVideos();
    }, []);

    const handleUploadSuccess = () => {
        fetchVideos(); // Refresh list
    };

    return (
        <>
            <div className="w-64 bg-sidebar-bg border-r border-white/10 flex flex-col h-full bg-[#0B0F17] text-white">
                {/* Branding */}
                <div className="p-4 flex items-center gap-2 border-b border-white/10">
                    <div className="w-8 h-8 bg-gradient-to-tr from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center">
                        <Video className="w-5 h-5 text-white" />
                    </div>
                    <span className="font-bold text-lg tracking-tight">SynapseVideo</span>
                </div>

                {/* Primary Action */}
                <div className="p-4">
                    <Button
                        className="w-full justify-start gap-2 bg-indigo-600 hover:bg-indigo-700 text-white border-none shadow-lg shadow-indigo-500/20"
                        onClick={() => setIsUploadOpen(true)}
                    >
                        <Plus className="w-4 h-4" />
                        Upload Video
                    </Button>
                </div>

                {/* Navigation / Library */}
                <div className="flex-1 overflow-y-auto px-2">
                    <div className="flex items-center justify-between mb-2 px-2">
                        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Video Library</span>
                        {!loading && videos.length > 0 && (
                            <span className="text-xs text-gray-500">
                                {videos.filter((v) => v.status === "ready").length}/{videos.length} ready
                            </span>
                        )}
                    </div>
                    <div className="space-y-1">
                        {loading ? (
                            <div className="px-2 text-sm text-gray-500 flex items-center gap-2">
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Loading...
                            </div>
                        ) : videos.length === 0 ? (
                            <div className="px-2 text-sm text-gray-500 italic">No videos found. Upload one!</div>
                        ) : (
                            videos.map((video) => (
                                <Link key={video.id} href={`/videos/${video.id}`}>
                                    <Button
                                        variant="ghost"
                                        className="w-full justify-start text-sm text-gray-400 hover:text-white hover:bg-white/5 px-2"
                                        title={`${video.title} (${video.status})`}
                                    >
                                        <div className="flex items-center gap-2 overflow-hidden w-full">
                                            <PlayCircle className="w-4 h-4 shrink-0" />
                                            <span className="truncate">{video.title}</span>
                                        </div>
                                    </Button>
                                </Link>
                            ))
                        )}
                    </div>
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-white/10">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-gray-700 to-gray-600 flex items-center justify-center border border-white/10">
                            <User className="w-4 h-4" />
                        </div>
                        <div className="flex-1 overflow-hidden">
                            <div className="text-sm font-medium truncate">User</div>
                            <div className="text-xs text-gray-500">Free Plan</div>
                        </div>
                        <Settings className="w-4 h-4 text-gray-400 cursor-pointer hover:text-white transition-colors" />
                    </div>
                </div>
            </div>

            {/* Upload Modal */}
            {isUploadOpen && (
                <UploadModal
                    onClose={() => setIsUploadOpen(false)}
                    onUploadSuccess={handleUploadSuccess}
                />
            )}
        </>
    );
}

"use client";

import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import SearchBar from "@/components/SearchBar";
import SearchResults from "@/components/SearchResults";
import { SearchResult } from "@/lib/types";
import { API_BASE } from "@/lib/api";

export default function Home() {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [generatedAnswer, setGeneratedAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (query: string, searchType: string) => {
    setLoading(true);
    setHasSearched(true);
    try {
      const res = await fetch(
        `${API_BASE}/search/?q=${encodeURIComponent(query)}&search_type=${searchType}&limit=10`
      );
      if (!res.ok) throw new Error("Search failed");
      const data = await res.json();
      setResults(data.results);
      setGeneratedAnswer(data.generated_answer);
    } catch (error) {
      console.error("Search error:", error);
      setResults([]);
      setGeneratedAnswer(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex h-screen w-full overflow-hidden bg-[#0F1117]">
      <Sidebar />
      <div className="flex-1 flex flex-col h-screen overflow-y-auto relative">
        <div className="flex-1 flex flex-col items-center justify-start pt-20 px-4 gap-8">

          {/* Hero Section (only show when no search has been made) */}
          {!hasSearched && (
            <div className="text-center space-y-4 mb-8">
              <h1 className="text-5xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-600">
                SynapseVideo
              </h1>
              <p className="text-gray-400 text-lg max-w-xl mx-auto">
                Search through your videos using natural language. Find exact moments, spoken words, or visual scenes instantly.
              </p>
            </div>
          )}

          <div className="w-full max-w-3xl z-10">
            <SearchBar onSearch={handleSearch} loading={loading} />
          </div>

          <div className="w-full max-w-5xl pb-10">
            {hasSearched && (
              <SearchResults results={results} loading={loading} generatedAnswer={generatedAnswer} />
            )}
          </div>
        </div>

        {/* Background Gradients */}
        <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
          <div className="absolute top-[-10%] right-[10%] w-[500px] h-[500px] bg-purple-900/20 rounded-full blur-[120px]" />
          <div className="absolute bottom-[-10%] left-[10%] w-[500px] h-[500px] bg-blue-900/20 rounded-full blur-[120px]" />
        </div>
      </div>
    </main>
  );
}

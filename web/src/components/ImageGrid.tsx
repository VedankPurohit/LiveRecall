'use client';

import { useState } from 'react';
import { X, Sparkles } from 'lucide-react';
import type { Screenshot } from '@/types';

interface ImageGridProps {
  images: Screenshot[];
  getImageUrl: (path: string) => string;
  showSimilarity?: boolean;
}

function formatTimestamp(timestamp: string): string {
  if (timestamp.length !== 12) return timestamp;

  const year = 2000 + parseInt(timestamp.slice(0, 2));
  const month = parseInt(timestamp.slice(2, 4));
  const day = parseInt(timestamp.slice(4, 6));
  const hour = parseInt(timestamp.slice(6, 8));
  const minute = parseInt(timestamp.slice(8, 10));

  const date = new Date(year, month - 1, day, hour, minute);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

export function ImageGrid({ images, getImageUrl, showSimilarity = false }: ImageGridProps) {
  const [selectedImage, setSelectedImage] = useState<Screenshot | null>(null);

  if (images.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-[#86868b]">
        <div className="w-16 h-16 rounded-2xl bg-[#1c1c1e] flex items-center justify-center mb-5">
          <svg className="w-8 h-8 text-[#48484a]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
          </svg>
        </div>
        <p className="text-lg font-medium text-white mb-1">No screenshots yet</p>
        <p className="text-sm">Start recording to capture your screen</p>
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
        {images.map((image) => (
          <div
            key={image.id}
            onClick={() => setSelectedImage(image)}
            className="image-card relative group cursor-pointer rounded-xl overflow-hidden bg-[#1c1c1e]"
          >
            {/* Image */}
            <div className="aspect-video relative">
              <img
                src={getImageUrl(image.image_path)}
                alt=""
                className="w-full h-full object-cover"
                loading="lazy"
              />

              {/* Similarity Badge - pill style */}
              {showSimilarity && image.similarity !== undefined && (
                <div className="absolute top-2 right-2 px-2.5 py-1 bg-[#0a84ff] rounded-full text-xs text-white font-medium flex items-center gap-1 shadow-lg">
                  <Sparkles className="w-3 h-3" />
                  {(image.similarity * 100).toFixed(0)}%
                </div>
              )}
            </div>

            {/* Hover overlay with timestamp */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-end">
              <div className="p-3 w-full">
                <p className="text-sm text-white/90 font-medium">
                  {formatTimestamp(image.timestamp)}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Lightbox - Apple Photos style */}
      {selectedImage && (
        <div
          className="fixed inset-0 z-50 bg-black/95 flex items-center justify-center"
          onClick={() => setSelectedImage(null)}
        >
          {/* Close button */}
          <button
            onClick={() => setSelectedImage(null)}
            className="absolute top-5 right-5 z-10 w-10 h-10 flex items-center justify-center text-white/60 hover:text-white bg-white/10 hover:bg-white/20 rounded-full transition-all"
          >
            <X className="w-5 h-5" />
          </button>

          {/* Image container */}
          <div
            className="max-w-[90vw] max-h-[85vh] relative"
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={getImageUrl(selectedImage.image_path)}
              alt=""
              className="max-w-full max-h-[85vh] object-contain rounded-lg shadow-2xl"
            />
          </div>

          {/* Bottom info bar */}
          <div className="absolute bottom-0 inset-x-0 glass py-4 px-6">
            <div className="max-w-3xl mx-auto flex items-center justify-between">
              <div className="text-white">
                <p className="font-medium">{formatTimestamp(selectedImage.timestamp)}</p>
                {selectedImage.is_compressed === 1 && (
                  <p className="text-sm text-[#86868b] mt-0.5">Compressed</p>
                )}
              </div>
              {showSimilarity && selectedImage.similarity !== undefined && (
                <div className="flex items-center gap-2 text-[#0a84ff]">
                  <Sparkles className="w-4 h-4" />
                  <span className="font-medium">
                    {(selectedImage.similarity * 100).toFixed(1)}% match
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

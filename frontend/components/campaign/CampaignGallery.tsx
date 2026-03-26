"use client";

import { useState } from "react";
import Image from "next/image";
import { cn } from "@/lib/utils";

interface CampaignGalleryProps {
  images: string[];
  title: string;
}

export default function CampaignGallery({ images, title }: CampaignGalleryProps) {
  const [activeIndex, setActiveIndex] = useState(0);

  return (
    <div className="space-y-3">
      {/* Main image */}
      <div className="relative aspect-square rounded-xl overflow-hidden bg-gray-100">
        <Image
          src={images[activeIndex]}
          alt={`${title} - görsel ${activeIndex + 1}`}
          fill
          className="object-cover"
          sizes="(max-width: 768px) 100vw, 50vw"
          priority
        />
      </div>

      {/* Thumbnails */}
      {images.length > 1 && (
        <div className="flex gap-2">
          {images.map((src, i) => (
            <button
              key={i}
              onClick={() => setActiveIndex(i)}
              className={cn(
                "relative w-16 h-16 rounded-lg overflow-hidden border-2 transition-colors flex-shrink-0",
                activeIndex === i
                  ? "border-blue-600"
                  : "border-gray-200 hover:border-gray-400"
              )}
            >
              <Image
                src={src}
                alt={`Küçük resim ${i + 1}`}
                fill
                className="object-cover"
                sizes="64px"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

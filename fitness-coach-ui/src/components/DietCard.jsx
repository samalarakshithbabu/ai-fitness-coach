import React from "react";

/**
 * DietCard — displays a single meal (breakfast/lunch/dinner/snacks).
 */
export default function DietCard({ meal }) {
  const { title, emoji, items, total } = meal;

  return (
    <div className="bg-card border border-border rounded-xl p-5 hover:border-neon/30 hover:shadow-[0_0_15px_#39ff1415] transition-all duration-300 animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{emoji}</span>
          <h3 className="font-bold text-white text-base">{title}</h3>
        </div>
        <span className="text-xs font-semibold text-neon bg-neon/10 border border-neon/20 px-2.5 py-1 rounded-full">
          {total}
        </span>
      </div>

      {/* Items */}
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-gray-400">
            <span className="text-neon mt-0.5 flex-shrink-0">•</span>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

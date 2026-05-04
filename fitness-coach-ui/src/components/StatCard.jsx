import React from "react";

/**
 * StatCard — dashboard metric card with icon, value, label, and optional trend.
 */
export default function StatCard({ icon: Icon, label, value, unit = "", trend, color = "neon" }) {
  const colorMap = {
    neon:   "text-neon bg-neon/10 border-neon/20",
    blue:   "text-blue-400 bg-blue-400/10 border-blue-400/20",
    purple: "text-purple-400 bg-purple-400/10 border-purple-400/20",
    orange: "text-orange-400 bg-orange-400/10 border-orange-400/20",
  };

  const iconBg = {
    neon:   "bg-neon/10 text-neon",
    blue:   "bg-blue-400/10 text-blue-400",
    purple: "bg-purple-400/10 text-purple-400",
    orange: "bg-orange-400/10 text-orange-400",
  };

  return (
    <div
      className={`bg-card border rounded-xl p-5 flex items-start gap-4 hover:scale-[1.02] transition-all duration-200 ${colorMap[color]}`}
    >
      {/* Icon */}
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${iconBg[color]}`}>
        <Icon size={22} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-gray-500 text-xs font-medium uppercase tracking-wider mb-1">{label}</p>
        <p className="text-2xl font-bold text-white">
          {value}
          {unit && <span className="text-sm font-normal text-gray-500 ml-1">{unit}</span>}
        </p>
        {trend && (
          <p className={`text-xs mt-1 ${trend.up ? "text-neon" : "text-red-400"}`}>
            {trend.up ? "▲" : "▼"} {trend.label}
          </p>
        )}
      </div>
    </div>
  );
}

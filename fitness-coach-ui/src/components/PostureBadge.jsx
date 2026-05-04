import React from "react";
import { CheckCircle, AlertTriangle, XCircle } from "lucide-react";

/**
 * PostureBadge — animated status indicator for posture feedback.
 * status: "correct" | "warning" | "incorrect"
 */
export default function PostureBadge({ status, large = false }) {
  const config = {
    correct: {
      icon: CheckCircle,
      label: "Correct Form",
      classes: "text-neon bg-neon/10 border-neon/30",
      pulse: "bg-neon",
    },
    warning: {
      icon: AlertTriangle,
      label: "Needs Improvement",
      classes: "text-yellow-400 bg-yellow-400/10 border-yellow-400/30",
      pulse: "bg-yellow-400",
    },
    incorrect: {
      icon: XCircle,
      label: "Incorrect Form",
      classes: "text-red-400 bg-red-400/10 border-red-400/30",
      pulse: "bg-red-400",
    },
  };

  const { icon: Icon, label, classes, pulse } = config[status] || config.warning;
  const size = large ? "text-base px-4 py-2" : "text-xs px-3 py-1.5";

  return (
    <span className={`inline-flex items-center gap-2 border rounded-full font-semibold ${classes} ${size}`}>
      {/* Animated pulse dot */}
      <span className="relative flex h-2 w-2">
        <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-60 ${pulse}`} />
        <span className={`relative inline-flex rounded-full h-2 w-2 ${pulse}`} />
      </span>
      <Icon size={large ? 16 : 13} />
      {label}
    </span>
  );
}

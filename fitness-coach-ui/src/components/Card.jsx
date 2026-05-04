import React from "react";

/**
 * Card — base surface card with optional neon border highlight.
 */
export default function Card({ children, className = "", glow = false }) {
  return (
    <div
      className={`bg-card border rounded-xl p-5 transition-all duration-300 ${
        glow
          ? "border-neon/40 shadow-[0_0_15px_#39ff1420] hover:shadow-[0_0_25px_#39ff1440]"
          : "border-border hover:border-neon/20"
      } ${className}`}
    >
      {children}
    </div>
  );
}

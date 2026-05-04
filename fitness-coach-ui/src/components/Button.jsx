import React from "react";

/**
 * Button — reusable button with variant support.
 * variants: "primary" | "outline" | "danger" | "ghost"
 */
export default function Button({
  children,
  onClick,
  variant = "primary",
  size = "md",
  disabled = false,
  className = "",
  type = "button",
  icon: Icon,
}) {
  const base =
    "inline-flex items-center justify-center gap-2 font-semibold rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-neon/50 disabled:opacity-40 disabled:cursor-not-allowed";

  const sizes = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-5 py-2.5 text-sm",
    lg: "px-7 py-3.5 text-base",
  };

  const variants = {
    primary:
      "bg-neon text-black hover:bg-neon-dim hover:shadow-[0_0_15px_#39ff1460] active:scale-95",
    outline:
      "border border-neon text-neon bg-transparent hover:bg-neon/10 hover:shadow-[0_0_10px_#39ff1430]",
    danger:
      "bg-red-600 text-white hover:bg-red-500 active:scale-95",
    ghost:
      "text-gray-400 hover:text-neon hover:bg-neon/5",
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${sizes[size]} ${variants[variant]} ${className}`}
    >
      {Icon && <Icon size={16} />}
      {children}
    </button>
  );
}

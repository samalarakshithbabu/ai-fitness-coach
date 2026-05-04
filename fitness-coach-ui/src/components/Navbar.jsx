import React, { useState, useEffect } from "react";
import { NavLink } from "react-router-dom";
import { Menu, X, Zap } from "lucide-react";

const links = [
  { to: "/",           label: "Home" },
  { to: "/dashboard",  label: "Dashboard" },
  { to: "/workout",    label: "Workout" },
  { to: "/diet",       label: "Diet" },
  { to: "/exercises",  label: "Exercises" },
];

/**
 * Navbar — sticky, responsive.
 * Collapses to hamburger on mobile.
 * Active link highlighted with neon green.
 */
export default function Navbar() {
  const [open, setOpen]       = useState(false);
  const [scrolled, setScrolled] = useState(false);

  // Add shadow/blur on scroll
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const linkClass = ({ isActive }) =>
    `text-sm font-medium px-3 py-1.5 rounded-md transition-all duration-200 ${
      isActive
        ? "text-neon neon-text border border-neon/30 bg-neon/5"
        : "text-gray-400 hover:text-neon hover:bg-neon/5"
    }`;

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? "bg-dark/95 backdrop-blur-md border-b border-border shadow-lg" : "bg-transparent"
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">

          {/* Logo */}
          <NavLink to="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 bg-neon rounded-lg flex items-center justify-center group-hover:neon-glow transition-all">
              <Zap size={18} className="text-black" fill="black" />
            </div>
            <span className="font-bold text-white text-lg tracking-tight">
              AI<span className="text-neon">Fit</span>
            </span>
          </NavLink>

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-1">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to} className={linkClass}>
                {l.label}
              </NavLink>
            ))}
          </div>

          {/* CTA button — desktop */}
          <div className="hidden md:block">
            <NavLink
              to="/workout"
              className="bg-neon text-black text-sm font-bold px-4 py-2 rounded-lg hover:bg-neon-dim hover:neon-glow transition-all"
            >
              Start Training
            </NavLink>
          </div>

          {/* Hamburger — mobile */}
          <button
            className="md:hidden text-gray-400 hover:text-neon p-1"
            onClick={() => setOpen(!open)}
            aria-label="Toggle menu"
          >
            {open ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden bg-surface border-t border-border px-4 pb-4 pt-2 animate-fade-in">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) =>
                `block py-2.5 px-3 rounded-md text-sm font-medium mb-1 ${
                  isActive ? "text-neon bg-neon/10" : "text-gray-400 hover:text-neon hover:bg-neon/5"
                }`
              }
              onClick={() => setOpen(false)}
            >
              {l.label}
            </NavLink>
          ))}
          <NavLink
            to="/workout"
            className="block mt-2 bg-neon text-black text-sm font-bold px-4 py-2.5 rounded-lg text-center"
            onClick={() => setOpen(false)}
          >
            Start Training
          </NavLink>
        </div>
      )}
    </nav>
  );
}

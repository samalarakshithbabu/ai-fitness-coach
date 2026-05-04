import React from "react";
import { useNavigate } from "react-router-dom";
import { Zap, Brain, Salad, BarChart2, ChevronRight, Shield, Target, TrendingUp } from "lucide-react";
import Button from "../components/Button";

/** Feature card for the features section */
function FeatureCard({ icon: Icon, title, desc, color }) {
  const colors = {
    neon:   "text-neon bg-neon/10 border-neon/20",
    blue:   "text-blue-400 bg-blue-400/10 border-blue-400/20",
    purple: "text-purple-400 bg-purple-400/10 border-purple-400/20",
  };
  return (
    <div className="bg-card border border-border rounded-xl p-6 hover:border-neon/30 hover:translate-y-[-4px] transition-all duration-300 group">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 border ${colors[color]}`}>
        <Icon size={22} />
      </div>
      <h3 className="font-bold text-white text-lg mb-2 group-hover:text-neon transition-colors">{title}</h3>
      <p className="text-gray-500 text-sm leading-relaxed">{desc}</p>
    </div>
  );
}

/** Step card for how-it-works section */
function StepCard({ number, title, desc }) {
  return (
    <div className="flex gap-4">
      <div className="flex-shrink-0 w-10 h-10 rounded-full bg-neon/10 border border-neon/30 flex items-center justify-center text-neon font-bold text-sm">
        {number}
      </div>
      <div>
        <h4 className="font-semibold text-white mb-1">{title}</h4>
        <p className="text-gray-500 text-sm leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}

/**
 * Home — landing page with hero, features, how-it-works, and CTA sections.
 */
export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen">

      {/* ── HERO ──────────────────────────────────────────────────────────── */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden">

        {/* Gradient background */}
        <div className="absolute inset-0 bg-gradient-to-br from-dark via-[#0d1a0d] to-dark" />

        {/* Animated grid overlay */}
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage:
              "linear-gradient(#39ff14 1px, transparent 1px), linear-gradient(90deg, #39ff14 1px, transparent 1px)",
            backgroundSize: "60px 60px",
          }}
        />

        {/* Glow orbs */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-neon/5 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-neon/8 rounded-full blur-3xl pointer-events-none" />

        {/* Content */}
        <div className="relative z-10 text-center px-4 max-w-4xl mx-auto animate-fade-in">

          {/* Badge */}
          <div className="inline-flex items-center gap-2 bg-neon/10 border border-neon/30 text-neon text-xs font-semibold px-4 py-2 rounded-full mb-8">
            <Zap size={12} fill="currentColor" />
            Powered by Deep Learning & Computer Vision
          </div>

          {/* Title */}
          <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-black text-white leading-tight mb-6">
            AI-Powered{" "}
            <span className="text-neon neon-text block sm:inline">Personal Fitness</span>{" "}
            Coach
          </h1>

          {/* Subtitle */}
          <p className="text-gray-400 text-lg sm:text-xl max-w-2xl mx-auto mb-10 leading-relaxed">
            Smart Posture Detection &amp; Personalized Diet Guidance — using deep learning to
            analyze your form in real-time and build a plan tailored to you.
          </p>

          {/* CTA buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" onClick={() => navigate("/workout")} icon={Zap}>
              Get Started
            </Button>
            <Button size="lg" variant="outline" onClick={() => navigate("/dashboard")} icon={BarChart2}>
              View Dashboard
            </Button>
          </div>

          {/* Stats row */}
          <div className="mt-16 grid grid-cols-3 gap-6 max-w-lg mx-auto">
            {[
              { value: "22+", label: "Exercises" },
              { value: "33", label: "Keypoints" },
              { value: "Real-time", label: "Feedback" },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-2xl font-black text-neon neon-text">{s.value}</div>
                <div className="text-gray-600 text-xs mt-1">{s.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1 text-gray-600 text-xs animate-bounce">
          <span>Scroll</span>
          <ChevronRight size={14} className="rotate-90" />
        </div>
      </section>

      {/* ── FEATURES ──────────────────────────────────────────────────────── */}
      <section className="py-24 px-4 max-w-7xl mx-auto">
        <div className="text-center mb-14">
          <p className="text-neon text-sm font-semibold uppercase tracking-widest mb-3">Features</p>
          <h2 className="text-3xl sm:text-4xl font-black text-white">Everything you need to train smarter</h2>
          <p className="text-gray-500 mt-3 max-w-xl mx-auto text-sm">
            Combining computer vision, deep learning, and nutrition science into one platform.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          <FeatureCard
            icon={Brain}
            color="neon"
            title="AI Posture Detection"
            desc="Real-time analysis using MediaPipe's 33-keypoint skeleton to detect form errors across 8 exercise types."
          />
          <FeatureCard
            icon={Salad}
            color="blue"
            title="Personalized Diet Plans"
            desc="BMI-aware meal plans tailored to your goal — weight loss, muscle gain, or maintenance."
          />
          <FeatureCard
            icon={BarChart2}
            color="purple"
            title="Progress Dashboard"
            desc="Track calories burned, workouts completed, and posture scores over time with interactive charts."
          />
          <FeatureCard
            icon={Shield}
            color="neon"
            title="Injury Prevention"
            desc="Instant feedback on dangerous movement patterns before they cause long-term damage."
          />
          <FeatureCard
            icon={Target}
            color="blue"
            title="Goal-Based Training"
            desc="Beginner to advanced workout plans that adapt to your fitness level and BMI category."
          />
          <FeatureCard
            icon={TrendingUp}
            color="purple"
            title="Rep Counting"
            desc="Automatic rep and set tracking so you can focus on form instead of counting."
          />
        </div>
      </section>

      {/* ── HOW IT WORKS ──────────────────────────────────────────────────── */}
      <section className="py-20 px-4 bg-surface border-y border-border">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-14">
            <p className="text-neon text-sm font-semibold uppercase tracking-widest mb-3">How It Works</p>
            <h2 className="text-3xl sm:text-4xl font-black text-white">Three steps to better form</h2>
          </div>

          <div className="grid md:grid-cols-3 gap-10">
            <StepCard
              number="01"
              title="Upload or Use Webcam"
              desc="Upload a workout image/video or enable your webcam for live posture analysis."
            />
            <StepCard
              number="02"
              title="AI Analyzes Your Form"
              desc="YOLOv8 detects the exercise, MediaPipe extracts 33 keypoints, and rule-based checks flag issues."
            />
            <StepCard
              number="03"
              title="Get Instant Feedback"
              desc="Receive a posture score, specific corrections, and a personalized workout + diet plan."
            />
          </div>
        </div>
      </section>

      {/* ── BOTTOM CTA ────────────────────────────────────────────────────── */}
      <section className="py-24 px-4 text-center">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-black text-white mb-4">
            Ready to train with <span className="text-neon neon-text">AI precision?</span>
          </h2>
          <p className="text-gray-500 mb-8 text-sm">
            Start your first session now — no equipment needed, just your camera.
          </p>
          <Button size="lg" onClick={() => navigate("/workout")} icon={Zap}>
            Start Your First Session
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-6 text-center text-gray-600 text-xs">
        AI-Powered Personal Fitness Coach — Final Year Major Project &nbsp;·&nbsp; Deep Learning + FastAPI + MediaPipe
      </footer>
    </div>
  );
}

import React, { useState } from "react";
import { Salad, Flame, ChevronRight, Sparkles } from "lucide-react";
import Button from "../components/Button";
import DietCard from "../components/DietCard";
import { dietPlans } from "../data/mockData";

const API_BASE = "http://localhost:8000";

// Map frontend goal keys to backend fitness_goal values
const GOAL_MAP = { lose: "fat_loss", gain: "muscle_gain", maintain: "endurance" };

/**
 * Diet — personalized diet recommendation page.
 * User fills in age, weight, and goal → generates a meal plan.
 */
export default function Diet() {
  const [form, setForm]     = useState({ age: "25", weight: "70", height: "170", goal: "lose" });
  const [plan, setPlan]     = useState(null);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  const validate = () => {
    const e = {};
    if (!form.age || form.age < 10 || form.age > 100) e.age = "Enter a valid age (10–100)";
    if (!form.weight || form.weight < 30 || form.weight > 300) e.weight = "Enter a valid weight (30–300 kg)";
    if (!form.height || form.height < 100 || form.height > 250) e.height = "Enter a valid height (100–250 cm)";
    return e;
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setErrors({});
    setLoading(true);
    setPlan(null);

    try {
      // Try real backend first
      const formData = new FormData();
      formData.append("age",           form.age);
      formData.append("weight_kg",     form.weight);
      formData.append("height_cm",     form.height);
      formData.append("fitness_goal",  GOAL_MAP[form.goal] || "fat_loss");
      formData.append("detected_exercise", "");

      const res = await fetch(`${API_BASE}/get-recommendation`, { method: "POST", body: formData });
      if (!res.ok) throw new Error("Backend error");
      const data = await res.json();

      // Convert backend plan format to frontend DietCard format
      const calMap = { fat_loss: 1600, muscle_gain: 2800, endurance: 2200 };
      const goalLabel = { fat_loss: "Weight Loss", muscle_gain: "Muscle Gain", endurance: "Maintenance" };
      setPlan({
        goal:     goalLabel[data.goal] || data.goal,
        calories: calMap[data.goal] || 2000,
        level:    data.level,
        bmi:      data.bmi_category,
        exercises: data.exercises,
        tips:     data.tips,
        schedule: data.weekly_schedule,
        highlight: data.highlight,
        // Keep mock meals for display (backend doesn't return meal plans)
        meals:    dietPlans[form.goal]?.meals || {},
      });
    } catch {
      // Fallback to mock data if backend is offline
      setPlan(dietPlans[form.goal]);
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="min-h-screen pt-20 pb-12 px-4 max-w-7xl mx-auto">

      {/* Header */}
      <div className="mb-8 animate-fade-in">
        <p className="text-neon text-sm font-semibold uppercase tracking-widest mb-1">Nutrition</p>
        <h1 className="text-3xl font-black text-white">Diet Recommendations</h1>
        <p className="text-gray-500 text-sm mt-1">
          Enter your details to get a personalized meal plan tailored to your fitness goal.
        </p>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">

        {/* ── FORM ──────────────────────────────────────────────────────── */}
        <div className="lg:col-span-1">
          <div className="bg-card border border-border rounded-2xl p-6 sticky top-24">
            <div className="flex items-center gap-2 mb-6">
              <div className="w-9 h-9 bg-neon/10 border border-neon/20 rounded-xl flex items-center justify-center">
                <Salad size={18} className="text-neon" />
              </div>
              <h2 className="font-bold text-white">Your Profile</h2>
            </div>

            <form onSubmit={handleGenerate} className="space-y-5">

              {/* Age */}
              <div>
                <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5">
                  Age
                </label>
                <input
                  type="number"
                  min="10" max="100"
                  placeholder="e.g. 25"
                  value={form.age}
                  onChange={(e) => setForm({ ...form, age: e.target.value })}
                  className={`w-full bg-surface border rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-600 outline-none transition-all focus:border-neon focus:shadow-[0_0_0_2px_#39ff1420] ${
                    errors.age ? "border-red-500" : "border-border"
                  }`}
                />
                {errors.age && <p className="text-red-400 text-xs mt-1">{errors.age}</p>}
              </div>

              {/* Weight */}
              <div>
                <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5">
                  Weight (kg)
                </label>
                <input
                  type="number"
                  min="30" max="300"
                  placeholder="e.g. 70"
                  value={form.weight}
                  onChange={(e) => setForm({ ...form, weight: e.target.value })}
                  className={`w-full bg-surface border rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-600 outline-none transition-all focus:border-neon focus:shadow-[0_0_0_2px_#39ff1420] ${
                    errors.weight ? "border-red-500" : "border-border"
                  }`}
                />
                {errors.weight && <p className="text-red-400 text-xs mt-1">{errors.weight}</p>}
              </div>

              {/* Height */}
              <div>
                <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5">
                  Height (cm)
                </label>
                <input
                  type="number"
                  min="100" max="250"
                  placeholder="e.g. 170"
                  value={form.height}
                  onChange={(e) => setForm({ ...form, height: e.target.value })}
                  className={`w-full bg-surface border rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-600 outline-none transition-all focus:border-neon focus:shadow-[0_0_0_2px_#39ff1420] ${
                    errors.height ? "border-red-500" : "border-border"
                  }`}
                />
                {errors.height && <p className="text-red-400 text-xs mt-1">{errors.height}</p>}
              </div>

              {/* Fitness Goal */}
              <div>
                <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider mb-1.5">
                  Fitness Goal
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { value: "lose",     label: "Lose",     emoji: "🔥" },
                    { value: "gain",     label: "Gain",     emoji: "💪" },
                    { value: "maintain", label: "Maintain", emoji: "⚖️" },
                  ].map((g) => (
                    <button
                      key={g.value}
                      type="button"
                      onClick={() => setForm({ ...form, goal: g.value })}
                      className={`flex flex-col items-center gap-1 py-3 rounded-xl border text-xs font-semibold transition-all duration-200 ${
                        form.goal === g.value
                          ? "border-neon bg-neon/10 text-neon"
                          : "border-border text-gray-500 hover:border-neon/30 hover:text-gray-300"
                      }`}
                    >
                      <span className="text-lg">{g.emoji}</span>
                      {g.label}
                    </button>
                  ))}
                </div>
              </div>

              <Button type="submit" size="lg" className="w-full" disabled={loading} icon={Sparkles}>
                {loading ? "Generating…" : "Generate Diet Plan"}
              </Button>
            </form>
          </div>
        </div>

        {/* ── RESULTS ───────────────────────────────────────────────────── */}
        <div className="lg:col-span-2">
          {/* Loading skeleton */}
          {loading && (
            <div className="space-y-4 animate-pulse">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="bg-card border border-border rounded-xl p-5 h-36" />
              ))}
            </div>
          )}

          {/* Empty state */}
          {!loading && !plan && (
            <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-center">
              <div className="w-20 h-20 bg-surface border border-border rounded-2xl flex items-center justify-center mb-4">
                <Salad size={36} className="text-gray-700" />
              </div>
              <h3 className="text-gray-500 font-semibold mb-2">No plan generated yet</h3>
              <p className="text-gray-700 text-sm max-w-xs">
                Fill in your profile on the left and click "Generate Diet Plan" to see your personalized meals.
              </p>
            </div>
          )}

          {/* Plan results */}
          {!loading && plan && (
            <div className="animate-fade-in space-y-6">

              {/* Plan header */}
              <div className="bg-card border border-neon/30 rounded-2xl p-5 shadow-[0_0_20px_#39ff1420]">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-gray-500 text-xs uppercase tracking-wider mb-1">Your Plan</p>
                    <h2 className="text-xl font-black text-white">{plan.goal}</h2>
                  </div>
                  <div className="flex items-center gap-2">
                    <Flame size={16} className="text-neon" />
                    <span className="text-neon font-bold text-lg">{plan.calories.toLocaleString()}</span>
                    <span className="text-gray-500 text-sm">kcal / day</span>
                  </div>
                </div>
              </div>

              {/* Meal cards */}
              <div className="grid sm:grid-cols-2 gap-4">
                {Object.values(plan.meals).map((meal) => (
                  <DietCard key={meal.title} meal={meal} />
                ))}
              </div>

              {/* Tips */}
              <div className="bg-card border border-border rounded-2xl p-5">
                <h3 className="font-bold text-white mb-4 flex items-center gap-2">
                  <span className="text-neon">💡</span> Nutrition Tips
                </h3>
                <ul className="space-y-2.5">
                  {plan.tips.map((tip, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-400">
                      <ChevronRight size={14} className="text-neon mt-0.5 flex-shrink-0" />
                      {tip}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Workout plan from backend */}
              {plan.exercises && (
                <div className="bg-card border border-border rounded-2xl p-5">
                  <h3 className="font-bold text-white mb-1 flex items-center gap-2">
                    <span className="text-neon">🏋️</span> Recommended Workout Plan
                  </h3>
                  {plan.level && (
                    <p className="text-gray-500 text-xs mb-4 capitalize">
                      Level: {plan.level} · {plan.schedule}
                    </p>
                  )}
                  {plan.highlight && (
                    <p className="text-neon text-xs mb-3">{plan.highlight}</p>
                  )}
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border text-left">
                          <th className="pb-2 text-gray-500 text-xs uppercase tracking-wider">Exercise</th>
                          <th className="pb-2 text-gray-500 text-xs uppercase tracking-wider">Sets</th>
                          <th className="pb-2 text-gray-500 text-xs uppercase tracking-wider">Reps</th>
                          <th className="pb-2 text-gray-500 text-xs uppercase tracking-wider">Rest</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {plan.exercises.map((ex, i) => (
                          <tr key={i}>
                            <td className="py-2.5 text-white font-medium">{ex.name}</td>
                            <td className="py-2.5 text-gray-400">{ex.sets}</td>
                            <td className="py-2.5 text-gray-400">{ex.reps}</td>
                            <td className="py-2.5 text-gray-400">{ex.rest}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

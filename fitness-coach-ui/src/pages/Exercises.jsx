import React, { useState } from "react";
import { Search, Dumbbell, ChevronRight } from "lucide-react";
import Card from "../components/Card";

const EXERCISES = [
  { id: 0,  name: "Deadlift",             muscle: "Back, Glutes, Hamstrings", difficulty: "Advanced",     emoji: "🏋️", tip: "Keep bar close to shins, drive hips forward at lockout." },
  { id: 1,  name: "Lateral Raise",        muscle: "Shoulders (Medial Delt)",  difficulty: "Beginner",     emoji: "💪", tip: "Slight elbow bend, raise to shoulder height only." },
  { id: 2,  name: "Squat",                muscle: "Quads, Glutes, Core",      difficulty: "Intermediate", emoji: "🦵", tip: "Knees track over toes, chest tall, break parallel." },
  { id: 3,  name: "Front Squat",          muscle: "Quads, Core, Upper Back",  difficulty: "Advanced",     emoji: "🦵", tip: "Elbows high, very upright torso throughout." },
  { id: 4,  name: "Zercher Squat",        muscle: "Quads, Core, Biceps",      difficulty: "Advanced",     emoji: "🦵", tip: "Bar in elbow crease, stay upright, brace hard." },
  { id: 5,  name: "Romanian Deadlift",    muscle: "Hamstrings, Glutes",       difficulty: "Intermediate", emoji: "🏋️", tip: "Soft knee bend, hinge at hips, bar stays close to legs." },
  { id: 6,  name: "Sumo Deadlift",        muscle: "Glutes, Inner Thighs",     difficulty: "Intermediate", emoji: "🏋️", tip: "Wide stance, toes out, knees push out over toes." },
  { id: 7,  name: "Bench Press",          muscle: "Chest, Triceps, Shoulders",difficulty: "Intermediate", emoji: "🤸", tip: "Retract scapula, bar to lower chest, drive feet into floor." },
  { id: 8,  name: "Incline Bench Press",  muscle: "Upper Chest, Shoulders",   difficulty: "Intermediate", emoji: "🤸", tip: "30–45° incline, control the descent, don't flare elbows." },
  { id: 9,  name: "Decline Bench Press",  muscle: "Lower Chest, Triceps",     difficulty: "Intermediate", emoji: "🤸", tip: "Secure feet, lower bar to lower chest, full ROM." },
  { id: 10, name: "Barbell Biceps Curl",  muscle: "Biceps",                   difficulty: "Beginner",     emoji: "💪", tip: "Elbows pinned to sides, full extension at bottom." },
  { id: 11, name: "Hammer Curl",          muscle: "Biceps, Brachialis",       difficulty: "Beginner",     emoji: "💪", tip: "Neutral grip, controlled tempo, no swinging." },
  { id: 12, name: "Shoulder Press",       muscle: "Shoulders, Triceps",       difficulty: "Intermediate", emoji: "🙌", tip: "Press directly overhead, don't arch lower back." },
  { id: 13, name: "Lat Pulldown",         muscle: "Lats, Biceps",             difficulty: "Beginner",     emoji: "🙌", tip: "Pull to upper chest, lean back slightly, squeeze lats." },
  { id: 14, name: "Pull Up",              muscle: "Lats, Biceps, Core",       difficulty: "Advanced",     emoji: "🙌", tip: "Dead hang start, chin over bar, avoid kipping." },
  { id: 15, name: "Push Up",              muscle: "Chest, Triceps, Core",     difficulty: "Beginner",     emoji: "🤸", tip: "Straight body line, elbows at 45°, chest touches floor." },
  { id: 16, name: "Leg Extension",        muscle: "Quadriceps",               difficulty: "Beginner",     emoji: "🦵", tip: "Full extension at top, slow eccentric, avoid locking out hard." },
  { id: 17, name: "Leg Raises",           muscle: "Lower Abs, Hip Flexors",   difficulty: "Beginner",     emoji: "🦵", tip: "Keep lower back pressed down, controlled lowering." },
  { id: 18, name: "Hip Thrust",           muscle: "Glutes, Hamstrings",       difficulty: "Intermediate", emoji: "🍑", tip: "Drive through heels, squeeze glutes at top, chin tucked." },
  { id: 19, name: "Plank",               muscle: "Core, Shoulders",           difficulty: "Beginner",     emoji: "🧘", tip: "Neutral spine, don't let hips sag or pike up." },
  { id: 20, name: "Tricep Dips",          muscle: "Triceps, Chest",           difficulty: "Intermediate", emoji: "💪", tip: "Elbows back not flared, lower until 90°, full lockout." },
  { id: 21, name: "Tricep Pushdown",      muscle: "Triceps",                  difficulty: "Beginner",     emoji: "💪", tip: "Elbows fixed at sides, full extension, squeeze at bottom." },
  { id: 22, name: "T-Bar Row",            muscle: "Back, Biceps, Rear Delt",  difficulty: "Intermediate", emoji: "🏋️", tip: "Chest on pad, pull to sternum, squeeze shoulder blades." },
  { id: 23, name: "Russian Twist",        muscle: "Obliques, Core",           difficulty: "Beginner",     emoji: "🧘", tip: "Feet off floor, rotate fully each side, control the twist." },
  { id: 24, name: "Chest Fly Machine",    muscle: "Chest, Front Delt",        difficulty: "Beginner",     emoji: "🤸", tip: "Slight elbow bend, full stretch at open, squeeze at close." },
];

const DIFFICULTIES = ["All", "Beginner", "Intermediate", "Advanced"];

const diffColor = {
  Beginner:     "text-neon bg-neon/10 border-neon/20",
  Intermediate: "text-yellow-400 bg-yellow-400/10 border-yellow-400/20",
  Advanced:     "text-red-400 bg-red-400/10 border-red-400/20",
};

export default function Exercises() {
  const [query, setQuery]      = useState("");
  const [filter, setFilter]    = useState("All");
  const [selected, setSelected] = useState(null);

  const filtered = EXERCISES.filter((ex) => {
    const matchQuery = ex.name.toLowerCase().includes(query.toLowerCase()) ||
                       ex.muscle.toLowerCase().includes(query.toLowerCase());
    const matchDiff  = filter === "All" || ex.difficulty === filter;
    return matchQuery && matchDiff;
  });

  return (
    <div className="min-h-screen pt-20 pb-12 px-4 max-w-7xl mx-auto">

      {/* Header */}
      <div className="mb-8 animate-fade-in">
        <p className="text-neon text-sm font-semibold uppercase tracking-widest mb-1">Reference</p>
        <h1 className="text-3xl font-black text-white">Exercise Library</h1>
        <p className="text-gray-500 text-sm mt-1">
          All {EXERCISES.length} exercises supported by the AI detection model.
        </p>
      </div>

      {/* Search + filter bar */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-600" />
          <input
            type="text"
            placeholder="Search exercise or muscle group…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-surface border border-border rounded-lg pl-9 pr-4 py-2.5 text-sm text-white placeholder-gray-600 outline-none focus:border-neon transition-all"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          {DIFFICULTIES.map((d) => (
            <button
              key={d}
              onClick={() => setFilter(d)}
              className={`px-3 py-2 rounded-lg text-xs font-semibold border transition-all ${
                filter === d
                  ? "bg-neon text-black border-neon"
                  : "bg-surface border-border text-gray-400 hover:border-neon/40 hover:text-gray-200"
              }`}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      {/* Count */}
      <p className="text-gray-600 text-xs mb-4">{filtered.length} exercise{filtered.length !== 1 ? "s" : ""} found</p>

      <div className="grid lg:grid-cols-3 gap-6">

        {/* Exercise grid */}
        <div className="lg:col-span-2 grid sm:grid-cols-2 gap-3 content-start">
          {filtered.length === 0 && (
            <div className="sm:col-span-2 text-center py-16 text-gray-600">
              <Dumbbell size={36} className="mx-auto mb-3 opacity-30" />
              <p>No exercises match your search.</p>
            </div>
          )}
          {filtered.map((ex) => (
            <button
              key={ex.id}
              onClick={() => setSelected(ex)}
              className={`text-left bg-card border rounded-xl p-4 transition-all duration-200 hover:border-neon/40 hover:shadow-[0_0_15px_#39ff1415] hover:-translate-y-0.5 ${
                selected?.id === ex.id ? "border-neon shadow-[0_0_15px_#39ff1430]" : "border-border"
              }`}
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <span className="text-2xl">{ex.emoji}</span>
                <span className={`text-xs font-semibold border px-2 py-0.5 rounded-full ${diffColor[ex.difficulty]}`}>
                  {ex.difficulty}
                </span>
              </div>
              <p className="font-bold text-white text-sm mb-1">{ex.name}</p>
              <p className="text-gray-500 text-xs">{ex.muscle}</p>
            </button>
          ))}
        </div>

        {/* Detail panel */}
        <div className="lg:col-span-1">
          <div className="sticky top-24">
            {selected ? (
              <Card glow>
                <div className="text-4xl mb-3">{selected.emoji}</div>
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <h2 className="text-xl font-black text-white">{selected.name}</h2>
                  <span className={`text-xs font-semibold border px-2 py-0.5 rounded-full ${diffColor[selected.difficulty]}`}>
                    {selected.difficulty}
                  </span>
                </div>
                <p className="text-gray-500 text-xs mb-4">Class ID: {selected.id}</p>

                <div className="space-y-4">
                  <div>
                    <p className="text-gray-500 text-xs uppercase tracking-wider mb-1">Muscles Worked</p>
                    <p className="text-white text-sm font-medium">{selected.muscle}</p>
                  </div>
                  <div>
                    <p className="text-gray-500 text-xs uppercase tracking-wider mb-1">Form Tip</p>
                    <div className="flex items-start gap-2 bg-surface border border-neon/20 rounded-lg px-3 py-2.5">
                      <ChevronRight size={13} className="text-neon mt-0.5 flex-shrink-0" />
                      <p className="text-gray-300 text-xs leading-relaxed">{selected.tip}</p>
                    </div>
                  </div>
                  <div>
                    <p className="text-gray-500 text-xs uppercase tracking-wider mb-1">AI Detection</p>
                    <p className="text-neon text-xs font-semibold">✓ Supported</p>
                  </div>
                </div>
              </Card>
            ) : (
              <Card>
                <div className="flex flex-col items-center justify-center py-10 text-center">
                  <Dumbbell size={32} className="text-gray-700 mb-3" />
                  <p className="text-gray-600 text-sm">Select an exercise to see details.</p>
                </div>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

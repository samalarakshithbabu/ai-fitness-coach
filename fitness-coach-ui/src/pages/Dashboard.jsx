import React, { useState, useEffect } from "react";
import { Flame, Dumbbell, Activity, Zap } from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import StatCard from "../components/StatCard";
import Card from "../components/Card";
import PostureBadge from "../components/PostureBadge";
import { userStats, weeklyCalories, workoutProgress } from "../data/mockData";

const API_BASE = "http://localhost:8000";

/** Custom recharts tooltip */
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-gray-400 mb-1">{label}</p>
      <p className="text-neon font-bold">{payload[0].value} {payload[0].name === "calories" ? "kcal" : "reps"}</p>
    </div>
  );
}

/**
 * Dashboard — user stats, charts, and recent workout history.
 * Recent workouts are fetched live from the backend /history endpoint.
 */
export default function Dashboard() {
  const [recentWorkouts, setRecentWorkouts] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/history?limit=10`)
      .then((r) => r.json())
      .then((data) => {
        // Map backend session format to table row format
        const rows = (data.history || []).map((s, i) => ({
          id:     s.id,
          name:   s.exercise,
          sets:   "—",
          reps:   "—",
          score:  s.score,
          status: s.posture_ok ? "correct" : s.score >= 70 ? "warning" : "incorrect",
        }));
        setRecentWorkouts(rows);
      })
      .catch(() => setRecentWorkouts([]))
      .finally(() => setHistoryLoading(false));
  }, []);

  return (
    <div className="min-h-screen pt-20 pb-12 px-4 max-w-7xl mx-auto">

      {/* Page header */}
      <div className="mb-8 animate-fade-in">
        <p className="text-neon text-sm font-semibold uppercase tracking-widest mb-1">Overview</p>
        <h1 className="text-3xl font-black text-white">Your Dashboard</h1>
        <p className="text-gray-500 text-sm mt-1">Track your progress and performance at a glance.</p>
      </div>

      {/* ── STAT CARDS ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8 animate-slide-up">
        <StatCard
          icon={Flame}
          label="Calories Burned"
          value={userStats.caloriesBurned.toLocaleString()}
          unit="kcal"
          color="neon"
          trend={{ up: true, label: "+12% this week" }}
        />
        <StatCard
          icon={Dumbbell}
          label="Workouts Done"
          value={userStats.workoutsCompleted}
          unit="sessions"
          color="blue"
          trend={{ up: true, label: "+3 this week" }}
        />
        <StatCard
          icon={Activity}
          label="BMI"
          value={userStats.bmi}
          color="purple"
          trend={{ up: true, label: "Normal range" }}
        />
        <StatCard
          icon={Zap}
          label="Day Streak"
          value={userStats.streak}
          unit="days"
          color="orange"
          trend={{ up: true, label: "Personal best!" }}
        />
      </div>

      {/* ── CHARTS ──────────────────────────────────────────────────────── */}
      <div className="grid lg:grid-cols-2 gap-6 mb-8">

        {/* Calories chart */}
        <Card>
          <h3 className="font-bold text-white mb-1">Weekly Calories Burned</h3>
          <p className="text-gray-500 text-xs mb-5">Last 7 days</p>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={weeklyCalories} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="calGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#39ff14" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#39ff14" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
              <XAxis dataKey="day" tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="calories"
                stroke="#39ff14"
                strokeWidth={2}
                fill="url(#calGrad)"
                dot={{ fill: "#39ff14", r: 3 }}
                activeDot={{ r: 5, fill: "#39ff14" }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        {/* Rep progress chart */}
        <Card>
          <h3 className="font-bold text-white mb-1">Rep Progress</h3>
          <p className="text-gray-500 text-xs mb-5">Weekly total reps</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={workoutProgress} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
              <XAxis dataKey="week" tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="reps" fill="#39ff14" radius={[4, 4, 0, 0]} opacity={0.85} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* ── RECENT WORKOUTS ─────────────────────────────────────────────── */}
      <Card>
        <h3 className="font-bold text-white mb-1">Recent Workouts</h3>
        <p className="text-gray-500 text-xs mb-5">Your last sessions from the AI backend</p>

        {historyLoading ? (
          <div className="space-y-3 animate-pulse">
            {[1,2,3].map(i => <div key={i} className="h-10 bg-surface rounded-lg" />)}
          </div>
        ) : recentWorkouts.length === 0 ? (
          <p className="text-gray-600 text-sm py-4 text-center">
            No sessions yet — run a detection on the Workout page first.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left">
                  <th className="pb-3 text-gray-500 font-medium text-xs uppercase tracking-wider">Exercise</th>
                  <th className="pb-3 text-gray-500 font-medium text-xs uppercase tracking-wider">Score</th>
                  <th className="pb-3 text-gray-500 font-medium text-xs uppercase tracking-wider">Posture</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {recentWorkouts.map((w) => (
                  <tr key={w.id} className="hover:bg-neon/[0.02] transition-colors">
                    <td className="py-3.5 font-medium text-white capitalize">{w.name}</td>
                    <td className="py-3.5">
                      <span className={`font-bold ${
                        w.score >= 85 ? "text-neon" : w.score >= 70 ? "text-yellow-400" : "text-red-400"
                      }`}>
                        {w.score}/100
                      </span>
                    </td>
                    <td className="py-3.5">
                      <PostureBadge status={w.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

// ── Mock data for all pages ───────────────────────────────────────────────────

export const userStats = {
  caloriesBurned: 1240,
  workoutsCompleted: 18,
  bmi: 22.4,
  streak: 7,
};

export const weeklyCalories = [
  { day: "Mon", calories: 320 },
  { day: "Tue", calories: 480 },
  { day: "Wed", calories: 210 },
  { day: "Thu", calories: 560 },
  { day: "Fri", calories: 390 },
  { day: "Sat", calories: 620 },
  { day: "Sun", calories: 180 },
];

export const workoutProgress = [
  { week: "W1", reps: 40 },
  { week: "W2", reps: 55 },
  { week: "W3", reps: 70 },
  { week: "W4", reps: 65 },
  { week: "W5", reps: 90 },
  { week: "W6", reps: 110 },
];

export const recentWorkouts = [
  { id: 1, name: "Deadlift",          reps: 12, sets: 4, score: 92, status: "correct" },
  { id: 2, name: "Squat",             reps: 15, sets: 3, score: 78, status: "warning" },
  { id: 3, name: "Lateral Raise",     reps: 12, sets: 3, score: 95, status: "correct" },
  { id: 4, name: "Romanian Deadlift", reps: 10, sets: 4, score: 61, status: "incorrect" },
];

// Diet plans keyed by goal
export const dietPlans = {
  lose: {
    goal: "Weight Loss",
    calories: 1600,
    meals: {
      breakfast: {
        title: "Breakfast",
        emoji: "🌅",
        items: ["Oatmeal with berries (300 kcal)", "2 boiled eggs (140 kcal)", "Green tea (0 kcal)"],
        total: "440 kcal",
      },
      lunch: {
        title: "Lunch",
        emoji: "☀️",
        items: ["Grilled chicken breast (250 kcal)", "Steamed broccoli & carrots (80 kcal)", "Brown rice (200 kcal)"],
        total: "530 kcal",
      },
      dinner: {
        title: "Dinner",
        emoji: "🌙",
        items: ["Baked salmon (300 kcal)", "Mixed green salad (60 kcal)", "Lemon water (0 kcal)"],
        total: "360 kcal",
      },
      snacks: {
        title: "Snacks",
        emoji: "🍎",
        items: ["Apple (80 kcal)", "Handful of almonds (100 kcal)", "Greek yogurt (90 kcal)"],
        total: "270 kcal",
      },
    },
    tips: ["Drink 3L water daily", "Avoid processed sugar", "Eat every 3–4 hours"],
  },
  gain: {
    goal: "Muscle Gain",
    calories: 2800,
    meals: {
      breakfast: {
        title: "Breakfast",
        emoji: "🌅",
        items: ["Protein pancakes (450 kcal)", "Banana + peanut butter (250 kcal)", "Whole milk (150 kcal)"],
        total: "850 kcal",
      },
      lunch: {
        title: "Lunch",
        emoji: "☀️",
        items: ["Double chicken rice bowl (700 kcal)", "Avocado (160 kcal)", "Whole wheat bread (120 kcal)"],
        total: "980 kcal",
      },
      dinner: {
        title: "Dinner",
        emoji: "🌙",
        items: ["Beef steak 200g (500 kcal)", "Sweet potato (180 kcal)", "Steamed veggies (60 kcal)"],
        total: "740 kcal",
      },
      snacks: {
        title: "Snacks",
        emoji: "🍎",
        items: ["Protein shake (200 kcal)", "Mixed nuts (180 kcal)", "Cottage cheese (100 kcal)"],
        total: "480 kcal",
      },
    },
    tips: ["Eat in a 300 kcal surplus", "1.8g protein per kg bodyweight", "Sleep 8 hours for recovery"],
  },
  maintain: {
    goal: "Maintenance",
    calories: 2200,
    meals: {
      breakfast: {
        title: "Breakfast",
        emoji: "🌅",
        items: ["Scrambled eggs on toast (380 kcal)", "Orange juice (110 kcal)", "Coffee (5 kcal)"],
        total: "495 kcal",
      },
      lunch: {
        title: "Lunch",
        emoji: "☀️",
        items: ["Turkey sandwich (420 kcal)", "Side salad (90 kcal)", "Sparkling water (0 kcal)"],
        total: "510 kcal",
      },
      dinner: {
        title: "Dinner",
        emoji: "🌙",
        items: ["Pasta with tomato sauce (500 kcal)", "Garlic bread (150 kcal)", "Herbal tea (0 kcal)"],
        total: "650 kcal",
      },
      snacks: {
        title: "Snacks",
        emoji: "🍎",
        items: ["Granola bar (190 kcal)", "Fruit smoothie (180 kcal)", "Dark chocolate (100 kcal)"],
        total: "470 kcal",
      },
    },
    tips: ["Balance macros: 40% carbs, 30% protein, 30% fat", "Stay active daily", "Hydrate consistently"],
  },
};

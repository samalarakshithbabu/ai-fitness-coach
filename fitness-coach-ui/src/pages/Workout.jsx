import React, { useState, useEffect, useRef } from "react";
import { Play, Square, Upload, RefreshCw, ChevronRight, Film, ImageIcon, Link } from "lucide-react";
import Button from "../components/Button";
import Card from "../components/Card";
import PostureBadge from "../components/PostureBadge";

const API_BASE = "http://localhost:8000";

const TIPS = [
  "Keep your core engaged throughout the movement.",
  "Breathe out on exertion, breathe in on the return.",
  "Control the eccentric (lowering) phase — don't drop the weight.",
  "Ensure full range of motion for maximum muscle activation.",
  "Rest 60–90 seconds between sets for optimal recovery.",
];

// Workflow steps shown during processing
const WORKFLOW_STEPS = [
  "Extracting frames…",
  "Running YOLO pose detection…",
  "Extracting keypoints…",
  "Classifying exercise…",
  "Generating report…",
];

export default function Workout() {
  const [videoSrc, setVideoSrc]       = useState(null);
  const [imageSrc, setImageSrc]       = useState(null);
  const [mediaType, setMediaType]     = useState(null); // "video" | "image" | "youtube"
  const [fileName, setFileName]       = useState("");
  const [youtubeUrl, setYoutubeUrl]   = useState("");
  const [showYtInput, setShowYtInput] = useState(false);

  const [detecting, setDetecting]     = useState(false);
  const [loading, setLoading]         = useState(false);
  const [workflowStep, setWorkflowStep] = useState(0);
  const [result, setResult]           = useState(null);
  const [error, setError]             = useState(null);

  const [tipIndex, setTipIndex]       = useState(0);
  const [dragOver, setDragOver]       = useState(false);

  const videoRef     = useRef(null);
  const fileInputRef = useRef(null);
  const fileRef      = useRef(null); // keep raw File for API upload

  // Rotate tips every 4s
  useEffect(() => {
    const t = setInterval(() => setTipIndex((i) => (i + 1) % TIPS.length), 4000);
    return () => clearInterval(t);
  }, []);

  // ── file handling ──────────────────────────────────────────────────────────
  const handleFile = (file) => {
    if (!file) return;
    fileRef.current = file;
    const url = URL.createObjectURL(file);
    setResult(null);
    setError(null);
    setDetecting(false);

    if (file.type.startsWith("video/")) {
      setVideoSrc(url);
      setImageSrc(null);
      setMediaType("video");
      setFileName(file.name);
    } else if (file.type.startsWith("image/")) {
      setImageSrc(url);
      setVideoSrc(null);
      setMediaType("image");
      setFileName(file.name);
    }
    setShowYtInput(false);
  };

  const onFileChange = (e) => handleFile(e.target.files[0]);
  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFile(e.dataTransfer.files[0]);
  };

  // ── workflow step animation ────────────────────────────────────────────────
  const runWorkflowAnimation = (totalMs) => {
    const stepMs = totalMs / WORKFLOW_STEPS.length;
    let step = 0;
    setWorkflowStep(0);
    const iv = setInterval(() => {
      step++;
      if (step >= WORKFLOW_STEPS.length) { clearInterval(iv); return; }
      setWorkflowStep(step);
    }, stepMs);
    return iv;
  };

  // ── API calls ──────────────────────────────────────────────────────────────
  const startDetection = async () => {
    if (!fileRef.current && !youtubeUrl) return;
    setLoading(true);
    setDetecting(true);
    setResult(null);
    setError(null);

    // Estimate processing time for animation (image ~3s, video ~15s)
    const estimatedMs = mediaType === "image" ? 3000 : 15000;
    const iv = runWorkflowAnimation(estimatedMs);

    try {
      let data;

      if (mediaType === "image") {
        // POST /predict-image
        const form = new FormData();
        form.append("file", fileRef.current);
        const res = await fetch(`${API_BASE}/predict-image`, { method: "POST", body: form });
        if (!res.ok) throw new Error((await res.json()).detail || "Server error");
        data = await res.json();

      } else if (mediaType === "video") {
        // POST /predict-video with file
        const form = new FormData();
        form.append("file", fileRef.current);
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 120000); // 2 min timeout
        try {
          const res = await fetch(`${API_BASE}/predict-video`, { method: "POST", body: form, signal: controller.signal });
          clearTimeout(timeout);
          if (!res.ok) throw new Error((await res.json()).detail || "Server error");
          data = await res.json();
        } catch (e) {
          clearTimeout(timeout);
          if (e.name === "AbortError") throw new Error("Request timed out. Try a shorter video.");
          throw e;
        }

      } else if (mediaType === "youtube") {
        // POST /predict-video with youtube_url
        const form = new FormData();
        form.append("youtube_url", youtubeUrl);
        const res = await fetch(`${API_BASE}/predict-video`, { method: "POST", body: form });
        if (!res.ok) throw new Error((await res.json()).detail || "Server error");
        data = await res.json();
      }

      clearInterval(iv);
      setWorkflowStep(WORKFLOW_STEPS.length - 1);
      setResult(data);
    } catch (err) {
      clearInterval(iv);
      setError(err.message || "Something went wrong. Is the backend running?");
    } finally {
      setLoading(false);
      setDetecting(false);
    }
  };

  const reset = () => {
    setVideoSrc(null);
    setImageSrc(null);
    setMediaType(null);
    setFileName("");
    setYoutubeUrl("");
    setShowYtInput(false);
    setResult(null);
    setError(null);
    setDetecting(false);
    setLoading(false);
    fileRef.current = null;
    if (fileInputRef.current) fileInputRef.current.value = "";
    videoRef.current?.pause();
  };

  // ── derived display values ─────────────────────────────────────────────────
  const hasMedia = videoSrc || imageSrc || (mediaType === "youtube" && youtubeUrl);
  const score    = result?.posture?.score ?? null;
  const scoreColor =
    score === null   ? "text-gray-500"
    : score >= 85    ? "text-neon"
    : score >= 70    ? "text-yellow-400"
    : "text-red-400";

  const postureStatus =
    score === null   ? null
    : score >= 85    ? "correct"
    : score >= 70    ? "warning"
    : "incorrect";

  return (
    <div className="min-h-screen pt-20 pb-12 px-4 max-w-7xl mx-auto">

      {/* Header */}
      <div className="mb-8 animate-fade-in">
        <p className="text-neon text-sm font-semibold uppercase tracking-widest mb-1">AI Detection</p>
        <h1 className="text-3xl font-black text-white">Posture Detection</h1>
        <p className="text-gray-500 text-sm mt-1">
          Upload a workout image/video or paste a YouTube link — the AI will analyze your form.
        </p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">

        {/* ── LEFT: media + controls ───────────────────────────────────── */}
        <div className="lg:col-span-2 space-y-4">

          {/* Drop zone */}
          {!hasMedia && !showYtInput && (
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`w-full aspect-video rounded-2xl border-2 border-dashed flex flex-col items-center justify-center cursor-pointer transition-all duration-300 ${
                dragOver
                  ? "border-neon bg-neon/10 shadow-[0_0_30px_#39ff1430]"
                  : "border-border bg-surface hover:border-neon/40 hover:bg-neon/5"
              }`}
            >
              <div className={`w-20 h-20 rounded-2xl border-2 flex items-center justify-center mb-4 transition-all ${
                dragOver ? "border-neon bg-neon/20" : "border-border bg-card"
              }`}>
                <Film size={36} className={dragOver ? "text-neon" : "text-gray-600"} />
              </div>
              <p className="font-semibold text-white mb-1">
                {dragOver ? "Drop your file here" : "Upload a workout image or video"}
              </p>
              <p className="text-gray-600 text-sm mb-4">Drag & drop or click to browse</p>
              <div className="flex gap-2 flex-wrap justify-center">
                <span className="text-xs text-gray-700 bg-card border border-border px-3 py-1.5 rounded-full flex items-center gap-1">
                  <Film size={11} /> MP4 · AVI · MOV
                </span>
                <span className="text-xs text-gray-700 bg-card border border-border px-3 py-1.5 rounded-full flex items-center gap-1">
                  <ImageIcon size={11} /> JPG · PNG · WEBP
                </span>
              </div>
              <input ref={fileInputRef} type="file" accept="image/*,video/*" className="hidden" onChange={onFileChange} />
            </div>
          )}

          {/* YouTube URL input */}
          {showYtInput && !hasMedia && (
            <div className="w-full aspect-video rounded-2xl border-2 border-border bg-surface flex flex-col items-center justify-center gap-4 px-8">
              <Link size={36} className="text-neon" />
              <p className="text-white font-semibold">Paste a YouTube URL</p>
              <input
                type="url"
                placeholder="https://youtube.com/watch?v=..."
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
                className="w-full max-w-md bg-card border border-border rounded-lg px-4 py-2.5 text-sm text-white placeholder-gray-600 outline-none focus:border-neon"
              />
              {youtubeUrl && (
                <Button size="sm" onClick={() => { setMediaType("youtube"); setShowYtInput(false); }}>
                  Use This URL
                </Button>
              )}
            </div>
          )}

          {/* Image preview */}
          {mediaType === "image" && imageSrc && (
            <div className={`relative w-full aspect-video rounded-2xl overflow-hidden border-2 bg-black flex items-center justify-center transition-all ${
              loading ? "border-neon shadow-[0_0_30px_#39ff1430]" : "border-border"
            }`}>
              <img src={imageSrc} alt="workout" className="max-w-full max-h-full object-contain" />
              {loading && <ScanOverlay />}
              {loading && <AnalyzingBadge />}
              {result && (
                <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between bg-black/75 backdrop-blur-sm rounded-xl px-4 py-2.5">
                  <span className="text-white font-bold text-sm">{result.exercise}</span>
                  <PostureBadge status={postureStatus} />
                </div>
              )}
            </div>
          )}

          {/* Video preview */}
          {mediaType === "video" && videoSrc && (
            <div className={`relative w-full aspect-video rounded-2xl overflow-hidden border-2 bg-black transition-all ${
              loading ? "border-neon shadow-[0_0_30px_#39ff1430]" : "border-border"
            }`}>
              <video ref={videoRef} src={videoSrc} className="w-full h-full object-contain" controls={!loading} />
              {loading && <ScanOverlay />}
              {loading && <AnalyzingBadge />}
              {result && (
                <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between bg-black/75 backdrop-blur-sm rounded-xl px-4 py-2.5">
                  <span className="text-white font-bold text-sm">{result.exercise}</span>
                  <PostureBadge status={postureStatus} />
                </div>
              )}
            </div>
          )}

          {/* YouTube placeholder */}
          {mediaType === "youtube" && (
            <div className={`relative w-full aspect-video rounded-2xl border-2 bg-surface flex flex-col items-center justify-center gap-3 transition-all ${
              loading ? "border-neon shadow-[0_0_30px_#39ff1430]" : "border-border"
            }`}>
              <Link size={40} className="text-neon" />
              <p className="text-white font-semibold text-sm truncate max-w-xs">{youtubeUrl}</p>
              {loading && <AnalyzingBadge />}
              {result && (
                <div className="flex items-center gap-3 bg-black/50 rounded-xl px-4 py-2">
                  <span className="text-white font-bold text-sm">{result.exercise}</span>
                  <PostureBadge status={postureStatus} />
                </div>
              )}
            </div>
          )}

          {/* Scan line keyframe */}
          <style>{`@keyframes scanLine { 0% { top: 0%; } 100% { top: 100%; } }`}</style>

          {/* File name pill */}
          {fileName && (
            <div className="flex items-center gap-2 bg-surface border border-border rounded-xl px-4 py-2.5">
              {mediaType === "image" ? <ImageIcon size={14} className="text-neon flex-shrink-0" /> : <Film size={14} className="text-neon flex-shrink-0" />}
              <span className="text-gray-300 text-sm truncate">{fileName}</span>
              <span className="ml-auto text-xs text-gray-600 bg-card border border-border px-2 py-0.5 rounded-full capitalize">{mediaType}</span>
            </div>
          )}

          {/* Workflow steps */}
          {loading && (
            <div className="bg-surface border border-neon/20 rounded-xl px-4 py-3 space-y-1.5">
              {WORKFLOW_STEPS.map((step, i) => (
                <div key={i} className={`flex items-center gap-2 text-xs transition-all ${
                  i < workflowStep ? "text-neon" : i === workflowStep ? "text-white" : "text-gray-700"
                }`}>
                  <span>{i < workflowStep ? "✓" : i === workflowStep ? "›" : "·"}</span>
                  {step}
                </div>
              ))}
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Control buttons */}
          <div className="flex gap-3 flex-wrap">
            {!hasMedia ? (
              <>
                <Button size="lg" onClick={() => fileInputRef.current?.click()} icon={Upload}>
                  Choose File
                </Button>
                <Button size="lg" variant="outline" onClick={() => { setShowYtInput(true); }} icon={Link}>
                  YouTube URL
                </Button>
              </>
            ) : !loading ? (
              <>
                <Button size="lg" onClick={startDetection} icon={Play} disabled={loading}>
                  {result ? "Re-Analyze" : "Start Detection"}
                </Button>
                <Button size="lg" variant="outline" onClick={() => fileInputRef.current?.click()} icon={Upload}>
                  Change File
                </Button>
              </>
            ) : (
              <Button size="lg" variant="danger" onClick={reset} icon={Square}>
                Cancel
              </Button>
            )}
            <Button size="lg" variant="ghost" onClick={reset} icon={RefreshCw}>Reset</Button>
          </div>
          {/* Single shared hidden file input */}
          <input ref={fileInputRef} type="file" accept="image/*,video/*" className="hidden" onChange={onFileChange} />

          {/* Tip ticker */}
          <div className="flex items-start gap-2 bg-surface border border-border rounded-xl px-4 py-3">
            <ChevronRight size={14} className="text-neon mt-0.5 flex-shrink-0" />
            <p className="text-gray-400 text-xs leading-relaxed">
              <span className="text-neon font-semibold">Tip: </span>{TIPS[tipIndex]}
            </p>
          </div>
        </div>

        {/* ── RIGHT: results panel ─────────────────────────────────────── */}
        <div className="space-y-4">

          {/* Detected exercise */}
          <Card glow={!!result}>
            <p className="text-gray-500 text-xs uppercase tracking-wider mb-2">Detected Exercise</p>
            <p className={`text-xl font-black capitalize ${result ? "text-white" : "text-gray-600"}`}>
              {result?.exercise ?? "—"}
            </p>
            {result?.confidence != null && (
              <p className="text-xs text-gray-500 mt-1">{Math.round(result.confidence * 100)}% confidence</p>
            )}
          </Card>

          {/* Frames analyzed (video only) */}
          {result?.frames_analyzed != null && (
            <Card>
              <p className="text-gray-500 text-xs uppercase tracking-wider mb-2">Frames Analyzed</p>
              <p className="text-3xl font-black text-neon neon-text">{result.frames_analyzed}</p>
              <p className="text-xs text-gray-600 mt-1">of {result.total_frames} total</p>
            </Card>
          )}

          {/* Posture score */}
          <Card>
            <p className="text-gray-500 text-xs uppercase tracking-wider mb-2">Posture Score</p>
            <div className="flex items-end gap-2 mb-3">
              <span className={`text-5xl font-black tabular-nums ${result ? scoreColor : "text-gray-700"}`}>
                {score ?? "—"}
              </span>
              {score != null && <span className="text-gray-600 text-sm mb-2">/100</span>}
            </div>
            {score != null && (
              <>
                <div className="w-full bg-border rounded-full h-1.5 mb-3">
                  <div
                    className={`h-1.5 rounded-full transition-all duration-700 ${
                      score >= 85 ? "bg-neon" : score >= 70 ? "bg-yellow-400" : "bg-red-400"
                    }`}
                    style={{ width: `${score}%` }}
                  />
                </div>
                <PostureBadge status={postureStatus} large />
              </>
            )}
          </Card>

          {/* Issues & suggestions */}
          {result?.posture?.issues?.length > 0 && (
            <Card>
              <p className="text-gray-500 text-xs uppercase tracking-wider mb-2">Issues Found</p>
              <ul className="space-y-1.5">
                {result.posture.issues.map((issue, i) => (
                  <li key={i} className="text-xs text-red-400 flex items-start gap-1.5">
                    <span className="mt-0.5">⚠</span>{issue}
                  </li>
                ))}
              </ul>
              {result.posture.suggestions?.length > 0 && (
                <>
                  <p className="text-gray-500 text-xs uppercase tracking-wider mt-3 mb-2">Suggestions</p>
                  <ul className="space-y-1.5">
                    {result.posture.suggestions.map((s, i) => (
                      <li key={i} className="text-xs text-neon flex items-start gap-1.5">
                        <span className="mt-0.5">→</span>{s}
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </Card>
          )}

          {/* No issues */}
          {result && result.posture?.issues?.length === 0 && (
            <Card>
              <p className="text-gray-500 text-xs uppercase tracking-wider mb-2">AI Feedback</p>
              <p className="text-neon text-sm font-semibold">Great form! No issues detected.</p>
            </Card>
          )}

          {/* Empty state */}
          {!result && !loading && (
            <Card>
              <p className="text-gray-500 text-xs uppercase tracking-wider mb-2">AI Feedback</p>
              <p className="text-gray-700 text-sm">
                {hasMedia ? "Press Start Detection to begin analysis." : "Upload an image or video to get started."}
              </p>
            </Card>
          )}

          {/* Supported exercises */}
          <Card>
            <p className="text-gray-500 text-xs uppercase tracking-wider mb-3">Supported Exercises</p>
            <ul className="space-y-1.5">
              {[
                "Barbell Biceps Curl", "Bench Press", "Chest Fly Machine",
                "Deadlift", "Decline Bench Press", "Front Squat",
                "Hammer Curl", "Hip Thrust", "Incline Bench Press",
                "Lat Pulldown", "Lateral Raise", "Leg Extension",
                "Leg Raises", "Plank", "Pull Up", "Push Up",
                "Romanian Deadlift", "Russian Twist", "Shoulder Press",
                "Squat", "Sumo Deadlift", "T Bar Row",
                "Tricep Dips", "Tricep Pushdown", "Zercher Squat",
              ].map((ex) => (
                <li key={ex} className="flex items-center gap-2 text-xs text-gray-400">
                  <span className="w-1.5 h-1.5 rounded-full bg-neon flex-shrink-0" />
                  {ex}
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </div>
  );
}

// ── small helper components ───────────────────────────────────────────────────

function ScanOverlay() {
  return (
    <div className="absolute inset-0 pointer-events-none">
      <div
        className="absolute left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-neon to-transparent opacity-60"
        style={{ animation: "scanLine 2.5s linear infinite" }}
      />
      {["top-3 left-3", "top-3 right-3", "bottom-3 left-3", "bottom-3 right-3"].map((pos, i) => (
        <div key={i} className={`absolute ${pos} w-6 h-6 border-neon opacity-70`}
          style={{
            borderTopWidth:    i < 2  ? "2px" : "0",
            borderBottomWidth: i >= 2 ? "2px" : "0",
            borderLeftWidth:   i % 2 === 0 ? "2px" : "0",
            borderRightWidth:  i % 2 === 1 ? "2px" : "0",
          }}
        />
      ))}
    </div>
  );
}

function AnalyzingBadge() {
  return (
    <div className="absolute top-4 left-4 flex items-center gap-1.5 bg-black/70 backdrop-blur-sm px-3 py-1.5 rounded-full">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neon opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-neon" />
      </span>
      <span className="text-white text-xs font-semibold">ANALYZING</span>
    </div>
  );
}

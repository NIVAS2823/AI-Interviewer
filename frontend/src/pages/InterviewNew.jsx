import React, { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { resumeAPI, interviewAPI } from "../lib/api";
import {
  Loader2,
  Video,
  AlertCircle,
  Briefcase,
  Sparkles,
} from "lucide-react";
import toast from "react-hot-toast";

export default function InterviewNew() {
  const navigate = useNavigate();
  const location = useLocation();

  const [resumes, setResumes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  const [formData, setFormData] = useState({
    resume_id: location.state?.resumeId || "",
    interview_type: "mixed",
    difficulty: "medium",
    max_questions: 5,
    job_description: "",
  });

  useEffect(() => {
    (async () => {
      try {
        const res = await resumeAPI.list();
        const completed = (res.data || []).filter(
          (r) => r.parsing_status === "completed"
        );
        setResumes(completed);

        if (!formData.resume_id && completed.length > 0) {
          setFormData((f) => ({
            ...f,
            resume_id: completed[0]._id || completed[0].id,
          }));
        }

        if (completed.length === 0) {
          toast.error("Please upload a resume first");
          navigate("/resumes");
        }
      } catch (err) {
        toast.error("Failed to load resumes");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((s) => ({ ...s, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.resume_id) {
      toast.error("Please select a resume");
      return;
    }

    setCreating(true);

    try {
      const payload = {
        resume_id: formData.resume_id,
        interview_type: formData.interview_type,
        difficulty: formData.difficulty,
        max_questions: Number(formData.max_questions),
        job_description: formData.job_description || undefined,
      };

      const res = await interviewAPI.create(payload);
      const id = res.data?.interview_id || res.data?.id;

      toast.success("Interview created!");
      navigate(`/interviews/${id}`);
    } catch (err) {
      /* toast via interceptor */
    } finally {
      setCreating(false);
    }
  };

  const jobDescCount = formData.job_description.length;
  const hasJD = jobDescCount > 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-10 h-10 animate-spin text-neon-primary" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-10 text-gray-200">
      {/* Header */}
      <div className="text-center">
        <div className="w-16 h-16 rounded-full bg-[#00f0ff20] border border-neon-primary/40 flex items-center justify-center mx-auto mb-4 shadow-[0_0_20px_var(--neon-primary)]">
          <Video className="w-8 h-8 text-neon-primary" />
        </div>

        <h1 className="text-3xl font-bold text-neon-primary drop-shadow-[0_0_8px_var(--neon-primary)]">
          Create New Interview
        </h1>
        <p className="text-gray-400 mt-2">
          Configure your personalized AI interview
        </p>
      </div>

      {/* Form Card */}
      <div className="bg-darkbg-card border border-white/10 rounded-xl p-8 shadow-xl space-y-8">
        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Resume Selector */}
          <div>
            <label className="text-sm text-gray-300">Select Resume *</label>
            <select
              name="resume_id"
              value={formData.resume_id}
              onChange={handleChange}
              className="w-full mt-2 bg-darkbg border border-white/10 rounded-lg p-3 focus:border-neon-primary focus:ring-1 focus:ring-neon-primary outline-none transition"
            >
              <option value="">Choose a resume...</option>
              {resumes.map((r) => (
                <option key={r._id || r.id} value={r._id || r.id}>
                  {r.file_name} — {r.completeness_score}%
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Questions are generated based on your resume.
            </p>
          </div>

          {/* Job Description */}
          <div>
            <div className="flex items-center justify-between">
              <label className="text-sm text-gray-300 flex items-center space-x-2">
                <Briefcase className="w-4 h-4" />
                <span>Job Description (optional)</span>
              </label>

              {hasJD && (
                <span className="text-xs flex items-center text-neon-green">
                  <Sparkles className="w-3 h-3 mr-1" />
                  Smart Questions ON
                </span>
              )}
            </div>

            <textarea
              name="job_description"
              value={formData.job_description}
              onChange={handleChange}
              rows={6}
              className="w-full mt-2 bg-darkbg border border-white/10 rounded-lg p-3 resize-none focus:border-neon-primary focus:ring-1 focus:ring-neon-primary outline-none"
              placeholder="Paste JD here for context-aware questions..."
            />

            <div className="flex justify-between mt-1 text-xs">
              <span className="text-gray-500">
                {hasJD
                  ? "AI will tailor questions to this role"
                  : "Add JD for more relevant questions"}
              </span>
              <span className="font-mono text-gray-500">
                {jobDescCount} / 2000
              </span>
            </div>
          </div>

          {/* Interview Type */}
          <div>
            <label className="text-sm text-gray-300">Interview Type *</label>

            <select
              name="interview_type"
              value={formData.interview_type}
              onChange={handleChange}
              className="w-full mt-2 bg-darkbg border border-white/10 rounded-lg p-3 focus:border-neon-primary focus:ring-1 focus:ring-neon-primary outline-none"
            >
              <option value="technical">Technical</option>
              <option value="behavioral">Behavioral</option>
              <option value="hr">HR Screening</option>
              <option value="mixed">Mixed (Recommended)</option>
            </select>

            <p className="text-xs text-gray-500 mt-2">
              {formData.interview_type === "mixed" &&
                "Balanced technical + behavioral + HR"}
              {formData.interview_type === "technical" &&
                "Focus on problem-solving & coding"}
              {formData.interview_type === "behavioral" &&
                "Focus on soft skills & past experiences"}
              {formData.interview_type === "hr" &&
                "Motivation, culture fit & expectations"}
            </p>
          </div>

          {/* Difficulty */}
          <div>
            <label className="text-sm text-gray-300">Difficulty *</label>

            <div className="grid grid-cols-3 gap-4 mt-3">
              {["easy", "medium", "hard"].map((lvl) => {
                const active = formData.difficulty === lvl;
                return (
                  <label
                    key={lvl}
                    className={`p-4 rounded-lg text-center cursor-pointer border transition ${
                      active
                        ? "border-neon-primary bg-[#00f0ff10] shadow-[0_0_12px_var(--neon-primary)]"
                        : "border-white/10 hover:border-white/20"
                    }`}
                  >
                    <input
                      type="radio"
                      name="difficulty"
                      value={lvl}
                      checked={active}
                      onChange={handleChange}
                      className="sr-only"
                    />
                    <span className="capitalize text-gray-200">{lvl}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {/* Number of Questions */}
          <div>
            <label className="text-sm text-gray-300">
              Number of Questions: {formData.max_questions}
            </label>

            <input
              type="range"
              name="max_questions"
              min="3"
              max="10"
              value={formData.max_questions}
              onChange={handleChange}
              className="w-full accent-neon-primary mt-2"
            />

            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>3 (Quick)</span>
              <span>10 (Comprehensive)</span>
            </div>
          </div>

          {/* Info Box */}
          <div className="bg-[#0f1a25] border border-blue-500/30 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <AlertCircle className="w-5 h-5 text-blue-400" />
              <div className="text-sm text-gray-300">
                <p className="font-medium mb-1">What to expect:</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>AI will ask {formData.max_questions} personalized questions</li>
                  <li>
                    Questions tailored {hasJD ? "to the job role" : "to your resume"}
                  </li>
                  <li>Interview lasts 15–25 mins</li>
                  <li>Instant evaluation after completion</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={creating || !formData.resume_id}
            className="w-full py-3 rounded-lg bg-neon-primary text-black text-lg font-semibold shadow-[0_0_20px_var(--neon-primary)] hover:shadow-[0_0_30px_var(--neon-primary)] active:scale-95 transition flex items-center justify-center"
          >
            {creating ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Creating Interview...
              </>
            ) : (
              <>
                <Video className="w-5 h-5 mr-2" />
                Create Interview
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

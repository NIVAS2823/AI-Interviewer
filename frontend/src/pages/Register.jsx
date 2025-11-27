import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authAPI } from "../lib/api";
import { useAuthStore } from "../store/authStore";
import toast from "react-hot-toast";
import { Lock, Mail, User, Loader2, Briefcase } from "lucide-react";

export default function Register() {
  const [formData, setFormData] = useState({
    email: "",
    name: "",
    password: "",
    role: "job_seeker",
  });
  const [loading, setLoading] = useState(false);

  const { setAuth } = useAuthStore();
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await authAPI.register(formData);
      const { access_token, user } = response.data;

      setAuth(user, access_token);
      toast.success("Account created successfully!");
      navigate("/dashboard");
    } catch (error) {
      console.error("Registration error:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10 bg-darkbg">
      <div className="max-w-md w-full bg-darkbg-card/80 border border-white/10 backdrop-blur-xl shadow-[0_0_20px_rgba(0,0,0,0.4)] rounded-2xl p-8">
        {/* HEADER */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-neon-primary drop-shadow-[0_0_12px_var(--neon-primary)] mb-2">
            Create Account
          </h1>
          <p className="text-gray-400">
            Start practicing interviews with AI today
          </p>
        </div>

        {/* FORM */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* NAME */}
          <div>
            <label className="text-gray-300 font-medium text-sm flex items-center gap-2 mb-1">
              <User className="w-4 h-4 text-neon-primary" />
              Full Name
            </label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              placeholder="John Doe"
              required
              minLength={2}
              className="w-full px-4 py-3 bg-darkbg-card border border-white/10 rounded-lg 
              focus:border-neon-primary focus:ring-2 focus:ring-neon-primary/40
              text-gray-200 placeholder-gray-500 outline-none transition-all"
            />
          </div>

          {/* EMAIL */}
          <div>
            <label className="text-gray-300 font-medium text-sm flex items-center gap-2 mb-1">
              <Mail className="w-4 h-4 text-neon-primary" />
              Email Address
            </label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="you@example.com"
              required
              className="w-full px-4 py-3 bg-darkbg-card border border-white/10 rounded-lg 
              focus:border-neon-primary focus:ring-2 focus:ring-neon-primary/40
              text-gray-200 placeholder-gray-500 outline-none transition-all"
            />
          </div>

          {/* PASSWORD */}
          <div>
            <label className="text-gray-300 font-medium text-sm flex items-center gap-2 mb-1">
              <Lock className="w-4 h-4 text-neon-primary" />
              Password
            </label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="••••••••"
              required
              minLength={8}
              className="w-full px-4 py-3 bg-darkbg-card border border-white/10 rounded-lg 
              focus:border-neon-primary focus:ring-2 focus:ring-neon-primary/40
              text-gray-200 placeholder-gray-500 outline-none transition-all"
            />
            <p className="text-xs text-gray-500 mt-1">
              Min 8 characters, include uppercase, lowercase, and number
            </p>
          </div>

          {/* ROLE */}
          <div>
            <label className="text-gray-300 font-medium text-sm flex items-center gap-2 mb-1">
              <Briefcase className="w-4 h-4 text-neon-primary" />
              I am a...
            </label>
            <select
              name="role"
              value={formData.role}
              onChange={handleChange}
              className="w-full px-4 py-3 bg-darkbg-card border border-white/10 rounded-lg
              focus:border-neon-primary focus:ring-2 focus:ring-neon-primary/40
              text-gray-200 outline-none transition-all"
            >
              <option value="job_seeker">Job Seeker</option>
              <option value="hr_professional">HR Professional</option>
            </select>
          </div>

          {/* SUBMIT BUTTON */}
          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center px-6 py-3 rounded-xl font-semibold 
            bg-neon-primary text-black shadow-[0_0_15px_var(--neon-primary)]
            hover:shadow-[0_0_25px_var(--neon-primary)]
            transition-all active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Creating account...
              </>
            ) : (
              "Create Account"
            )}
          </button>
        </form>

        {/* FOOTER */}
        <div className="mt-6 text-center text-sm text-gray-400">
          Already have an account?{" "}
          <Link
            to="/login"
            className="text-neon-primary hover:underline"
          >
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}

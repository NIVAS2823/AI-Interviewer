import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authAPI } from "../lib/api";
import { useAuthStore } from "../store/authStore";
import toast from "react-hot-toast";
import { Lock, Mail, Loader2 } from "lucide-react";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const { setAuth } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await authAPI.login({ email, password });
      const { access_token, user } = response.data;

      setAuth(user, access_token);
      toast.success("Login successful!");
      navigate("/dashboard");
    } catch (error) {
      console.error("Login error:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10 bg-darkbg">
      <div className="max-w-md w-full bg-darkbg-card/80 border border-white/10 rounded-2xl p-8 shadow-[0_0_20px_rgba(0,0,0,0.4)] backdrop-blur-xl">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-neon-primary drop-shadow-[0_0_12px_var(--neon-primary)] mb-2">
            Welcome Back
          </h1>
          <p className="text-gray-400">
            Sign in to continue your interview practice
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Email Field */}
          <div>
            <label className="text-gray-300 font-medium text-sm flex items-center gap-2 mb-1">
              <Mail className="w-4 h-4 text-neon-primary" />
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              className="w-full px-4 py-3 bg-darkbg-card border border-white/10 rounded-lg
              focus:border-neon-primary focus:ring-2 focus:ring-neon-primary/40 
              text-gray-200 placeholder-gray-500 outline-none transition-all"
            />
          </div>

          {/* Password Field */}
          <div>
            <label className="text-gray-300 font-medium text-sm flex items-center gap-2 mb-1">
              <Lock className="w-4 h-4 text-neon-primary" />
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              className="w-full px-4 py-3 bg-darkbg-card border border-white/10 rounded-lg
              focus:border-neon-primary focus:ring-2 focus:ring-neon-primary/40 
              text-gray-200 placeholder-gray-500 outline-none transition-all"
            />
          </div>

          {/* Submit Button */}
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
                Signing in...
              </>
            ) : (
              "Sign In"
            )}
          </button>
        </form>

        {/* Footer */}
        <div className="mt-6 text-center text-sm text-gray-400">
          Don’t have an account?{" "}
          <Link
            to="/register"
            className="text-neon-primary hover:underline"
          >
            Sign up for free
          </Link>
        </div>
      </div>
    </div>
  );
}

import React from "react";
import { Link } from "react-router-dom";
import {
  Video,
  Zap,
  TrendingUp,
  Shield,
  ArrowRight,
  CheckCircle,
} from "lucide-react";

export default function Landing() {
  const features = [
    {
      icon: Video,
      title: "AI-Powered Video Interviews",
      description:
        "Practice with realistic AI interviewers featuring avatars and natural conversation.",
    },
    {
      icon: Zap,
      title: "Instant Feedback",
      description:
        "Get detailed evaluation and scores immediately after your interview.",
    },
    {
      icon: TrendingUp,
      title: "Track Progress",
      description:
        "Monitor your improvement over time with detailed analytics.",
    },
    {
      icon: Shield,
      title: "Completely Free",
      description:
        "Built with free and open-source tools. No hidden costs or subscriptions.",
    },
  ];

  const benefits = [
    "Unlimited practice interviews",
    "AI-powered question generation",
    "Detailed performance analysis",
    "Resume parsing & optimization",
    "Multi-category scoring",
    "Personalized improvement tips",
  ];

  return (
    <div className="min-h-screen bg-darkbg text-gray-200">
      {/* HERO SECTION */}
      <section className="relative py-24 px-4 bg-gradient-to-br from-[#00f0ff22] to-[#ff00e622] backdrop-blur-md border-b border-white/10">
        <div className="max-w-6xl mx-auto text-center animate-fade-in">
          <h1 className="text-5xl md:text-6xl font-extrabold mb-6 text-neon-primary drop-shadow-[0_0_10px_var(--neon-primary)]">
            Ace Your Next Interview
          </h1>

          <p className="text-xl md:text-2xl text-gray-300 mb-10 max-w-3xl mx-auto">
            Practice with AI-powered video interviews. Get instant feedback.  
            Improve your skills. Land your dream job.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            {/* Primary CTA */}
            <Link
              to="/register"
              className="px-8 py-4 rounded-xl font-semibold text-lg
              bg-neon-primary text-black shadow-[0_0_15px_var(--neon-primary)]
              hover:shadow-[0_0_25px_var(--neon-primary)] transition-all active:scale-95"
            >
              Get Started Free
              <ArrowRight className="inline ml-2 w-5 h-5" />
            </Link>

            {/* Secondary CTA */}
            <Link
              to="/login"
              className="px-8 py-4 rounded-xl font-semibold text-lg border border-neon-primary
              text-neon-primary hover:bg-neon-primary hover:text-black transition-all active:scale-95"
            >
              Sign In
            </Link>
          </div>
        </div>
      </section>

      {/* FEATURES SECTION */}
      <section className="py-20 px-4 bg-darkbg">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-100 mb-4">
              How It Works
            </h2>
            <p className="text-xl text-gray-400">
              Simple, powerful, and completely free
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => {
              const Icon = feature.icon;

              return (
                <div
                  key={index}
                  className="p-6 rounded-2xl bg-darkbg-card border border-white/10
                  hover:border-neon-primary hover:shadow-[0_0_20px_var(--neon-primary)]
                  transition-all text-center animate-slide-up"
                  style={{ animationDelay: `${index * 120}ms` }}
                >
                  <div className="inline-flex items-center justify-center w-16 h-16 
                  bg-[#00f0ff10] rounded-full mb-4 border border-neon-primary/60">
                    <Icon className="w-9 h-9 text-neon-primary" />
                  </div>

                  <h3 className="text-xl font-semibold text-white mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-gray-400">{feature.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* BENEFITS SECTION */}
      <section className="py-20 px-4 bg-darkbg">
        <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-12 items-center">
          {/* LEFT */}
          <div>
            <h2 className="text-4xl font-bold text-gray-100 mb-6">
              Everything You Need to Succeed
            </h2>
            <p className="text-lg text-gray-400 mb-8">
              Our AI-powered platform provides comprehensive interview
              preparation with features designed to boost your confidence and performance.
            </p>

            <div className="space-y-4">
              {benefits.map((benefit, index) => (
                <div key={index} className="flex items-start space-x-3">
                  <CheckCircle className="w-6 h-6 text-neon-green flex-shrink-0 mt-0.5" />
                  <span className="text-gray-300">{benefit}</span>
                </div>
              ))}
            </div>
          </div>

          {/* RIGHT – METRICS CARD */}
          <div className="bg-darkbg-card border border-white/10 p-8 rounded-2xl shadow-[0_0_20px_rgba(0,0,0,0.3)]">
            <div className="space-y-8">
              <div className="border-l-4 border-neon-primary pl-4">
                <div className="text-4xl font-bold text-white mb-1">100%</div>
                <div className="text-gray-400">Free Forever</div>
              </div>

              <div className="border-l-4 border-neon-green pl-4">
                <div className="text-4xl font-bold text-white mb-1">∞</div>
                <div className="text-gray-400">Unlimited Interviews</div>
              </div>

              <div className="border-l-4 border-neon-secondary pl-4">
                <div className="text-4xl font-bold text-white mb-1">AI</div>
                <div className="text-gray-400">Powered by Groq & LLaMA</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FINAL CTA SECTION */}
      <section className="py-20 px-4 bg-[#00f0ff15] border-t border-white/10">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl font-bold text-white mb-6">
            Ready to Start Practicing?
          </h2>
          <p className="text-xl text-gray-300 mb-8">
            Join thousands of job seekers improving their interview skills with AI
          </p>

          <Link
            to="/register"
            className="px-8 py-4 bg-neon-primary text-black rounded-xl font-semibold text-lg
            shadow-[0_0_15px_var(--neon-primary)] hover:shadow-[0_0_25px_var(--neon-primary)]
            transition-all active:scale-95"
          >
            Create Free Account
            <ArrowRight className="inline ml-2 w-5 h-5" />
          </Link>
        </div>
      </section>
    </div>
  );
}

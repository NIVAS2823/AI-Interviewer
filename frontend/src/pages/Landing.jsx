import React from 'react';
import { Link } from 'react-router-dom';
import { Video, Zap, TrendingUp, Shield, ArrowRight, CheckCircle } from 'lucide-react';

export default function Landing() {

  console.log("On landing page")
  const features = [
    {
      icon: Video,
      title: 'AI-Powered Video Interviews',
      description: 'Practice with realistic AI interviewers featuring avatars and natural conversation.',
    },
    {
      icon: Zap,
      title: 'Instant Feedback',
      description: 'Get detailed evaluation and scores immediately after your interview.',
    },
    {
      icon: TrendingUp,
      title: 'Track Progress',
      description: 'Monitor your improvement over time with detailed analytics.',
    },
    {
      icon: Shield,
      title: 'Completely Free',
      description: 'Built with free and open-source tools. No hidden costs or subscriptions.',
    },
  ];

  const benefits = [
    'Unlimited practice interviews',
    'AI-powered question generation',
    'Detailed performance analysis',
    'Resume parsing & optimization',
    'Multi-category scoring',
    'Personalized improvement tips',
  ];

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative bg-gradient-to-br from-primary-600 to-primary-800 text-white py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center animate-fade-in">
            <h1 className="text-5xl md:text-6xl font-bold mb-6">
              Ace Your Next Interview
            </h1>
            <p className="text-xl md:text-2xl text-primary-100 mb-8 max-w-3xl mx-auto">
              Practice with AI-powered video interviews. Get instant feedback.
              Improve your skills. Land your dream job.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                to="/register"
                className="inline-flex items-center justify-center px-8 py-4 bg-white text-primary-700 rounded-lg font-semibold text-lg hover:bg-primary-50 transition-all shadow-lg hover:shadow-xl active:scale-95"
              >
                Get Started Free
                <ArrowRight className="ml-2 w-5 h-5" />
              </Link>
              <Link
                to="/login"
                className="inline-flex items-center justify-center px-8 py-4 border-2 border-white text-white rounded-lg font-semibold text-lg hover:bg-white hover:text-primary-700 transition-all"
              >
                Sign In
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-4 bg-white">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              How It Works
            </h2>
            <p className="text-xl text-gray-600">
              Simple, powerful, and completely free
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <div
                  key={index}
                  className="text-center p-6 rounded-xl hover:shadow-lg transition-shadow animate-slide-up"
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-full mb-4">
                    <Icon className="w-8 h-8 text-primary-600" />
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-gray-600">{feature.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="py-20 px-4 bg-gray-50">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-4xl font-bold text-gray-900 mb-6">
                Everything You Need to Succeed
              </h2>
              <p className="text-lg text-gray-600 mb-8">
                Our AI-powered platform provides comprehensive interview
                preparation with features designed to boost your confidence
                and performance.
              </p>
              <div className="space-y-4">
                {benefits.map((benefit, index) => (
                  <div key={index} className="flex items-start space-x-3">
                    <CheckCircle className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">{benefit}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white p-8 rounded-2xl shadow-xl">
              <div className="space-y-6">
                <div className="border-l-4 border-primary-500 pl-4">
                  <div className="text-4xl font-bold text-gray-900 mb-1">
                    100%
                  </div>
                  <div className="text-gray-600">Free Forever</div>
                </div>
                <div className="border-l-4 border-green-500 pl-4">
                  <div className="text-4xl font-bold text-gray-900 mb-1">
                    ∞
                  </div>
                  <div className="text-gray-600">Unlimited Interviews</div>
                </div>
                <div className="border-l-4 border-blue-500 pl-4">
                  <div className="text-4xl font-bold text-gray-900 mb-1">
                    AI
                  </div>
                  <div className="text-gray-600">Powered by Groq & LLaMA</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>


      <button 
  onClick={async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/health');
      const data = await response.json();
      alert('✅ Backend Connected!\n' + JSON.stringify(data, null, 2));
    } catch (error) {
      alert('❌ Backend connection failed!\n' + error.message);
    }
  }}
  className="bg-blue-500 text-white px-4 py-2 rounded"
>
  Test Backend Connection
</button>

      {/* CTA Section */}
      <section className="py-20 px-4 bg-primary-600 text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl font-bold mb-6">
            Ready to Start Practicing?
          </h2>
          <p className="text-xl text-primary-100 mb-8">
            Join thousands of job seekers improving their interview skills with AI
          </p>
          <Link
            to="/register"
            className="inline-flex items-center justify-center px-8 py-4 bg-white text-primary-700 rounded-lg font-semibold text-lg hover:bg-primary-50 transition-all shadow-lg hover:shadow-xl active:scale-95"
          >
            Create Free Account
            <ArrowRight className="ml-2 w-5 h-5" />
          </Link>
        </div>
      </section>
    </div>
  );
}
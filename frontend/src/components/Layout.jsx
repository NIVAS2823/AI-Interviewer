import React from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import { LogOut, User, FileText, Video, BarChart3 } from "lucide-react";
import toast from "react-hot-toast";

export default function Layout({ children }) {
  const { user, isAuthenticated, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    toast.success("Logged out successfully");
    navigate("/login");
  };

  const navItems = [
    { name: "Dashboard", path: "/dashboard", icon: BarChart3 },
    { name: "Resumes", path: "/resumes", icon: FileText },
    { name: "Interviews", path: "/interviews", icon: Video },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-darkbg text-gray-200">
      {/* HEADER */}
      <header className="bg-darkbg-card border-b border-white/10 backdrop-blur-xl sticky top-0 z-50 shadow-[0_2px_20px_rgba(0,0,0,0.4)]">
        <div className="max-w-7xl mx-auto px-4 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* LOGO */}
            <Link to="/" className="flex items-center space-x-2 group">
              <div
                className="w-9 h-9 rounded-lg flex items-center justify-center 
                bg-[#00f0ff30] border border-neon-primary/40 
                shadow-[0_0_10px_var(--neon-primary)] group-hover:shadow-[0_0_15px_var(--neon-primary)] transition"
              >
                <Video className="w-5 h-5 text-neon-primary" />
              </div>
              <span className="text-xl font-bold text-neon-primary drop-shadow-[0_0_8px_var(--neon-primary)]">
                AI Interviewer
              </span>
            </Link>

            {/* NAVIGATION */}
            {isAuthenticated && (
              <nav className="hidden md:flex space-x-3">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = location.pathname.startsWith(item.path);

                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`flex items-center px-4 py-2 rounded-lg font-medium transition-all 
                        ${
                          isActive
                            ? "text-black bg-neon-primary shadow-[0_0_15px_var(--neon-primary)]"
                            : "text-gray-300 hover:text-neon-primary hover:bg-white/5 border border-transparent hover:border-neon-primary/40"
                        }`}
                    >
                      <Icon className="w-4 h-4 mr-2" />
                      {item.name}
                    </Link>
                  );
                })}
              </nav>
            )}

            {/* USER MENU */}
            <div className="flex items-center space-x-4">
              {isAuthenticated ? (
                <>
                  <div className="hidden sm:flex items-center space-x-2 text-sm text-gray-300">
                    <User className="w-4 h-4 text-neon-primary" />
                    <span>{user?.name}</span>
                  </div>

                  <button
                    onClick={handleLogout}
                    className="flex items-center px-4 py-2 rounded-lg text-gray-300 
                    hover:bg-white/5 hover:text-neon-primary border border-transparent hover:border-neon-primary/40 
                    transition-all"
                  >
                    <LogOut className="w-4 h-4 mr-2" />
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <Link
                    to="/login"
                    className="text-gray-300 hover:text-neon-primary transition"
                  >
                    Login
                  </Link>
                  <Link
                    to="/register"
                    className="px-4 py-2 bg-neon-primary text-black rounded-lg font-semibold shadow-[0_0_12px_var(--neon-primary)]
                    hover:shadow-[0_0_20px_var(--neon-primary)] transition"
                  >
                    Sign Up
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* MAIN CONTENT */}
      <main className="max-w-7xl mx-auto w-full px-4 lg:px-8 py-10">
        {children}
      </main>

      {/* FOOTER */}
      <footer className="bg-darkbg-card border-t border-white/10 mt-auto py-6">
        <div className="max-w-7xl mx-auto text-center text-gray-400 text-sm">
          © 2025 AI Interviewer Platform • Built with ❤️ using open-source tools
        </div>
      </footer>
    </div>
  );
}

import React, { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { resumeAPI } from "../lib/api";
import {
  Loader2,
  ArrowLeft,
  Briefcase,
  GraduationCap,
  Award,
  Code,
} from "lucide-react";
import toast from "react-hot-toast";
import { formatDate } from "../lib/utils";

export default function ResumeDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [resume, setResume] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    loadResume();
  }, [id]);

  const loadResume = async () => {
    try {
      const response = await resumeAPI.get(id);
      setResume(response.data);
    } catch (error) {
      toast.error("Failed to load resume");
      navigate("/resumes");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-neon-primary" />
      </div>
    );
  }

  if (!resume) return null;

  const { parsed_data } = resume;
  const skills = parsed_data?.skills || {};

  return (
    <div className="space-y-10 text-gray-200">
      {/* BACK */}
      <Link
        to="/resumes"
        className="inline-flex items-center text-gray-400 hover:text-neon-primary transition mb-2"
      >
        <ArrowLeft className="w-4 h-4 mr-2" /> Back to Resumes
      </Link>

      {/* HEADER */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-neon-primary drop-shadow-[0_0_10px_var(--neon-primary)]">
            {resume.file_name}
          </h1>
          <p className="text-gray-400 mt-2">
            Uploaded {formatDate(resume.uploaded_at)}
          </p>
        </div>

        <Link
          to="/interviews/new"
          state={{ resumeId: resume._id || resume.id }}
          className="px-5 py-2 bg-neon-primary text-black rounded-lg font-semibold shadow-[0_0_15px_var(--neon-primary)]
          hover:shadow-[0_0_25px_var(--neon-primary)] transition"
        >
          Start Interview
        </Link>
      </div>

      {/* COMPLETENESS SCORE */}
      <div className="bg-darkbg-card border border-white/10 rounded-xl p-8 shadow-md text-center">
        <p className="text-gray-400 mb-2">Completeness Score</p>
        <p className="text-5xl font-bold text-neon-primary drop-shadow-[0_0_10px_var(--neon-primary)]">
          {resume.completeness_score}%
        </p>
      </div>

      {/* PARSED DATA */}
      {parsed_data ? (
        <div className="grid gap-6">

          {/* PERSONAL INFO */}
          {(parsed_data.name ||
            parsed_data.email ||
            parsed_data.phone) && (
            <div className="bg-darkbg-card border border-white/10 p-6 rounded-xl shadow">
              <h2 className="text-xl font-bold mb-4 text-neon-primary">
                Personal Information
              </h2>
              {parsed_data.name && (
                <p className="text-gray-300">
                  <strong>Name:</strong> {parsed_data.name}
                </p>
              )}
              {parsed_data.email && (
                <p className="text-gray-300">
                  <strong>Email:</strong> {parsed_data.email}
                </p>
              )}
              {parsed_data.phone && (
                <p className="text-gray-300">
                  <strong>Phone:</strong> {parsed_data.phone}
                </p>
              )}
            </div>
          )}

          {/* SUMMARY */}
          {parsed_data.summary && (
            <div className="bg-darkbg-card border border-white/10 p-6 rounded-xl shadow">
              <h2 className="text-xl font-bold text-neon-primary mb-4">
                Summary
              </h2>
              <p className="text-gray-300">{parsed_data.summary}</p>
            </div>
          )}

          {/* SKILLS BLOCK (NEW STRUCTURE) */}
          {(skills.keywords?.length ||
            skills.technical?.length ||
            skills.soft?.length ||
            skills.tools?.length) > 0 && (
            <div className="bg-darkbg-card border border-white/10 p-6 rounded-xl shadow">
              <div className="flex items-center space-x-2 mb-4">
                <Code className="w-5 h-5 text-neon-primary" />
                <h2 className="text-xl font-bold text-neon-primary">Skills</h2>
              </div>

              {/* KEYWORDS */}
              {skills.keywords?.length > 0 && (
                <Section title="Keywords" items={skills.keywords} />
              )}

              {/* TECHNICAL */}
              {skills.technical?.length > 0 && (
                <Section title="Technical Skills" items={skills.technical} />
              )}

              {/* SOFT */}
              {skills.soft?.length > 0 && (
                <Section title="Soft Skills" items={skills.soft} />
              )}

              {/* TOOLS */}
              {skills.tools?.length > 0 && (
                <Section title="Tools" items={skills.tools} />
              )}
            </div>
          )}

          {/* EXPERIENCE */}
          {parsed_data.experience?.length > 0 && (
            <div className="bg-darkbg-card border border-white/10 p-6 rounded-xl shadow">
              <div className="flex items-center space-x-2 mb-4">
                <Briefcase className="w-5 h-5 text-neon-primary" />
                <h2 className="text-xl font-bold text-neon-primary">
                  Experience
                </h2>
              </div>
              {parsed_data.experience.map((exp, i) => (
                <div
                  key={i}
                  className="border-l-2 border-neon-primary/40 pl-4 mb-4"
                >
                  <h3 className="font-semibold text-white">{exp.role}</h3>
                  <p className="text-gray-300">{exp.company}</p>
                  <p className="text-sm text-gray-400">{exp.duration}</p>
                </div>
              ))}
            </div>
          )}

          {/* EDUCATION */}
          {parsed_data.education?.length > 0 && (
            <div className="bg-darkbg-card border border-white/10 p-6 rounded-xl shadow">
              <div className="flex items-center space-x-2 mb-4">
                <GraduationCap className="w-5 h-5 text-neon-primary" />
                <h2 className="text-xl font-bold text-neon-primary">
                  Education
                </h2>
              </div>
              {parsed_data.education.map((edu, i) => (
                <div key={i} className="mb-4">
                  <h3 className="font-semibold text-white">
                    {edu.degree} in {edu.field}
                  </h3>
                  <p className="text-gray-300">{edu.institution}</p>
                </div>
              ))}
            </div>
          )}

          {/* CERTIFICATIONS */}
          {parsed_data.certifications?.length > 0 && (
            <div className="bg-darkbg-card border border-white/10 p-6 rounded-xl shadow">
              <div className="flex items-center space-x-2 mb-4">
                <Award className="w-5 h-5 text-neon-primary" />
                <h2 className="text-xl font-bold text-neon-primary">
                  Certifications
                </h2>
              </div>
              <ul className="list-disc ml-5 text-gray-300">
                {parsed_data.certifications.map((cert, i) => (
                  <li key={i}>{cert}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <div className="text-center text-gray-500">Resume not parsed yet.</div>
      )}
    </div>
  );
}

/* Helper Section Component */
function Section({ title, items }) {
  return (
    <div className="mb-4">
      <h4 className="font-semibold text-neon-primary mb-2">{title}</h4>
      <div className="flex flex-wrap gap-2">
        {items.map((item, i) => (
          <span
            key={i}
            className="px-3 py-1 bg-white/10 border border-neon-primary/40 text-neon-primary rounded-full text-sm shadow-[0_0_8px_var(--neon-primary)]"
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

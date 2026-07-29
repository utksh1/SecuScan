import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence, type Variants } from "framer-motion";
import { getScanTemplates, type ScanTemplate } from "../api";

const categories = [
  { value: "", label: "ALL_TEMPLATES", icon: "dashboard" },
  { value: "network", label: "NETWORK", icon: "lan" },
  { value: "web", label: "WEB", icon: "language" },
  { value: "reconnaissance", label: "RECONNAISSANCE", icon: "travel_explore" },
  { value: "vulnerability", label: "VULNERABILITY", icon: "bug_report" },
  { value: "compliance", label: "COMPLIANCE", icon: "verified" },
];

const complexityColors: Record<string, string> = {
  basic: "bg-rag-green text-black",
  intermediate: "bg-rag-amber text-black",
  advanced: "bg-rag-red text-black",
};

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06 },
  },
};

const cardVariants: Variants = {
  hidden: { opacity: 0, y: 24, scale: 0.95 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring", stiffness: 200, damping: 20 },
  },
};

export default function ScanTemplates() {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState<ScanTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState("");

  useEffect(() => {
    loadTemplates();
  }, [activeCategory]);

  async function loadTemplates() {
    setLoading(true);
    try {
      const data = await getScanTemplates(activeCategory || undefined);
      setTemplates(data.templates || []);
    } catch (err) {
      console.error("Failed to load scan templates:", err);
    } finally {
      setLoading(false);
    }
  }

  function handleUseTemplate(template: ScanTemplate) {
    navigate(`/toolkit?template=${template.id}`);
  }

  return (
    <div className="min-h-screen bg-charcoal-dark text-silver p-6 md:p-12 space-y-12">
      {/* Neo-Brutalist Header */}
      <header className="relative flex flex-col md:flex-row justify-between items-start md:items-end gap-8 pb-12 border-b-4 border-silver-bright/10">
        <div className="space-y-4">
          <div className="bg-rag-blue text-black px-4 py-1 text-xs font-black uppercase tracking-widest inline-block shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
            Scan_Templates_v1.0
          </div>
          <h1 className="text-6xl md:text-8xl font-black text-silver-bright uppercase tracking-tighter leading-none italic">
            Scan{" "}
            <span
              className="text-transparent stroke-white"
              style={{ WebkitTextStroke: "1px var(--accent-silver-bright)" }}
            >
              Templates
            </span>
          </h1>
          <p className="text-sm font-mono text-silver/40 uppercase tracking-widest italic flex items-center gap-4">
            Total_Templates: {templates.length} //{" "}
            {loading ? "LOADING..." : "READY"}
            <span
              className={`w-2 h-2 rounded-full ${loading ? "bg-rag-amber animate-pulse" : "bg-rag-green"}`}
            ></span>
          </p>
        </div>
      </header>

      {/* Category Filter Chips */}
      <section className="bg-charcoal border-4 border-black p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
        <div className="flex flex-wrap items-center gap-4">
          {categories.map((cat) => (
            <button
              key={cat.value}
              onClick={() => setActiveCategory(cat.value)}
              aria-pressed={activeCategory === cat.value}
              className={`px-6 py-3 text-[10px] font-black uppercase tracking-widest transition-all border-2 flex items-center gap-2 ${
                activeCategory === cat.value
                  ? "bg-silver-bright text-black border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] -translate-x-0.5 -translate-y-0.5"
                  : "bg-charcoal-dark text-silver/30 border-silver-bright/5 hover:border-silver-bright/20"
              }`}
            >
              <span className="material-symbols-outlined text-sm">{cat.icon}</span>
              {cat.label}
              {activeCategory === cat.value && <span className="w-1 h-3 bg-black"></span>}
            </button>
          ))}
        </div>
      </section>

      {/* Templates Grid */}
      <section className="relative">
        <AnimatePresence mode="wait">
          {loading ? (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="py-40 flex items-center justify-center"
            >
              <div className="flex flex-col items-center gap-6">
                <div className="w-12 h-12 border-4 border-rag-blue border-t-transparent rounded-full animate-spin"></div>
                <p className="text-xs font-mono text-silver/40 uppercase tracking-widest italic">
                  Loading templates...
                </p>
              </div>
            </motion.div>
          ) : templates.length === 0 ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="py-40 bg-charcoal/30 border-4 border-dashed border-silver-bright/5 text-center flex flex-col items-center gap-8"
            >
              <span className="material-symbols-outlined text-silver/5 text-9xl">scan_delete</span>
              <div className="space-y-2">
                <p className="text-xl font-black text-silver/20 uppercase tracking-[0.4em] italic">
                  No templates found
                </p>
                <p className="text-xs font-mono text-silver/10 uppercase tracking-widest">
                  No scan templates available for the selected category
                </p>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key={activeCategory || "all"}
              variants={containerVariants}
              initial="hidden"
              animate="visible"
              className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8"
            >
              {templates.map((template) => (
                <motion.div
                  key={template.id}
                  variants={cardVariants}
                  layout
                  className="bg-charcoal border-4 border-black p-8 shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] transition-all flex flex-col group"
                >
                  {/* Icon */}
                  <div className="w-14 h-14 bg-charcoal-dark border-4 border-black flex items-center justify-center shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] group-hover:shadow-none group-hover:translate-x-1 group-hover:translate-y-1 transition-all mb-6">
                    <span className="material-symbols-outlined text-2xl text-rag-blue">
                      {template.icon}
                    </span>
                  </div>

                  {/* Name & Description */}
                  <div className="flex-1 space-y-3 mb-6">
                    <h3 className="text-2xl font-black text-silver-bright uppercase tracking-tighter italic leading-none group-hover:text-rag-blue transition-colors">
                      {template.name}
                    </h3>
                    <p className="text-xs font-mono text-silver/50 leading-relaxed">
                      {template.description}
                    </p>
                  </div>

                  {/* Badges */}
                  <div className="flex flex-wrap items-center gap-3 mb-6">
                    <span className="px-3 py-1 text-[9px] font-black uppercase italic border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] bg-charcoal-dark text-silver/60">
                      {template.category}
                    </span>
                    <span
                      className={`px-3 py-1 text-[9px] font-black uppercase italic border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${
                        complexityColors[template.complexity] || "bg-charcoal-dark text-silver/60"
                      }`}
                    >
                      {template.complexity}
                    </span>
                    <span className="px-3 py-1 text-[9px] font-black uppercase italic border-2 border-black shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] bg-charcoal-dark text-silver/60">
                      {template.estimated_duration}
                    </span>
                  </div>

                  {/* Tags */}
                  {template.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-8">
                      {template.tags.map((tag) => (
                        <span
                          key={tag}
                          className="text-[8px] font-mono text-silver/30 uppercase tracking-widest border border-silver-bright/10 px-2 py-1"
                        >
                          #{tag}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* CTA */}
                  <button
                    onClick={() => handleUseTemplate(template)}
                    className="w-full bg-rag-blue text-black py-4 text-[10px] font-black uppercase tracking-widest shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all flex items-center justify-center gap-3 italic"
                  >
                    Use Template
                    <span className="material-symbols-outlined text-sm">arrow_right_alt</span>
                  </button>
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      {/* Footer */}
      <footer className="pt-24 opacity-20 pointer-events-none select-none flex flex-col md:flex-row justify-between items-center gap-8 text-[9px] font-black uppercase tracking-[0.5em] italic">
        <div className="flex items-center gap-4">
          <span className="w-8 h-8 border-4 border-silver/20 flex items-center justify-center font-serif text-lg">S</span>
          SECUSCAN TEMPLATE CATALOG v1.0
        </div>
        <div className="flex gap-2">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((i) => (
            <div key={i} className="w-1.5 h-3 bg-silver/20"></div>
          ))}
        </div>
      </footer>
    </div>
  );
}

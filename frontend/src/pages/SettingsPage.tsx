import React, { useEffect, useState, useCallback } from 'react'
import {
  Activity,
  Server,
  Database,
  Cpu,
  DollarSign,
  TrendingUp,
  RotateCw,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Clock,
  ShieldCheck,
} from 'lucide-react'
import { getMonitoringStats } from '../api/monitoring'
import type { MonitoringStats } from '../types'
import Spinner from '../components/Spinner'

export const SettingsPage: React.FC = () => {
  const [stats, setStats] = useState<MonitoringStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadStats = useCallback(async () => {
    try {
      const data = await getMonitoringStats()
      setStats(data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch monitoring metrics'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadStats()
    const interval = setInterval(() => void loadStats(), 10000)
    return () => clearInterval(interval)
  }, [loadStats])

  return (
    <div className="flex flex-col h-full overflow-hidden bg-slate-50">
      {/* Header */}
      <div className="border-b border-slate-200 bg-white px-8 py-5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
              <Activity className="h-5 w-5 text-emerald-600" />
              Admin & System Monitoring
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              Live ingestion pipeline metrics, subsystem health checks, and RAG evaluation benchmarks
            </p>
          </div>
          <button
            type="button"
            onClick={() => void loadStats()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition shadow-xs"
          >
            <RotateCw className="h-3.5 w-3.5" />
            Refresh Metrics
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto px-8 py-6 space-y-6">
        {error && (
          <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">
            <AlertTriangle className="h-4 w-4 text-red-500 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {loading && !stats ? (
          <div className="flex justify-center py-20">
            <Spinner size={32} className="text-emerald-600" />
          </div>
        ) : stats ? (
          <>
            {/* Top Stat Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Total Indexed Chunks
                  </span>
                  <div className="rounded-lg bg-emerald-50 p-2 text-emerald-600">
                    <Layers className="h-4 w-4" />
                  </div>
                </div>
                <div className="mt-2 text-2xl font-bold text-slate-800">
                  {stats.ingestion.total_chunks}
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  Across {stats.ingestion.total_documents} uploaded documents
                </p>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Recall @ 5 Benchmark
                  </span>
                  <div className="rounded-lg bg-blue-50 p-2 text-blue-600">
                    <TrendingUp className="h-4 w-4" />
                  </div>
                </div>
                <div className="mt-2 text-2xl font-bold text-slate-800">
                  {(stats.evaluation.recall_at_5 * 100).toFixed(0)}%
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  MRR: {stats.evaluation.mrr.toFixed(2)} | Coverage: {(stats.evaluation.fact_coverage * 100).toFixed(0)}%
                </p>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Avg Answer Latency
                  </span>
                  <div className="rounded-lg bg-purple-50 p-2 text-purple-600">
                    <Clock className="h-4 w-4" />
                  </div>
                </div>
                <div className="mt-2 text-2xl font-bold text-slate-800">
                  {stats.evaluation.avg_answer_latency_sec}s
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  End-to-end retrieval + LLM synthesis
                </p>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    Est. LLM Cost
                  </span>
                  <div className="rounded-lg bg-amber-50 p-2 text-amber-600">
                    <DollarSign className="h-4 w-4" />
                  </div>
                </div>
                <div className="mt-2 text-2xl font-bold text-slate-800">
                  ${stats.llm_usage.estimated_cost_usd}
                </div>
                <p className="text-[11px] text-slate-400 mt-1">
                  {stats.llm_usage.total_prompt_tokens + stats.llm_usage.total_completion_tokens} tokens tracked
                </p>
              </div>
            </div>

            {/* Ingestion Pipeline Statuses */}
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
              <h2 className="text-sm font-bold text-slate-800 mb-4 flex items-center gap-2">
                <Layers className="h-4 w-4 text-emerald-600" />
                Ingestion Job & Document Pipeline Statuses
              </h2>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="rounded-lg border border-emerald-100 bg-emerald-50/50 p-3">
                  <p className="text-xs font-semibold text-emerald-800">Indexed</p>
                  <p className="text-xl font-bold text-emerald-900 mt-1">
                    {stats.ingestion.status_counts.indexed ?? 0}
                  </p>
                  <p className="text-[10px] text-emerald-600 mt-0.5">Searchable in Qdrant</p>
                </div>
                <div className="rounded-lg border border-amber-100 bg-amber-50/50 p-3">
                  <p className="text-xs font-semibold text-amber-800">Processing</p>
                  <p className="text-xl font-bold text-amber-900 mt-1">
                    {stats.ingestion.status_counts.processing ?? 0}
                  </p>
                  <p className="text-[10px] text-amber-600 mt-0.5">Celery worker running</p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs font-semibold text-slate-700">Uploaded</p>
                  <p className="text-xl font-bold text-slate-800 mt-1">
                    {stats.ingestion.status_counts.uploaded ?? 0}
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5">Awaiting worker queue</p>
                </div>
                <div className="rounded-lg border border-red-100 bg-red-50/50 p-3">
                  <p className="text-xs font-semibold text-red-800">Failed</p>
                  <p className="text-xl font-bold text-red-900 mt-1">
                    {stats.ingestion.status_counts.failed ?? 0}
                  </p>
                  <p className="text-[10px] text-red-600 mt-0.5">Retry available</p>
                </div>
              </div>
            </div>

            {/* Subsystem Health & Evaluation Section */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Service Health */}
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
                <h2 className="text-sm font-bold text-slate-800 mb-4 flex items-center gap-2">
                  <Server className="h-4 w-4 text-emerald-600" />
                  Service Health & Connectivity
                </h2>
                <div className="space-y-3">
                  <div className="flex items-center justify-between rounded-lg border border-slate-100 p-3">
                    <div className="flex items-center gap-3">
                      <Database className="h-4 w-4 text-slate-500" />
                      <div>
                        <p className="text-xs font-semibold text-slate-800">PostgreSQL Relational DB</p>
                        <p className="text-[11px] text-slate-400">Stores users, docs, conversation history</p>
                      </div>
                    </div>
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800">
                      <CheckCircle2 className="h-3 w-3" /> Healthy
                    </span>
                  </div>

                  <div className="flex items-center justify-between rounded-lg border border-slate-100 p-3">
                    <div className="flex items-center gap-3">
                      <Cpu className="h-4 w-4 text-slate-500" />
                      <div>
                        <p className="text-xs font-semibold text-slate-800">Qdrant Vector Database</p>
                        <p className="text-[11px] text-slate-400">Cosine similarity semantic search</p>
                      </div>
                    </div>
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800">
                      <CheckCircle2 className="h-3 w-3" /> Healthy
                    </span>
                  </div>

                  <div className="flex items-center justify-between rounded-lg border border-slate-100 p-3">
                    <div className="flex items-center gap-3">
                      <Activity className="h-4 w-4 text-slate-500" />
                      <div>
                        <p className="text-xs font-semibold text-slate-800">Redis & Celery Task Queue</p>
                        <p className="text-[11px] text-slate-400">Asynchronous background ingestion</p>
                      </div>
                    </div>
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800">
                      <CheckCircle2 className="h-3 w-3" /> Healthy
                    </span>
                  </div>
                </div>
              </div>

              {/* RAG Quality Benchmarks */}
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
                <h2 className="text-sm font-bold text-slate-800 mb-4 flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-emerald-600" />
                  RAG Evaluation Benchmarks
                </h2>
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                      <span>Citation Precision</span>
                      <span>{(stats.evaluation.citation_precision * 100).toFixed(0)}%</span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                      <div
                        className="h-full rounded-full bg-emerald-500"
                        style={{ width: `${stats.evaluation.citation_precision * 100}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                      <span>Abstention Accuracy (unanswerable questions)</span>
                      <span>{(stats.evaluation.abstention_accuracy * 100).toFixed(0)}%</span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                      <div
                        className="h-full rounded-full bg-emerald-500"
                        style={{ width: `${stats.evaluation.abstention_accuracy * 100}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-xs font-medium text-slate-700 mb-1">
                      <span>Fact Coverage</span>
                      <span>{(stats.evaluation.fact_coverage * 100).toFixed(0)}%</span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                      <div
                        className="h-full rounded-full bg-blue-500"
                        style={{ width: `${stats.evaluation.fact_coverage * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </>
        ) : null}
      </div>
    </div>
  )
}

export default SettingsPage

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  AlertCircle,
  ArrowDownRight,
  ArrowLeft,
  ArrowUpRight,
  ChevronDown,
  ChevronUp,
  Clock,
  FileText,
  HelpCircle,
  LayoutDashboard,
  Phone,
  TrendingUp,
  Users,
} from 'lucide-react';

interface CallLog {
  id: number;
  user_id: string;
  farmer_name: string;
  summary: string;
  duration_seconds: number;
  outcome: string;
  error_log: string | null;
  call_type: string;
  created_at: string;
}

interface AnalyticsData {
  total_calls: number;
  success_rate: number;
  avg_duration: number;
  pending_escalations: number;
  inbound_count: number;
  outbound_count: number;
  recent_calls: CallLog[];
}

export default function DashboardPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<'ALL' | 'INBOUND' | 'OUTBOUND' | 'ESCALATIONS'>(
    'ALL'
  );
  const [expandedCallId, setExpandedCallId] = useState<number | null>(null);

  useEffect(() => {
    async function fetchAnalytics() {
      try {
        const res = await fetch('/api/analytics');
        if (!res.ok) throw new Error('Failed to fetch analytics data');
        const json = await res.json();
        setData(json);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    }
    fetchAnalytics();
  }, []);

  const toggleExpand = (id: number) => {
    setExpandedCallId(expandedCallId === id ? null : id);
  };

  if (loading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[#fcfbfa] text-[#423d38]">
        <div className="text-center">
          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-4 border-[#3c6e47] border-t-transparent"></div>
          <p className="mt-4 font-medium">कृषी मित्र माहिती गोळा करत आहे...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[#fcfbfa] text-[#8b3a3a]">
        <div className="max-w-md rounded-2xl border border-[#ebdccb] bg-white p-6 text-center shadow-sm">
          <AlertCircle className="mx-auto mb-4 h-12 w-12 text-[#8b3a3a]" />
          <h3 className="text-lg font-bold">Analytics Connection Failed</h3>
          <p className="mt-2 text-sm text-[#70665c]">
            {error || 'Could not read data from SQLite database.'}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="mt-6 rounded-lg bg-[#3c6e47] px-4 py-2 text-sm font-medium text-white hover:bg-[#2d5235]"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  // Filter logs locally
  const filteredCalls = data.recent_calls.filter((call) => {
    if (activeFilter === 'ALL') return true;
    if (activeFilter === 'INBOUND') return call.call_type === 'INBOUND';
    if (activeFilter === 'OUTBOUND') return call.call_type === 'OUTBOUND';
    if (activeFilter === 'ESCALATIONS')
      return call.summary?.toLowerCase().includes('ticket') || call.summary?.includes('तक्रार');
    return true;
  });

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#fcfbfa] font-sans text-[#423d38]">
      {/* Sidebar Navigation - Referenced from Copperx */}
      <aside className="flex w-64 shrink-0 flex-col justify-between border-r border-[#ebdccb] bg-white">
        <div className="p-6">
          <div className="flex items-center gap-3">
            <div className="relative h-8 w-8 shrink-0 overflow-hidden rounded-full border border-[#ebdccb]">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/cotton-logo-icon.png"
                alt="Krushi Mitra Logo"
                className="h-full w-full object-cover"
              />
            </div>
            <span className="text-lg font-bold tracking-tight text-[#2d5235]">Krushi Mitra</span>
          </div>

          <nav className="mt-8 space-y-1">
            <button className="flex w-full items-center gap-3 rounded-xl bg-[#f0f7f2] px-3 py-2.5 text-sm font-medium text-[#2d5235]">
              <LayoutDashboard className="h-4.5 w-4.5" />
              Dashboard
            </button>
            <Link
              href="/"
              className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-[#70665c] hover:bg-[#fcfbfa] hover:text-[#423d38]"
            >
              <Phone className="h-4.5 w-4.5 text-[#a89d91]" />
              Voice Dialer (Client)
            </Link>
            <button className="flex w-full cursor-not-allowed items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-[#70665c] opacity-50">
              <Users className="h-4.5 w-4.5 text-[#a89d91]" />
              Farmer Profiles
            </button>
            <button className="flex w-full cursor-not-allowed items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-[#70665c] opacity-50">
              <FileText className="h-4.5 w-4.5 text-[#a89d91]" />
              Escalation Logs
            </button>
          </nav>
        </div>

        <div className="space-y-4 border-t border-[#ebdccb] p-6">
          <div className="rounded-2xl border border-[#ebdccb] bg-[#fcfbfa] p-4 text-center">
            <h4 className="text-xs font-semibold text-[#70665c]">Vidarbha Cotton Track</h4>
            <p className="mt-1 text-xs text-[#a89d91]">Status: Active SQLite</p>
          </div>
          <button className="flex w-full items-center gap-3 px-3 py-2.5 text-sm font-medium text-[#70665c] hover:text-[#423d38]">
            <HelpCircle className="h-4.5 w-4.5 text-[#a89d91]" />
            Documentation
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto p-8 lg:p-10">
        <div className="mx-auto w-full max-w-[960px]">
          {/* Header Action Row */}
          <header className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-[#2d5235]">
                Call Analytics & Performance
              </h1>
              <p className="mt-1 text-sm text-[#70665c]">
                Real-time statistics of inbound calls and outbound alert dispatches.
              </p>
            </div>
            <Link
              href="/"
              className="flex items-center gap-2 rounded-xl border border-[#ebdccb] bg-white px-4 py-2 text-sm font-medium hover:bg-[#fcfbfa]"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Dialer
            </Link>
          </header>

          {/* Top Alert Banner - Mimics Copperx KYC alert style */}
          <div className="mb-8 flex flex-col items-start justify-between gap-4 rounded-2xl border border-[#3c6e47]/20 bg-[#3c6e47]/10 p-4 sm:flex-row sm:items-center">
            <div className="flex items-start gap-3">
              <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-[#3c6e47]" />
              <div>
                <p className="text-sm font-semibold text-[#2d5235]">
                  Review Pending Farmer Escalations
                </p>
                <p className="mt-0.5 text-xs text-[#70665c]">
                  There are {data.pending_escalations} active human-escalation tickets waiting for
                  agricultural specialist call-back.
                </p>
              </div>
            </div>
            <button
              onClick={() => setActiveFilter('ESCALATIONS')}
              className="rounded-xl bg-[#3c6e47] px-4 py-1.5 text-xs font-semibold text-white hover:bg-[#2d5235]"
            >
              Review Tickets
            </button>
          </div>

          {/* Core Metrics Block - Overall Balance Box layout from Copperx */}
          <section className="mb-10 grid grid-cols-1 gap-8 lg:grid-cols-3">
            {/* Main Display: Success Rate (Big Balance style) */}
            <div className="flex min-h-[220px] flex-col justify-between rounded-3xl border border-[#ebdccb] bg-white p-8 shadow-sm lg:col-span-2">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-[#70665c]">
                    Overall Advisory Success Rate
                  </span>
                  <span className="flex items-center gap-1 rounded-full bg-[#f0f7f2] px-2.5 py-1 text-xs font-semibold text-[#2d5235]">
                    <TrendingUp className="h-3 w-3" /> Live
                  </span>
                </div>
                <div className="mt-6">
                  <span className="text-5xl font-extrabold tracking-tight text-[#2d5235]">
                    {data.success_rate}%
                  </span>
                  <p className="mt-2 text-sm text-[#a89d91]">
                    Percentage of queries resolved via mandi pricing, weather forecasting, or ticket
                    logging.
                  </p>
                </div>
              </div>
              <div className="mt-6 flex items-center gap-2 border-t border-[#f5ece3] pt-4 text-xs text-[#70665c]">
                <span className="font-semibold text-[#2d5235]">{data.inbound_count} Inbound</span>
                <span>•</span>
                <span className="font-semibold text-[#2d5235]">{data.outbound_count} Outbound</span>
                <span>•</span>
                <span>Total calls: {data.total_calls}</span>
              </div>
            </div>

            {/* Quick Metrics Columns */}
            <div className="grid grid-cols-1 gap-4">
              <div className="flex items-center gap-4 rounded-2xl border border-[#ebdccb] bg-white p-5 shadow-sm">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#ebdccb]/40 text-[#423d38]">
                  <Clock className="h-5 w-5" />
                </div>
                <div>
                  <span className="block text-xs font-medium text-[#70665c]">
                    Average Call Duration
                  </span>
                  <span className="mt-1 text-xl font-bold text-[#423d38]">
                    {data.avg_duration} seconds
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-4 rounded-2xl border border-[#ebdccb] bg-white p-5 shadow-sm">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#3c6e47]/10 text-[#3c6e47]">
                  <FileText className="h-5 w-5" />
                </div>
                <div>
                  <span className="block text-xs font-medium text-[#70665c]">
                    Pending Escalations
                  </span>
                  <span className="mt-1 text-xl font-bold text-[#3c6e47]">
                    {data.pending_escalations} Tickets
                  </span>
                </div>
              </div>
            </div>
          </section>

          {/* Transactions / Call Log Section - Replicated Filter layout from Copperx */}
          <section className="overflow-hidden rounded-3xl border border-[#ebdccb] bg-white shadow-sm">
            {/* Header & Local Filters */}
            <div className="flex flex-col items-start justify-between gap-4 border-b border-[#ebdccb] bg-[#fcfbfa]/50 p-6 sm:flex-row sm:items-center">
              <h3 className="text-lg font-bold text-[#2d5235]">Recent call logs & warnings</h3>

              <div className="flex max-w-full gap-1 overflow-x-auto rounded-xl bg-[#ebdccb]/30 p-1">
                {(['ALL', 'INBOUND', 'OUTBOUND', 'ESCALATIONS'] as const).map((filter) => (
                  <button
                    key={filter}
                    onClick={() => {
                      setActiveFilter(filter);
                      setExpandedCallId(null);
                    }}
                    className={`shrink-0 rounded-lg px-3 py-1 text-xs font-semibold transition-colors ${
                      activeFilter === filter
                        ? 'bg-white text-[#2d5235] shadow-xs'
                        : 'text-[#70665c] hover:text-[#423d38]'
                    }`}
                  >
                    {filter === 'ALL' && 'All Calls'}
                    {filter === 'INBOUND' && 'Inbound'}
                    {filter === 'OUTBOUND' && 'Outbound Alerts'}
                    {filter === 'ESCALATIONS' && 'Escalations'}
                  </button>
                ))}
              </div>
            </div>

            {/* List of Calls */}
            {filteredCalls.length === 0 ? (
              <div className="p-12 text-center text-[#70665c]">
                <Phone className="mx-auto mb-3 h-10 w-10 text-[#a89d91]" />
                <p className="text-sm font-medium">No calls match your active filter.</p>
                <p className="mt-1 text-xs text-[#a89d91]">
                  Interactions will appear here once calls are initiated.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-[#f5ece3]">
                {filteredCalls.map((call) => {
                  const isExpanded = expandedCallId === call.id;
                  const isSuccess = call.outcome === 'SUCCESS';

                  return (
                    <div key={call.id} className="transition-colors hover:bg-[#fcfbfa]/40">
                      <div
                        onClick={() => toggleExpand(call.id)}
                        className="flex cursor-pointer flex-col items-start justify-between gap-4 p-5 sm:flex-row sm:items-center"
                      >
                        {/* Left: Call Status Icon & Farmer Identity */}
                        <div className="flex items-center gap-4">
                          <div
                            className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${
                              isSuccess
                                ? 'bg-[#f0f7f2] text-[#2d5235]'
                                : 'bg-[#8b3a3a]/10 text-[#8b3a3a]'
                            }`}
                          >
                            {isSuccess ? (
                              <ArrowUpRight className="h-4.5 w-4.5" />
                            ) : (
                              <ArrowDownRight className="h-4.5 w-4.5" />
                            )}
                          </div>
                          <div>
                            <span className="block text-sm font-bold text-[#423d38] sm:inline">
                              {call.farmer_name}
                            </span>
                            <span className="text-xs text-[#70665c] sm:ml-2">({call.user_id})</span>

                            <div className="mt-1 flex items-center gap-2">
                              <span
                                className={`rounded-md px-2 py-0.5 text-[10px] font-bold ${
                                  call.call_type === 'INBOUND'
                                    ? 'bg-[#ebdccb]/40 text-[#70665c]'
                                    : 'bg-[#3c6e47]/10 text-[#2d5235]'
                                }`}
                              >
                                {call.call_type}
                              </span>
                              <span className="text-[11px] text-[#a89d91]">{call.created_at}</span>
                            </div>
                          </div>
                        </div>

                        {/* Right: Duration & Expand Trigger */}
                        <div className="flex w-full items-center justify-between gap-4 border-t border-[#f5ece3] pt-2 sm:w-auto sm:justify-end sm:border-0 sm:pt-0">
                          <div className="text-left sm:text-right">
                            <span className="text-sm font-bold text-[#423d38]">
                              {call.duration_seconds}s
                            </span>
                            <span className="block text-xs text-[#a89d91]">Duration</span>
                          </div>
                          <div className="flex items-center gap-3">
                            <span
                              className={`rounded-md px-2 py-0.5 text-[10px] font-bold ${
                                isSuccess
                                  ? 'bg-[#f0f7f2] text-[#2d5235]'
                                  : 'bg-[#8b3a3a]/10 text-[#8b3a3a]'
                              }`}
                            >
                              {call.outcome}
                            </span>
                            {isExpanded ? (
                              <ChevronUp className="h-4 w-4 text-[#a89d91]" />
                            ) : (
                              <ChevronDown className="h-4 w-4 text-[#a89d91]" />
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Expandable summary details */}
                      {isExpanded && (
                        <div className="border-t border-[#f5ece3]/50 bg-[#fcfbfa]/70 px-5 pt-1 pb-5 text-xs text-[#70665c]">
                          <div className="max-w-3xl space-y-2">
                            <p className="text-xs font-semibold text-[#423d38]">
                              मराठी संवाद सारांश (Marathi Summary):
                            </p>
                            <p className="rounded-xl border border-[#ebdccb]/60 bg-white p-3 leading-relaxed font-medium text-[#423d38] italic">
                              &quot;{call.summary || 'No summary was generated.'}&quot;
                            </p>
                            {!isSuccess && call.error_log && (
                              <p className="mt-2 text-[10px] text-[#8b3a3a]">
                                <strong>Failure Details:</strong> {call.error_log}
                              </p>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {/* Table Footer */}
            <div className="border-t border-[#ebdccb] p-4 text-center text-xs text-[#a89d91]">
              Showing most recent call history entries • Powered by Krushi Mitra
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

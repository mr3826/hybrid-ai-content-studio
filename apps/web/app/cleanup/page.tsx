"use client";

import { useEffect, useState } from "react";
import {
  HardDrive,
  ShieldCheck,
  ShieldAlert,
  Archive,
  RefreshCw,
  Trash2,
  Play,
  FileCheck,
  AlertTriangle,
  Copy,
  CheckCircle2,
  Database,
  History,
  Info,
  Check,
  Sparkles,
  Layers,
  X,
  ExternalLink,
} from "lucide-react";
import { useLanguage } from "@/lib/LanguageContext";
import {
  ReliabilitySummaryResponse,
  StorageInspectionSummary,
  FileCandidateInfo,
  CleanupReport,
  StudioBackupRecord,
  BackupVerifyResponse,
  SandboxRestoreResponse,
  getReliabilitySummary,
  inspectStorage,
  executeCleanup,
  listCleanupLogs,
  createBackup,
  listBackups,
  verifyBackup,
  testRestoreBackup,
} from "@/lib/api";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

export default function CleanupPage() {
  const { t } = useLanguage();

  const [summary, setSummary] = useState<ReliabilitySummaryResponse | null>(null);
  const [inspection, setInspection] = useState<StorageInspectionSummary | null>(null);
  const [backups, setBackups] = useState<StudioBackupRecord[]>([]);
  const [auditLogs, setAuditLogs] = useState<CleanupReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<"inspection" | "backups" | "policies" | "logs">("inspection");

  // Selection & Actions
  const [selectedDirs, setSelectedDirs] = useState<string[]>(["tmp", "cache", "runtime", "exports"]);
  const [simulating, setSimulating] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [copiedChecksum, setCopiedChecksum] = useState<string | null>(null);

  // Backup modal
  const [showBackupModal, setShowBackupModal] = useState(false);
  const [creatingBackup, setCreatingBackup] = useState(false);
  const [backupForm, setBackupForm] = useState({
    backup_name: "",
    backup_type: "FULL",
    notes: "",
  });

  // Verification & Sandbox Restore state
  const [verifyingId, setVerifyingId] = useState<string | null>(null);
  const [restoringId, setRestoringId] = useState<string | null>(null);
  const [verifyResult, setVerifyResult] = useState<BackupVerifyResponse | null>(null);
  const [restoreResult, setRestoreResult] = useState<SandboxRestoreResponse | null>(null);

  // Toasts / Feedback message
  const [toastMessage, setToastMessage] = useState<{ text: string; type: "success" | "error" | "info" } | null>(null);

  const showToast = (text: string, type: "success" | "error" | "info" = "success") => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 5000);
  };

  const loadData = async (isManualRefresh = false) => {
    if (isManualRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const [sumRes, inspRes, bkpRes, logRes] = await Promise.all([
        getReliabilitySummary().catch(() => null),
        inspectStorage({ target_directories: selectedDirs, dry_run: true }).catch(() => null),
        listBackups().catch(() => []),
        listCleanupLogs().catch(() => []),
      ]);

      if (sumRes) setSummary(sumRes);
      if (inspRes) setInspection(inspRes);
      if (bkpRes) setBackups(bkpRes);
      if (logRes) setAuditLogs(logRes);
    } catch (err) {
      console.error("Failed to load cleanup & reliability data:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSimulate = async () => {
    setSimulating(true);
    try {
      const res = await executeCleanup({
        dry_run: true,
        target_directories: selectedDirs,
        max_files_to_delete: 500,
      });
      showToast(t("cleanup.toast.dryRunSuccess") || "Cleanup simulation completed successfully!");
      // Reload inspection & summary
      const [sumRes, inspRes, logRes] = await Promise.all([
        getReliabilitySummary(),
        inspectStorage({ target_directories: selectedDirs, dry_run: true }),
        listCleanupLogs(),
      ]);
      setSummary(sumRes);
      setInspection(inspRes);
      setAuditLogs(logRes);
    } catch (err: any) {
      showToast(err.message || "Simulation failed", "error");
    } finally {
      setSimulating(false);
    }
  };

  const handleExecuteDelete = async () => {
    setShowConfirmModal(false);
    setExecuting(true);
    try {
      const res = await executeCleanup({
        dry_run: false,
        target_directories: selectedDirs,
        max_files_to_delete: 500,
      });
      showToast(
        `${t("cleanup.toast.cleanupSuccess") || "Safe deletion executed cleanly!"} (${res.deleted_files_count} files, ${formatBytes(res.recovered_bytes)})`,
        "success"
      );
      // Refresh inspection and logs
      const [sumRes, inspRes, logRes] = await Promise.all([
        getReliabilitySummary(),
        inspectStorage({ target_directories: selectedDirs, dry_run: true }),
        listCleanupLogs(),
      ]);
      setSummary(sumRes);
      setInspection(inspRes);
      setAuditLogs(logRes);
    } catch (err: any) {
      showToast(err.message || "Execution failed", "error");
    } finally {
      setExecuting(false);
    }
  };

  const handleCreateBackup = async () => {
    setCreatingBackup(true);
    try {
      await createBackup({
        backup_name: backupForm.backup_name || undefined,
        backup_type: backupForm.backup_type,
        notes: backupForm.notes || undefined,
      });
      setShowBackupModal(false);
      setBackupForm({ backup_name: "", backup_type: "FULL", notes: "" });
      showToast(t("cleanup.toast.backupSuccess") || "Backup snapshot created and verified!");
      const [bkpRes, sumRes] = await Promise.all([listBackups(), getReliabilitySummary()]);
      setBackups(bkpRes);
      setSummary(sumRes);
    } catch (err: any) {
      showToast(err.message || "Backup creation failed", "error");
    } finally {
      setCreatingBackup(false);
    }
  };

  const handleVerifyBackup = async (id: string) => {
    setVerifyingId(id);
    try {
      const res = await verifyBackup(id);
      setVerifyResult(res);
      if (res.is_valid) {
        showToast(t("cleanup.toast.verifyValid") || "SHA-256 and archive integrity verified successfully!", "success");
      } else {
        showToast(t("cleanup.toast.verifyInvalid") || "Warning: Checksum or archive integrity mismatch!", "error");
      }
    } catch (err: any) {
      showToast(err.message || "Verification failed", "error");
    } finally {
      setVerifyingId(null);
    }
  };

  const handleTestRestore = async (id: string) => {
    setRestoringId(id);
    try {
      const res = await testRestoreBackup(id, { dry_run: true });
      setRestoreResult(res);
      if (res.status === "SUCCESS" && res.integrity_check === "ok") {
        showToast(
          t("cleanup.toast.sandboxSuccess") || "Sandbox restore and SQLite integrity check passed (PRAGMA: ok)!",
          "success"
        );
      } else {
        showToast(t("cleanup.toast.sandboxFailed") || "Sandbox restore validation failed!", "error");
      }
    } catch (err: any) {
      showToast(err.message || "Sandbox restore failed", "error");
    } finally {
      setRestoringId(null);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedChecksum(text);
    setTimeout(() => setCopiedChecksum(null), 2500);
  };

  const toggleDir = (dir: string) => {
    setSelectedDirs((prev) =>
      prev.includes(dir) ? prev.filter((d) => d !== dir) : [...prev, dir]
    );
  };

  return (
    <div className="flex-1 overflow-y-auto p-8 bg-slate-950 text-slate-100 min-h-screen">
      {/* Toast Notification */}
      {toastMessage && (
        <div
          className={`fixed bottom-8 right-8 z-50 px-5 py-3 rounded-xl border shadow-2xl backdrop-blur-md flex items-center gap-3 transition-all ${
            toastMessage.type === "success"
              ? "bg-emerald-950/90 border-emerald-500/50 text-emerald-200"
              : toastMessage.type === "error"
              ? "bg-rose-950/90 border-rose-500/50 text-rose-200"
              : "bg-blue-950/90 border-blue-500/50 text-blue-200"
          }`}
        >
          {toastMessage.type === "success" && <CheckCircle2 className="w-5 h-5 text-emerald-400" />}
          {toastMessage.type === "error" && <AlertTriangle className="w-5 h-5 text-rose-400" />}
          {toastMessage.type === "info" && <Info className="w-5 h-5 text-blue-400" />}
          <span className="text-sm font-medium">{toastMessage.text}</span>
          <button
            onClick={() => setToastMessage(null)}
            className="ml-2 hover:opacity-75 transition-opacity"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30">
              <HardDrive className="w-7 h-7 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-slate-100 via-slate-200 to-indigo-300 bg-clip-text text-transparent">
                {t("cleanup.title") || "Cleanup, Backup & Reliability"}
              </h1>
              <p className="text-sm text-slate-400 mt-0.5">
                {t("cleanup.subtitle") ||
                  "Local storage retention, reference-safe unlinking, and cryptographic backup verification"}
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => loadData(true)}
            disabled={refreshing}
            className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white flex items-center gap-2 text-sm font-medium transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin text-indigo-400" : ""}`} />
            {t("common.refresh") || "Refresh"}
          </button>
          <button
            onClick={() => setShowBackupModal(true)}
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-2 text-sm font-semibold shadow-lg shadow-indigo-600/20 transition-all hover:shadow-indigo-600/30"
          >
            <Archive className="w-4 h-4" />
            {t("cleanup.backups.createBtn") || "Create Backup"}
          </button>
        </div>
      </div>

      {/* Storage & Reliability KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mt-6">
        {/* Total Storage Used */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Storage Tracked</span>
            <HardDrive className="w-4 h-4 text-slate-500" />
          </div>
          <div className="text-2xl font-bold text-slate-100 mt-2">
            {summary ? formatBytes(summary.storage_usage_bytes) : "..."}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {inspection ? `${inspection.total_files_scanned} files across 5 directories` : "Scanning storage..."}
          </div>
        </div>

        {/* SQLite Database Size */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>{t("cleanup.kpis.dbSize") || "Database Size"}</span>
            <Database className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-cyan-300 mt-2">
            {summary ? formatBytes(summary.database_size_bytes) : "..."}
          </div>
          <div className="text-xs text-slate-500 mt-1">WAL-mode studio.sqlite</div>
        </div>

        {/* Recoverable Storage */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-emerald-900/30 backdrop-blur-sm relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>{t("cleanup.kpis.recoverable") || "Recoverable Space"}</span>
            <Trash2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 mt-2">
            {inspection ? formatBytes(inspection.recoverable_bytes) : "0 B"}
          </div>
          <div className="text-xs text-emerald-400/80 mt-1">
            {inspection ? `${inspection.candidates_count} eligible deletion candidates` : "0 files"}
          </div>
        </div>

        {/* Protected Assets Count */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Protected Files</span>
            <ShieldCheck className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-indigo-300 mt-2">
            {inspection ? inspection.protected_files_count : "0"}
          </div>
          <div className="text-xs text-slate-500 mt-1">Active project / DB invariants</div>
        </div>

        {/* Active Backups */}
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>{t("cleanup.kpis.backups") || "Backup Archives"}</span>
            <Archive className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-purple-300 mt-2">
            {backups.length}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {auditLogs.length} audit logs recorded
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 gap-6 mt-8">
        <button
          onClick={() => setActiveTab("inspection")}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === "inspection"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <HardDrive className="w-4 h-4" />
          {t("cleanup.tabs.inspection") || "Storage & Cleanup"}
          {inspection && inspection.candidates_count > 0 && (
            <span className="px-2 py-0.5 rounded-full text-xs bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              {inspection.candidates_count}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("backups")}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === "backups"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Archive className="w-4 h-4" />
          {t("cleanup.tabs.backups") || "Backups & Recovery"}
          <span className="px-2 py-0.5 rounded-full text-xs bg-purple-500/20 text-purple-300 border border-purple-500/30">
            {backups.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("policies")}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === "policies"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <ShieldCheck className="w-4 h-4" />
          {t("cleanup.tabs.policies") || "Protection Policies & Invariants"}
        </button>

        <button
          onClick={() => setActiveTab("logs")}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === "logs"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <History className="w-4 h-4" />
          Audit History ({auditLogs.length})
        </button>
      </div>

      {/* Tab 1: Storage Inspection & Safe Cleanup */}
      {activeTab === "inspection" && (
        <div className="mt-6 space-y-6">
          {/* Controls Bar */}
          <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                {t("cleanup.inspection.selectDirs") || "Target Storage Directories:"}
              </div>
              <div className="flex flex-wrap gap-2">
                {["tmp", "cache", "runtime", "exports"].map((d) => {
                  const isChecked = selectedDirs.includes(d);
                  return (
                    <button
                      key={d}
                      onClick={() => toggleDir(d)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium border flex items-center gap-1.5 transition-all ${
                        isChecked
                          ? "bg-indigo-600/20 border-indigo-500/50 text-indigo-300"
                          : "bg-slate-800/50 border-slate-700/50 text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      <div
                        className={`w-3.5 h-3.5 rounded flex items-center justify-center border ${
                          isChecked ? "bg-indigo-600 border-indigo-500 text-white" : "border-slate-600"
                        }`}
                      >
                        {isChecked && <Check className="w-2.5 h-2.5" />}
                      </div>
                      <span className="font-mono">{d}/</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex items-center gap-3 self-end md:self-auto">
              <button
                onClick={handleSimulate}
                disabled={simulating || executing}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 flex items-center gap-2 text-sm font-medium transition-colors disabled:opacity-50"
              >
                <Play className={`w-4 h-4 ${simulating ? "animate-spin text-indigo-400" : ""}`} />
                {simulating ? t("cleanup.inspection.simulating") || "Simulating..." : t("cleanup.inspection.dryRunBtn") || "Simulate (Dry-Run)"}
              </button>
              <button
                onClick={() => setShowConfirmModal(true)}
                disabled={simulating || executing || !inspection || inspection.candidates_count === 0}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white flex items-center gap-2 text-sm font-semibold shadow-lg shadow-rose-600/20 transition-all hover:shadow-rose-600/30 disabled:opacity-50 disabled:shadow-none"
              >
                <Trash2 className={`w-4 h-4 ${executing ? "animate-spin" : ""}`} />
                {executing ? t("cleanup.inspection.executing") || "Deleting..." : t("cleanup.inspection.executeBtn") || "Execute Safe Deletion"}
              </button>
            </div>
          </div>

          {/* Candidates & Protected Files Table */}
          <div className="rounded-2xl bg-slate-900/60 border border-slate-800 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-slate-100">
                  {t("cleanup.inspection.title") || "Storage Inspection & Candidate Files"}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Files scanned against tiered retention rules. Active database & project references are strictly protected.
                </p>
              </div>
              {inspection && (
                <div className="text-xs text-slate-400">
                  Showing {inspection.candidates.length} flagged files
                </div>
              )}
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-900/90 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-6">{t("cleanup.inspection.table.file") || "File"}</th>
                    <th className="py-3 px-6">{t("cleanup.inspection.table.category") || "Category"}</th>
                    <th className="py-3 px-6">{t("cleanup.inspection.table.size") || "Size"}</th>
                    <th className="py-3 px-6">{t("cleanup.inspection.table.age") || "Age"}</th>
                    <th className="py-3 px-6">{t("cleanup.inspection.table.status") || "Status"}</th>
                    <th className="py-3 px-6">{t("cleanup.inspection.table.reason") || "Reason / Guard"}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {inspection && inspection.candidates.length > 0 ? (
                    inspection.candidates.map((cand, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3.5 px-6 font-mono text-xs">
                          <div className="font-medium text-slate-200">{cand.filename}</div>
                          <div className="text-slate-500 truncate max-w-xs">{cand.path}</div>
                        </td>
                        <td className="py-3.5 px-6">
                          <span className="px-2.5 py-1 rounded-md text-xs font-mono font-medium bg-slate-800 text-slate-300 border border-slate-700/60">
                            {cand.category}
                          </span>
                        </td>
                        <td className="py-3.5 px-6 font-mono text-xs text-slate-300">
                          {formatBytes(cand.size_bytes)}
                        </td>
                        <td className="py-3.5 px-6 text-xs text-slate-400">
                          {cand.age_hours > 24
                            ? `${(cand.age_hours / 24).toFixed(1)} days`
                            : `${cand.age_hours} hrs`}
                        </td>
                        <td className="py-3.5 px-6">
                          {cand.is_protected ? (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-300 border border-indigo-500/30">
                              <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                              Protected
                            </span>
                          ) : cand.eligible_for_deletion ? (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                              Eligible
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-400">
                              Retained
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-6 text-xs text-slate-400">
                          {cand.protection_reason ? (
                            <span className="text-indigo-300/90 font-medium">
                              {cand.protection_reason}
                            </span>
                          ) : (
                            <span className="text-slate-500">Tier threshold exceeded</span>
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="py-12 text-center text-slate-500 text-sm">
                        {t("cleanup.inspection.empty") ||
                          "No candidate files found for deletion. All files comply with active retention rules."}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Backups & Recovery */}
      {activeTab === "backups" && (
        <div className="mt-6 space-y-6">
          <div className="rounded-2xl bg-slate-900/60 border border-slate-800 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-slate-100">
                  {t("cleanup.backups.title") || "Studio Backup Archives"}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Verified zip archives containing SQLite database snapshot, Brand configuration, Niche profile, and platform settings.
                </p>
              </div>
              <button
                onClick={() => setShowBackupModal(true)}
                className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors"
              >
                <Archive className="w-3.5 h-3.5" />
                {t("cleanup.backups.createBtn") || "Create Snapshot"}
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-900/90 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-6">{t("cleanup.backups.table.name") || "Archive Name"}</th>
                    <th className="py-3 px-6">{t("cleanup.backups.table.type") || "Type"}</th>
                    <th className="py-3 px-6">{t("cleanup.backups.table.size") || "Size"}</th>
                    <th className="py-3 px-6">{t("cleanup.backups.table.checksum") || "SHA-256 Checksum"}</th>
                    <th className="py-3 px-6">{t("cleanup.backups.table.date") || "Created"}</th>
                    <th className="py-3 px-6 text-right">{t("cleanup.backups.table.actions") || "Actions"}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {backups.length > 0 ? (
                    backups.map((bkp) => (
                      <tr key={bkp.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3.5 px-6 font-mono text-xs font-medium text-slate-200">
                          {bkp.backup_name}
                          {bkp.notes && (
                            <div className="text-slate-500 text-[11px] font-sans mt-0.5">{bkp.notes}</div>
                          )}
                        </td>
                        <td className="py-3.5 px-6">
                          <span className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-purple-950/80 text-purple-300 border border-purple-800/50">
                            {bkp.backup_type}
                          </span>
                        </td>
                        <td className="py-3.5 px-6 font-mono text-xs">
                          {formatBytes(bkp.size_bytes)}
                        </td>
                        <td className="py-3.5 px-6 font-mono text-xs">
                          <div className="flex items-center gap-2">
                            <span className="truncate max-w-[140px] text-slate-400">
                              {bkp.checksum_sha256}
                            </span>
                            <button
                              onClick={() => copyToClipboard(bkp.checksum_sha256)}
                              className="text-slate-500 hover:text-slate-300 transition-colors"
                              title="Copy SHA-256"
                            >
                              {copiedChecksum === bkp.checksum_sha256 ? (
                                <Check className="w-3.5 h-3.5 text-emerald-400" />
                              ) : (
                                <Copy className="w-3.5 h-3.5" />
                              )}
                            </button>
                          </div>
                        </td>
                        <td className="py-3.5 px-6 text-xs text-slate-400">
                          {bkp.created_at ? new Date(bkp.created_at).toLocaleString() : "N/A"}
                        </td>
                        <td className="py-3.5 px-6 text-right space-x-2">
                          <button
                            onClick={() => handleVerifyBackup(bkp.id)}
                            disabled={verifyingId === bkp.id}
                            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs font-medium text-indigo-300 border border-slate-700 inline-flex items-center gap-1 transition-colors disabled:opacity-50"
                          >
                            <ShieldCheck className={`w-3.5 h-3.5 ${verifyingId === bkp.id ? "animate-spin" : ""}`} />
                            {verifyingId === bkp.id ? "Verifying..." : "Verify SHA"}
                          </button>
                          <button
                            onClick={() => handleTestRestore(bkp.id)}
                            disabled={restoringId === bkp.id}
                            className="px-2.5 py-1 rounded bg-indigo-950/60 hover:bg-indigo-900/60 text-xs font-medium text-indigo-300 border border-indigo-800/50 inline-flex items-center gap-1 transition-colors disabled:opacity-50"
                          >
                            <Play className={`w-3.5 h-3.5 ${restoringId === bkp.id ? "animate-spin" : ""}`} />
                            {restoringId === bkp.id ? "Testing..." : "Sandbox Test"}
                          </button>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="py-12 text-center text-slate-500 text-sm">
                        {t("cleanup.backups.empty") ||
                          "No backup snapshots created yet. Create a verified backup to preserve SQLite DB and studio configs."}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Verification Results Panel */}
          {verifyResult && (
            <div
              className={`p-5 rounded-2xl border ${
                verifyResult.is_valid
                  ? "bg-emerald-950/30 border-emerald-800/50 text-emerald-200"
                  : "bg-rose-950/30 border-rose-800/50 text-rose-200"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5 font-semibold text-sm">
                  {verifyResult.is_valid ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-rose-400" />
                  )}
                  <span>Backup Verification Audit: {verifyResult.message}</span>
                </div>
                <button onClick={() => setVerifyResult(null)} className="text-slate-400 hover:text-white">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="mt-3 text-xs font-mono space-y-1">
                <div>Calculated SHA-256: {verifyResult.calculated_checksum}</div>
                <div>Expected SHA-256: {verifyResult.expected_checksum}</div>
                <div>Files Contained ({verifyResult.files_contained.length}): {verifyResult.files_contained.join(", ")}</div>
              </div>
            </div>
          )}

          {/* Sandbox Test Restore Results Panel */}
          {restoreResult && (
            <div
              className={`p-5 rounded-2xl border ${
                restoreResult.status === "SUCCESS" && restoreResult.integrity_check === "ok"
                  ? "bg-indigo-950/40 border-indigo-800/60 text-indigo-200"
                  : "bg-rose-950/30 border-rose-800/50 text-rose-200"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5 font-semibold text-sm">
                  <Database className="w-5 h-5 text-indigo-400" />
                  <span>Sandbox Restore Test: {restoreResult.message}</span>
                </div>
                <button onClick={() => setRestoreResult(null)} className="text-slate-400 hover:text-white">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="mt-3 text-xs font-mono space-y-1">
                <div>SQLite PRAGMA Integrity: <span className="font-bold text-emerald-400">{restoreResult.integrity_check || restoreResult.db_integrity}</span></div>
                <div>Manifest Validated: {restoreResult.has_manifest ? "YES" : "NO"}</div>
                {restoreResult.extracted_files && (
                  <div>Extracted Files: {restoreResult.extracted_files.join(", ")}</div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Protection Policies & Strict Invariants */}
      {activeTab === "policies" && (
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Retention Thresholds */}
          <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
            <div className="flex items-center gap-2 font-semibold text-slate-100">
              <HardDrive className="w-5 h-5 text-indigo-400" />
              <h4>{t("cleanup.policies.retentionTitle") || "Tiered Retention Thresholds"}</h4>
            </div>
            <div className="space-y-3 text-xs">
              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex justify-between items-center">
                <span className="font-medium text-slate-300">Temporary Scrapes & Raw Files (`tmp/`)</span>
                <span className="font-mono text-indigo-300 font-semibold">24 Hours</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex justify-between items-center">
                <span className="font-medium text-slate-300">Transient Cache (`cache/`)</span>
                <span className="font-mono text-indigo-300 font-semibold">24 Hours</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex justify-between items-center">
                <span className="font-medium text-slate-300">Failed Render Temp Files (`runtime/`)</span>
                <span className="font-mono text-indigo-300 font-semibold">3 Days (72 Hours)</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex justify-between items-center">
                <span className="font-medium text-slate-300">Unused Generated Asset Drafts</span>
                <span className="font-mono text-indigo-300 font-semibold">7 Days</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex justify-between items-center">
                <span className="font-medium text-slate-300">Final Published Video Media</span>
                <span className="font-mono text-indigo-300 font-semibold">30 Days after publish</span>
              </div>
              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex justify-between items-center">
                <span className="font-medium text-slate-300">Platform Export Archives (`exports/`)</span>
                <span className="font-mono text-indigo-300 font-semibold">30 Days</span>
              </div>
            </div>
          </div>

          {/* Absolute Invariants */}
          <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
            <div className="flex items-center gap-2 font-semibold text-slate-100">
              <ShieldAlert className="w-5 h-5 text-emerald-400" />
              <h4>{t("cleanup.policies.invariantsTitle") || "Strict Invariants (Never Deleted)"}</h4>
            </div>
            <p className="text-xs text-slate-400">
              The studio enforces automated database foreign reference checks prior to any file unlinking:
            </p>
            <div className="space-y-2 text-xs">
              {[
                "Active Media & Scene Assets (MediaAsset.file_path)",
                "Export Archives & Zip Packages (ExportPackage.archive_path)",
                "Rendered Videos, Voice Tracks & Timelines (MediaPackage)",
                "License Proofs & Copyright Metadata (AssetRightsRecord.uri)",
                "SQLite Databases (studio.sqlite, studio.sqlite-wal, -shm)",
                "Evidence Packets & Research Citations",
                "Creator Feedback Lessons & Attribution Benchmarks",
              ].map((inv, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-xl bg-slate-950/60 border border-emerald-950/40 text-emerald-300/90 flex items-center gap-2.5 font-medium"
                >
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>{inv}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Audit History */}
      {activeTab === "logs" && (
        <div className="mt-6 rounded-2xl bg-slate-900/60 border border-slate-800 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-800">
            <h3 className="font-semibold text-slate-100">Cleanup Audit History</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Cryptographically signed execution runs, file counts, and recoverable bytes tracking.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-900/90 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3 px-6">Run ID</th>
                  <th className="py-3 px-6">Mode</th>
                  <th className="py-3 px-6">Scanned</th>
                  <th className="py-3 px-6">Deleted</th>
                  <th className="py-3 px-6">Recovered</th>
                  <th className="py-3 px-6">Status</th>
                  <th className="py-3 px-6">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {auditLogs.length > 0 ? (
                  auditLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3.5 px-6 font-mono text-xs text-slate-300">
                        {log.run_id}
                      </td>
                      <td className="py-3.5 px-6">
                        <span
                          className={`px-2 py-0.5 rounded text-[11px] font-mono font-semibold ${
                            log.mode === "DRY_RUN"
                              ? "bg-blue-950/70 text-blue-300 border border-blue-800/40"
                              : "bg-emerald-950/70 text-emerald-300 border border-emerald-800/40"
                          }`}
                        >
                          {log.mode}
                        </span>
                      </td>
                      <td className="py-3.5 px-6 font-mono text-xs">{log.scanned_files_count}</td>
                      <td className="py-3.5 px-6 font-mono text-xs font-semibold text-slate-200">
                        {log.deleted_files_count}
                      </td>
                      <td className="py-3.5 px-6 font-mono text-xs text-emerald-400">
                        {formatBytes(log.recovered_bytes)}
                      </td>
                      <td className="py-3.5 px-6">
                        <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 text-slate-300">
                          {log.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-6 text-xs text-slate-400">
                        {log.created_at ? new Date(log.created_at).toLocaleString() : "N/A"}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-slate-500 text-sm">
                      No cleanup audit logs recorded yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl p-6">
            <div className="flex items-center gap-3 text-rose-400 mb-4">
              <AlertTriangle className="w-6 h-6" />
              <h3 className="text-lg font-bold text-slate-100">
                {t("cleanup.inspection.confirmTitle") || "Confirm Safe Deletion"}
              </h3>
            </div>
            <p className="text-sm text-slate-300 leading-relaxed">
              {t("cleanup.inspection.confirmMessage") ||
                "Are you sure you want to permanently delete eligible non-protected files? Active project media, database files, and export archives are strictly protected."}
            </p>
            <div className="mt-4 p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs font-mono text-slate-400">
              Recoverable space: <span className="text-emerald-400 font-semibold">{formatBytes(inspection?.recoverable_bytes || 0)}</span> ({inspection?.candidates_count || 0} files)
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-colors"
              >
                {t("cleanup.inspection.cancelBtn") || "Cancel"}
              </button>
              <button
                onClick={handleExecuteDelete}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-sm font-semibold transition-colors"
              >
                {t("cleanup.inspection.confirmBtn") || "Yes, Delete Files"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Backup Modal */}
      {showBackupModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-lg rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-2.5 font-bold text-slate-100">
                <Archive className="w-5 h-5 text-indigo-400" />
                <span>{t("cleanup.modal.createBackupTitle") || "Create Studio Backup Snapshot"}</span>
              </div>
              <button
                onClick={() => setShowBackupModal(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 mt-5">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                  {t("cleanup.modal.nameLabel") || "Backup Name (optional)"}
                </label>
                <input
                  type="text"
                  placeholder="e.g. pre_v1_milestone_backup"
                  value={backupForm.backup_name}
                  onChange={(e) => setBackupForm({ ...backupForm, backup_name: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                  {t("cleanup.modal.typeLabel") || "Backup Type"}
                </label>
                <select
                  value={backupForm.backup_type}
                  onChange={(e) => setBackupForm({ ...backupForm, backup_type: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
                >
                  <option value="FULL">FULL (SQLite DB + Brand + Niche + Platforms)</option>
                  <option value="SQLITE">SQLITE (Database & WAL only)</option>
                  <option value="CONFIG">CONFIG (Manifest & JSON settings only)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                  {t("cleanup.modal.notesLabel") || "Notes or Context"}
                </label>
                <textarea
                  rows={3}
                  placeholder="Description of this backup milestone..."
                  value={backupForm.notes}
                  onChange={(e) => setBackupForm({ ...backupForm, notes: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-sm focus:outline-none focus:border-indigo-500 resize-none"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-slate-800">
              <button
                onClick={() => setShowBackupModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-colors"
              >
                {t("common.cancel") || "Cancel"}
              </button>
              <button
                onClick={handleCreateBackup}
                disabled={creatingBackup}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition-colors disabled:opacity-50"
              >
                {creatingBackup ? t("cleanup.backups.creating") || "Creating..." : t("cleanup.modal.create") || "Create Snapshot"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

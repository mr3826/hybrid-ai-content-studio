"use client";

import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Boxes,
  CheckCircle2,
  Compass,
  Circle,
  AlertTriangle,
  Film,
  ShieldCheck,
  Share2,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { CockpitSummary, ContentFamilyDetail, StudioStatus } from "@/lib/api";
import {
  getCurrentWorkProgress,
  getNextCreatorStage,
  type CreatorStageId,
} from "@/lib/creator-workflow";
import { useLanguage } from "@/lib/LanguageContext";

interface CreatorWorkflowProps {
  summary: CockpitSummary | null;
  studioStatus: StudioStatus | null;
  activeFamiliesCount: number;
  currentFamily: ContentFamilyDetail | null;
  workflowLoadError: boolean;
  loading: boolean;
}

interface WorkflowCard {
  id: CreatorStageId;
  number: string;
  icon: LucideIcon;
  title: string;
  description: string;
  metric: number | string;
  metricLabel: string;
  href: string;
  actionLabel: string;
}

export function CreatorWorkflow({
  summary,
  studioStatus,
  activeFamiliesCount,
  currentFamily,
  workflowLoadError,
  loading,
}: CreatorWorkflowProps) {
  const { t } = useLanguage();
  const setupIncomplete = !studioStatus?.is_setup_completed;
  const topicsNeedingReview = summary?.needs_review ?? 0;
  const researchReady = summary?.research_ready ?? 0;
  const inProduction = summary?.in_production ?? 0;
  const readyToPublish = summary?.ready_to_publish ?? 0;
  const published = summary?.published ?? 0;

  const nextStage = getNextCreatorStage({
    studioSetupComplete: studioStatus?.is_setup_completed ?? false,
    topicsNeedingReview,
    researchReady,
    activeFamilies: activeFamiliesCount,
    inProduction,
    readyToPublish,
    published,
  });
  const currentWork = currentFamily ? getCurrentWorkProgress(currentFamily) : null;

  const cards: WorkflowCard[] = [
    {
      id: "discover",
      number: "01",
      icon: Compass,
      title: setupIncomplete
        ? t("workflow.setupTitle", "Set up your studio")
        : topicsNeedingReview > 0
          ? t("workflow.discoverReviewTitle", "Review topic opportunities")
          : t("workflow.discoverTitle", "Find new opportunities"),
      description: setupIncomplete
        ? t("workflow.setupDescription", "Set your single niche and brand before discovering topics.")
        : t("workflow.discoverDescription", "Check source coverage, then review and decide which topics may enter research."),
      metric: setupIncomplete ? t("workflow.setupNeeded", "Setup needed") : topicsNeedingReview,
      metricLabel: setupIncomplete
        ? t("workflow.studioProfile", "Niche and brand")
        : t("workflow.topicsWaiting", "topics waiting for a decision"),
      href: setupIncomplete ? "/settings" : topicsNeedingReview > 0 ? "/opportunities" : "/sources",
      actionLabel: setupIncomplete
        ? t("workflow.setupAction", "Configure studio")
        : topicsNeedingReview > 0
          ? t("workflow.reviewTopicsAction", "Review opportunities")
          : t("workflow.discoverAction", "Open sources"),
    },
    {
      id: "verify",
      number: "02",
      icon: ShieldCheck,
      title: t("workflow.verifyTitle", "Verify research"),
      description: t("workflow.verifyDescription", "Check sources, claims, and originality before creating content."),
      metric: researchReady,
      metricLabel: t("workflow.researchReadyMetric", "approved topics to research"),
      href: "/research",
      actionLabel: t("workflow.verifyAction", "Open research"),
    },
    {
      id: "create",
      number: "03",
      icon: Boxes,
      title: t("workflow.createTitle", "Create content families"),
      description: t("workflow.createDescription", "Turn verified research into a family of platform-ready drafts."),
      metric: activeFamiliesCount,
      metricLabel: t("workflow.familiesMetric", "active content families"),
      href: "/content-families",
      actionLabel: t("workflow.createAction", "Open content families"),
    },
    {
      id: "produce",
      number: "04",
      icon: Film,
      title: t("workflow.produceTitle", "Produce scenes and media"),
      description: t("workflow.produceDescription", "Prepare approved scripts as scenes, voice, subtitles, and media."),
      metric: inProduction,
      metricLabel: t("workflow.productionMetric", "opportunities in production"),
      href: "/content-families",
      actionLabel: t("workflow.produceAction", "Continue production"),
    },
    {
      id: "publish",
      number: "05",
      icon: Share2,
      title: t("workflow.publishTitle", "Complete final quality review"),
      description: t("workflow.publishDescription", "Pass the human QC gate, then prepare a manual publishing package."),
      metric: readyToPublish,
      metricLabel: t("workflow.publishMetric", "opportunities ready to publish"),
      href: readyToPublish > 0 ? "/quality-gate" : "/publishing",
      actionLabel: readyToPublish > 0
        ? t("workflow.qualityAction", "Open final QC")
        : t("workflow.publishAction", "Open publishing"),
    },
    {
      id: "learn",
      number: "06",
      icon: BarChart3,
      title: t("workflow.learnTitle", "Learn from performance"),
      description: t("workflow.learnDescription", "Review results and apply feedback only after your approval."),
      metric: published,
      metricLabel: t("workflow.publishedMetric", "opportunities published manually"),
      href: "/analytics",
      actionLabel: t("workflow.learnAction", "Review analytics"),
    },
  ];

  return (
    <section aria-labelledby="creator-workflow-title" className="space-y-4">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 id="creator-workflow-title" className="text-lg font-bold text-white">
            {t("workflow.title", "Creator workflow")}
          </h2>
          <p className="text-xs text-zinc-400 mt-1">
            {t("workflow.subtitle", "Move through six stages. Each decision stays in your hands.")}
          </p>
        </div>
        <span className="inline-flex items-center gap-2 self-start sm:self-auto rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-300">
          {t("workflow.nextActionLabel", "Next action")}
          <span aria-hidden="true">·</span>
          {t(`workflow.${nextStage}`, cards.find((card) => card.id === nextStage)?.title ?? "Discover")}
        </span>
      </div>

      <section
        aria-labelledby="current-work-title"
        className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4 sm:p-5"
      >
        <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h3 id="current-work-title" className="text-sm font-bold text-white">
              {t("workflow.currentWorkTitle", "Current work")}
            </h3>
            <p className="mt-1 text-xs text-slate-400">
              {t("workflow.currentWorkSubtitle", "Progress comes from saved content and approval states.")}
            </p>
          </div>
          {currentWork && (
            <span className="inline-flex items-center gap-1.5 self-start rounded-full border border-slate-700 bg-slate-950/70 px-3 py-1 text-xs font-semibold text-slate-300 sm:self-auto">
              {t(`workflow.${currentWork.stage}`, currentWork.stage)}
              <span aria-hidden="true">·</span>
              {t(
                `workflow.itemStatuses.${currentWork.status.toLowerCase()}`,
                currentWork.status.replaceAll("_", " ")
              )}
            </span>
          )}
        </div>

        {loading ? (
          <div
            role="status"
            aria-label={t("workflow.currentWorkLoading", "Loading saved creator progress")}
            aria-busy="true"
            className="mt-4 grid gap-3 rounded-xl border border-slate-800 bg-slate-950/45 p-4 sm:grid-cols-2"
          >
            <div className="h-14 animate-pulse rounded-lg bg-slate-800/60" />
            <div className="h-14 animate-pulse rounded-lg bg-slate-800/60" />
          </div>
        ) : workflowLoadError ? (
          <div role="alert" className="mt-4 rounded-xl border border-rose-500/30 bg-rose-950/25 p-4">
            <p className="text-sm text-rose-200">
              {t("workflow.currentWorkLoadError", "Current work could not be loaded. Open the content family list to check saved status.")}
            </p>
            <Link
              href="/content-families"
              className="mt-3 inline-flex min-h-11 items-center gap-2 rounded-lg border border-rose-500/30 px-3 text-xs font-semibold text-rose-100 hover:bg-rose-500/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-400"
            >
              {t("workflow.openFamiliesAction", "Open content families")}
              <ArrowRight aria-hidden="true" className="h-4 w-4" />
            </Link>
          </div>
        ) : currentFamily && currentWork ? (
          <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(18rem,0.8fr)]">
            <div className="min-w-0 space-y-3">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                  {t("workflow.currentFamily", "Current content family")}
                </p>
                <h4 className="mt-1 break-words text-base font-bold text-white">{currentFamily.title}</h4>
              </div>
              {currentWork.item ? (
                <p className="break-words text-xs text-slate-300">
                  <span className="font-semibold text-slate-400">{t("workflow.currentItem", "Current item")}: </span>
                  {currentWork.item.working_title}
                </p>
              ) : (
                <p className="text-xs text-slate-300">
                  {t("workflow.noCurrentItem", "No content item has been added to this family yet.")}
                </p>
              )}
              <div className={`rounded-xl border p-3 ${
                currentWork.blocker
                  ? "border-amber-500/30 bg-amber-950/20"
                  : "border-indigo-500/25 bg-indigo-950/20"
              }`}>
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                  {t("workflow.pendingRequirement", "Next requirement")}
                </p>
                <p className={`mt-1 text-xs leading-relaxed ${currentWork.blocker ? "text-amber-200" : "text-slate-200"}`}>
                  {currentWork.blocker
                    ? t(`workflow.blockers.${currentWork.blocker}`, "A saved prerequisite needs attention before this item can continue.")
                    : t(`workflow.nextSteps.${currentWork.action}`, "Continue from the current saved status.")}
                </p>
              </div>
              <Link
                href={currentWork.actionHref}
                className="inline-flex min-h-11 w-full items-center justify-between gap-2 rounded-lg border border-indigo-500/30 bg-indigo-600/15 px-3 text-xs font-semibold text-indigo-100 transition hover:bg-indigo-600/25 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 sm:w-auto sm:min-w-56"
              >
                <span>{t(`workflow.actions.${currentWork.action}`, "Continue current work")}</span>
                <ArrowRight aria-hidden="true" className="h-4 w-4 shrink-0" />
              </Link>
            </div>

            <div className="min-w-0 rounded-xl border border-slate-800 bg-slate-950/45 p-3">
              <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                {t("workflow.completedEvidence", "Saved progress")}
              </p>
              <ol className="grid grid-cols-1 gap-1.5 sm:grid-cols-2 xl:grid-cols-1">
                {currentWork.checkpoints.map((checkpoint) => {
                  const CheckpointIcon = checkpoint.complete ? CheckCircle2 : Circle;
                  return (
                    <li
                      key={checkpoint.id}
                      data-checkpoint={checkpoint.id}
                      data-complete={checkpoint.complete ? "true" : "false"}
                      className="flex min-w-0 items-center gap-2 text-xs"
                    >
                      <CheckpointIcon
                        aria-hidden="true"
                        className={`h-4 w-4 shrink-0 ${checkpoint.complete ? "text-emerald-400" : "text-slate-600"}`}
                      />
                      <span className={checkpoint.complete ? "text-slate-200" : "text-slate-500"}>
                        {t(`workflow.checkpoints.${checkpoint.id}`, checkpoint.id)}
                      </span>
                    </li>
                  );
                })}
              </ol>
            </div>
          </div>
        ) : (
          <div className="mt-4 flex flex-col gap-3 rounded-xl border border-dashed border-slate-700 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <AlertTriangle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
              <div>
                <h4 className="text-sm font-semibold text-slate-200">
                  {t("workflow.noCurrentWorkTitle", "No active content family")}
                </h4>
                <p className="mt-1 text-xs leading-relaxed text-slate-400">
                  {t("workflow.noCurrentWorkDescription", "Review an opportunity and approve it for research to begin a new content journey.")}
                </p>
              </div>
            </div>
            <Link
              href="/opportunities"
              className="inline-flex min-h-11 shrink-0 items-center justify-between gap-2 rounded-lg border border-slate-700 px-3 text-xs font-semibold text-slate-200 hover:border-indigo-500/50 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
            >
              {t("workflow.reviewOpportunitiesAction", "Review opportunities")}
              <ArrowRight aria-hidden="true" className="h-4 w-4" />
            </Link>
          </div>
        )}
      </section>

      {loading ? (
        <div
          aria-label={t("workflow.loading", "Loading creator workflow")}
          aria-busy="true"
          className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3"
        >
          {cards.map((card) => (
            <div key={card.id} className="h-40 animate-pulse rounded-2xl border border-zinc-800 bg-zinc-900/50" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {cards.map((card) => {
            const Icon = card.icon;
            const isNext = card.id === nextStage;
            return (
              <article
                key={card.id}
                data-workflow-stage={card.id}
                data-next-action={isNext ? "true" : "false"}
                className={`flex min-w-0 flex-col rounded-2xl border p-4 transition-colors ${
                  isNext
                    ? "border-indigo-500/50 bg-indigo-950/25 shadow-lg shadow-indigo-950/20"
                    : "border-zinc-800 bg-zinc-900/50"
                }`}
              >
                <div className="flex min-w-0 items-start justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${
                      isNext
                        ? "border-indigo-500/30 bg-indigo-500/10 text-indigo-300"
                        : "border-zinc-700 bg-zinc-800/70 text-zinc-300"
                    }`}>
                      <Icon aria-hidden="true" className="h-5 w-5" />
                    </span>
                    <div className="min-w-0">
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
                        {card.number} · {t(`workflow.${card.id}`, card.id)}
                      </p>
                      <p className="truncate text-xs text-zinc-400">
                        {card.metric}
                        {" "}{card.metricLabel}
                      </p>
                    </div>
                  </div>
                  {isNext && (
                    <span className="shrink-0 rounded-full bg-indigo-500/15 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-indigo-300">
                      {t("workflow.nextBadge", "Next")}
                    </span>
                  )}
                </div>
                <h3 className="mt-4 text-sm font-bold text-white">{card.title}</h3>
                <p className="mt-1 min-h-10 text-xs leading-relaxed text-zinc-400">{card.description}</p>
                <Link
                  href={card.href}
                  className="mt-3 inline-flex min-h-11 items-center justify-between gap-2 rounded-lg border border-zinc-700 bg-zinc-950/60 px-3 text-xs font-semibold text-zinc-200 transition hover:border-indigo-500/50 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
                >
                  <span>{card.actionLabel}</span>
                  <ArrowRight aria-hidden="true" className="h-4 w-4 shrink-0" />
                </Link>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

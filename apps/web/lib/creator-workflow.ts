import type { ContentChildItem, ContentFamilyDetail } from "./api";

export type CreatorStageId = "discover" | "verify" | "create" | "produce" | "publish" | "learn";

export interface CreatorWorkflowSnapshot {
  studioSetupComplete: boolean;
  topicsNeedingReview: number;
  researchReady: number;
  activeFamilies: number;
  inProduction: number;
  readyToPublish: number;
  published: number;
}

export type CurrentWorkActionId =
  | "approveFamily"
  | "addItem"
  | "openResearch"
  | "openOriginality"
  | "selectEvidence"
  | "generateScript"
  | "reviewScript"
  | "produceMedia"
  | "finalQc"
  | "prepareExport"
  | "publishManually"
  | "reviewAnalytics"
  | "reviewRejected"
  | "openFamily";

export type CurrentWorkBlockerId =
  | "familyApproval"
  | "researchPacket"
  | "originalityPlan"
  | "verifiedEvidence"
  | "rejectedItem";

export type CurrentWorkCheckpointId =
  | "topicLinked"
  | "researchLinked"
  | "originalityLinked"
  | "scriptApproved"
  | "finalQcApproved"
  | "exported"
  | "publicationRecorded";

export interface CurrentWorkProgress {
  stage: CreatorStageId;
  status: string;
  item: ContentChildItem | null;
  action: CurrentWorkActionId;
  actionHref: string;
  blocker: CurrentWorkBlockerId | null;
  checkpoints: Array<{ id: CurrentWorkCheckpointId; complete: boolean }>;
}

const SCRIPT_APPROVED_STATES = new Set([
  "SCRIPT_APPROVED",
  "READY_FOR_EXPORT",
  "FINAL_APPROVED",
  "EXPORTED",
  "READY_TO_PUBLISH",
  "PARTIALLY_PUBLISHED",
  "PUBLISHED",
]);

const FINAL_QC_APPROVED_STATES = new Set([
  "FINAL_APPROVED",
  "EXPORTED",
  "READY_TO_PUBLISH",
  "PARTIALLY_PUBLISHED",
  "PUBLISHED",
]);

const EXPORTED_STATES = new Set([
  "EXPORTED",
  "READY_TO_PUBLISH",
  "PARTIALLY_PUBLISHED",
  "PUBLISHED",
]);

const TERMINAL_ITEM_STATES = new Set(["PUBLISHED", "REJECTED"]);

function currentItemFor(family: ContentFamilyDetail): ContentChildItem | null {
  const activeItem = family.items.find(
    (item) => !TERMINAL_ITEM_STATES.has(item.status.toUpperCase())
  );
  if (activeItem) return activeItem;
  return family.items.length ? family.items[family.items.length - 1] : null;
}

function checkpointsFor(family: ContentFamilyDetail, item: ContentChildItem | null) {
  const itemStatus = item?.status.toUpperCase() ?? "";
  return [
    { id: "topicLinked" as const, complete: Boolean(family.topic_id) },
    { id: "researchLinked" as const, complete: Boolean(family.research_packet_id) },
    { id: "originalityLinked" as const, complete: Boolean(family.originality_plan_id) },
    { id: "scriptApproved" as const, complete: SCRIPT_APPROVED_STATES.has(itemStatus) },
    { id: "finalQcApproved" as const, complete: FINAL_QC_APPROVED_STATES.has(itemStatus) },
    { id: "exported" as const, complete: EXPORTED_STATES.has(itemStatus) },
    {
      id: "publicationRecorded" as const,
      complete: itemStatus === "PUBLISHED" || itemStatus === "PARTIALLY_PUBLISHED",
    },
  ];
}

export function getCurrentWorkProgress(family: ContentFamilyDetail): CurrentWorkProgress {
  const item = currentItemFor(family);
  const familyStatus = family.status.toUpperCase();
  const itemStatus = item?.status.toUpperCase() ?? "";
  const checkpoints = checkpointsFor(family, item);
  const familyHref = `/content-families/${encodeURIComponent(family.id)}`;
  const itemScriptHref = item
    ? `/script-studio/${encodeURIComponent(item.id)}`
    : familyHref;
  const itemPublishingHref = item
    ? `/publishing/${encodeURIComponent(item.id)}`
    : "/publishing";

  if (familyStatus === "DRAFT") {
    return {
      stage: "create",
      status: familyStatus,
      item,
      action: "approveFamily",
      actionHref: familyHref,
      blocker: "familyApproval",
      checkpoints,
    };
  }

  if (!item) {
    return {
      stage: "create",
      status: familyStatus,
      item: null,
      action: "addItem",
      actionHref: familyHref,
      blocker: null,
      checkpoints,
    };
  }

  if (itemStatus === "PLANNED" || itemStatus === "DRAFT") {
    if (!family.research_packet_id) {
      return {
        stage: "verify",
        status: itemStatus,
        item,
        action: "openResearch",
        actionHref: "/research",
        blocker: "researchPacket",
        checkpoints,
      };
    }
    if (!family.originality_plan_id) {
      return {
        stage: "verify",
        status: itemStatus,
        item,
        action: "openOriginality",
        actionHref: "/originality",
        blocker: "originalityPlan",
        checkpoints,
      };
    }
    if (!item.evidence_selections?.some((selection) => selection.is_verified)) {
      return {
        stage: "verify",
        status: itemStatus,
        item,
        action: "selectEvidence",
        actionHref: familyHref,
        blocker: "verifiedEvidence",
        checkpoints,
      };
    }
    return {
      stage: "create",
      status: itemStatus,
      item,
      action: "generateScript",
      actionHref: itemScriptHref,
      blocker: null,
      checkpoints,
    };
  }

  if (itemStatus === "SCRIPT_REVIEW") {
    return {
      stage: "create",
      status: itemStatus,
      item,
      action: "reviewScript",
      actionHref: itemScriptHref,
      blocker: null,
      checkpoints,
    };
  }

  if (itemStatus === "SCRIPT_APPROVED" || itemStatus === "READY_FOR_EXPORT") {
    return {
      stage: "produce",
      status: itemStatus,
      item,
      action: itemStatus === "SCRIPT_APPROVED" ? "produceMedia" : "finalQc",
      actionHref: itemStatus === "SCRIPT_APPROVED" ? "/scene-studio" : "/quality-gate",
      blocker: null,
      checkpoints,
    };
  }

  if (itemStatus === "FINAL_APPROVED") {
    return {
      stage: "publish",
      status: itemStatus,
      item,
      action: "prepareExport",
      actionHref: itemPublishingHref,
      blocker: null,
      checkpoints,
    };
  }

  if (EXPORTED_STATES.has(itemStatus)) {
    const isPublished = itemStatus === "PUBLISHED";
    return {
      stage: isPublished ? "learn" : "publish",
      status: itemStatus,
      item,
      action: isPublished ? "reviewAnalytics" : "publishManually",
      actionHref: isPublished ? "/analytics" : itemPublishingHref,
      blocker: null,
      checkpoints,
    };
  }

  if (itemStatus === "REJECTED") {
    return {
      stage: "create",
      status: itemStatus,
      item,
      action: "reviewRejected",
      actionHref: familyHref,
      blocker: "rejectedItem",
      checkpoints,
    };
  }

  return {
    stage: "create",
    status: itemStatus || familyStatus,
    item,
    action: "openFamily",
    actionHref: familyHref,
    blocker: null,
    checkpoints,
  };
}

export function getNextCreatorStage(snapshot: CreatorWorkflowSnapshot): CreatorStageId {
  if (!snapshot.studioSetupComplete || snapshot.topicsNeedingReview > 0) return "discover";
  if (snapshot.researchReady > 0) return "verify";
  if (snapshot.readyToPublish > 0) return "publish";
  if (snapshot.inProduction > 0) return "produce";
  if (snapshot.activeFamilies > 0) return "create";
  if (snapshot.published > 0) return "learn";
  return "discover";
}

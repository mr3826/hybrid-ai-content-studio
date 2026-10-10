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

export function getNextCreatorStage(snapshot: CreatorWorkflowSnapshot): CreatorStageId {
  if (!snapshot.studioSetupComplete || snapshot.topicsNeedingReview > 0) return "discover";
  if (snapshot.researchReady > 0) return "verify";
  if (snapshot.readyToPublish > 0) return "publish";
  if (snapshot.inProduction > 0) return "produce";
  if (snapshot.activeFamilies > 0) return "create";
  if (snapshot.published > 0) return "learn";
  return "discover";
}

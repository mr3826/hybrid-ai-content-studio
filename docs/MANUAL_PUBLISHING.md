# Manual Publishing Workflow Guide

## 1. Overview
The Fresh Local AI Content Studio implements a human-driven publishing model in V1. When a content project reaches `FINAL_APPROVED` and is exported, the **Platform Launcher** provides a distraction-free control panel to push content to YouTube, Facebook, Instagram, and TikTok.

## 2. Platform Action Cards

### YouTube
- `[Copy Title]`
- `[Copy Description]`
- `[Copy Tags / Hashtags]`
- `[Open YouTube Studio]` → Opens `https://studio.youtube.com/` in user's browser

### Facebook
- `[Copy Caption]`
- `[Open Facebook Page]` → Opens configured Facebook publishing URL

### Instagram
- `[Copy Caption]`
- `[Open Instagram]` → Opens `https://www.instagram.com/`

### TikTok
- `[Copy Caption]`
- `[Open TikTok Upload]` → Opens `https://www.tiktok.com/upload`

## 3. Publication State Machine
Platforms are tracked **independently**. A post can be published to YouTube while remaining pending on TikTok.

States per platform:
- `NOT_READY`: Media or platform metadata incomplete
- `READY`: Export package ready for upload
- `PUBLISHED`: User confirmed upload and recorded post URL
- `SKIPPED`: User intentionally bypassed this platform for this project

## 4. Verification Check
After marking a platform published, the studio prompts for:
- Published Post URL
- Platform Post ID (optional)
- Initial publication timestamp
- Editorial notes

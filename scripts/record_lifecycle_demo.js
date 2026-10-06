const path = require('path');
const fs = require('fs');
const { chromium } = require('../apps/web/node_modules/playwright');
const { execSync } = require('child_process');

const ARTIFACT_DIR = path.resolve('C:/Users/ahmee/.gemini/antigravity-ide/brain/e5b8600b-81d2-4266-b7a5-c2ff32d7be75');
const RECORDINGS_TEMP = path.join(__dirname, 'temp_recording');

if (!fs.existsSync(RECORDINGS_TEMP)) {
  fs.mkdirSync(RECORDINGS_TEMP, { recursive: true });
}

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function updateHud(page, stepNum, title, what, why) {
  await page.evaluate(({ stepNum, title, what, why }) => {
    let hud = document.getElementById('demo-hud');
    if (!hud) {
      hud = document.createElement('div');
      hud.id = 'demo-hud';
      hud.style.position = 'fixed';
      hud.style.top = '12px';
      hud.style.left = '50%';
      hud.style.transform = 'translateX(-50%)';
      hud.style.zIndex = '999999';
      hud.style.background = 'rgba(15, 23, 42, 0.95)';
      hud.style.border = '1px solid rgba(99, 102, 241, 0.6)';
      hud.style.backdropFilter = 'blur(12px)';
      hud.style.color = '#f8fafc';
      hud.style.padding = '10px 20px';
      hud.style.borderRadius = '12px';
      hud.style.boxShadow = '0 10px 25px -5px rgba(0, 0, 0, 0.6), 0 0 15px rgba(99, 102, 241, 0.3)';
      hud.style.fontFamily = 'system-ui, -apple-system, sans-serif';
      hud.style.width = '750px';
      hud.style.maxWidth = '90vw';
      hud.style.pointerEvents = 'none';
      hud.style.transition = 'all 0.3s ease-in-out';
      document.body.appendChild(hud);
    }

    hud.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 6px; margin-bottom: 6px;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="background: #4f46e5; color: white; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.5px;">STEP ${stepNum}</span>
          <span style="font-weight: 700; font-size: 14px; color: #e0e7ff;">${title}</span>
        </div>
        <span style="font-size: 11px; color: #10b981; font-weight: 600; display: flex; align-items: center; gap: 4px;">
          <span style="width: 6px; height: 6px; background: #10b981; border-radius: 50%; display: inline-block;"></span>
          LIVE STUDIO WALKTHROUGH
        </span>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 11px; line-height: 1.4;">
        <div><strong style="color: #93c5fd;">WHAT:</strong> <span style="color: #cbd5e1;">${what}</span></div>
        <div><strong style="color: #fde047;">WHY:</strong> <span style="color: #cbd5e1;">${why}</span></div>
      </div>
    `;
  }, { stepNum, title, what, why });
}

async function injectCursorFollower(page) {
  await page.evaluate(() => {
    let cursor = document.getElementById('demo-cursor');
    if (!cursor) {
      cursor = document.createElement('div');
      cursor.id = 'demo-cursor';
      cursor.style.width = '20px';
      cursor.style.height = '20px';
      cursor.style.borderRadius = '50%';
      cursor.style.background = 'rgba(239, 68, 68, 0.7)';
      cursor.style.border = '2px solid white';
      cursor.style.boxShadow = '0 0 10px rgba(239, 68, 68, 0.8)';
      cursor.style.position = 'fixed';
      cursor.style.pointerEvents = 'none';
      cursor.style.zIndex = '9999999';
      cursor.style.transform = 'translate(-50%, -50%)';
      cursor.style.transition = 'width 0.15s, height 0.15s, background-color 0.15s';
      document.body.appendChild(cursor);

      window.addEventListener('mousemove', (e) => {
        cursor.style.left = e.clientX + 'px';
        cursor.style.top = e.clientY + 'px';
      });

      window.addEventListener('mousedown', () => {
        cursor.style.width = '28px';
        cursor.style.height = '28px';
        cursor.style.background = 'rgba(245, 158, 11, 0.9)';
      });

      window.addEventListener('mouseup', () => {
        cursor.style.width = '20px';
        cursor.style.height = '20px';
        cursor.style.background = 'rgba(239, 68, 68, 0.7)';
      });
    }
  });
}

async function smoothScroll(page, distance, delay = 800) {
  await page.evaluate(async ({ distance, delay }) => {
    window.scrollBy({ top: distance, behavior: 'smooth' });
  }, { distance, delay });
  await sleep(delay);
}

(async () => {
  console.log('[1/10] Launching browser with high-res video recording...');
  const browser = await chromium.launch({
    channel: 'chrome',
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 1366, height: 768 },
    recordVideo: {
      dir: RECORDINGS_TEMP,
      size: { width: 1366, height: 768 }
    }
  });

  const page = await context.newPage();

  console.log('[2/10] Visiting Cockpit Dashboard...');
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
  await injectCursorFollower(page);
  await updateHud(
    page,
    '1 / 8',
    'Cockpit Dashboard & Bilingual Control',
    'Verifying the single-niche & single-brand configuration, engine health, and active signals.',
    'Studio ensures 100% brand consistency and prevents context contamination across runs.'
  );
  await sleep(3500);

  // Toggle language to Bengali and back
  console.log('[3/10] Demonstrating bilingual English / Bengali switcher...');
  try {
    const langBtn = await page.$('header button');
    if (langBtn) {
      await langBtn.click();
      await sleep(2500);
      await langBtn.click();
      await sleep(1500);
    }
  } catch (err) {
    console.log('Language button interaction noted');
  }

  await smoothScroll(page, 400, 1500);
  await smoothScroll(page, -400, 1500);

  // Step 2: Signal Discovery & Trends
  console.log('[4/10] Navigating to Trends Engine...');
  await page.goto('http://localhost:3000/trends', { waitUntil: 'networkidle' });
  await injectCursorFollower(page);
  await updateHud(
    page,
    '2 / 8',
    'Explainable Trends & Signal Discovery',
    'Aggregating verified RSS feeds, Google Trends velocity, and niche relevance filtering.',
    'Niche Guard discards irrelevant noise so creators only see high-impact trending signals.'
  );
  await sleep(3000);
  await smoothScroll(page, 350, 1200);

  // Step 3: Opportunity Cockpit & Gate 1
  console.log('[5/10] Navigating to Opportunities Cockpit (Gate 1)...');
  await page.goto('http://localhost:3000/opportunities', { waitUntil: 'networkidle' });
  await injectCursorFollower(page);
  await updateHud(
    page,
    '3 / 8',
    'Opportunity Cockpit — Human Quality Gate 1',
    'Reviewing algorithmic confidence, trend velocity, and topic relevance before approving.',
    'MANDATORY GATE: Auto-posting is strictly forbidden. Human creator must approve every topic.'
  );
  await sleep(3500);
  await smoothScroll(page, 350, 1200);

  // Step 4: Traceable Research Packets
  console.log('[6/10] Navigating to Research & Evidence Engine...');
  await page.goto('http://localhost:3000/research', { waitUntil: 'networkidle' });
  await injectCursorFollower(page);
  await updateHud(
    page,
    '4 / 8',
    'Traceable Research & Evidence Packets',
    'Extracting verified claims, source URLs, and citation anchors for the approved topic.',
    'Eliminates AI hallucinations by requiring every factual assertion to cite evidence.'
  );
  await sleep(3500);
  await smoothScroll(page, 400, 1500);

  // Step 5: Content Families & Script Studio
  console.log('[7/10] Navigating to Content Families Studio...');
  await page.goto('http://localhost:3000/content-families', { waitUntil: 'networkidle' });
  await injectCursorFollower(page);
  await updateHud(
    page,
    '5 / 8',
    'Content Family & Multi-Format Generation',
    'Atomizing verified research into Shorts, Reels, Long-form video scripts, and newsletters.',
    'Leverages Gemini AI to generate structured Hook, Core Body, and CTA tied to brand voice.'
  );
  await sleep(3500);
  await smoothScroll(page, 350, 1200);

  // Step 6: Scene & Media Studio
  console.log('[8/10] Navigating to Scene Studio...');
  await page.goto('http://localhost:3000/scene-studio', { waitUntil: 'networkidle' });
  await injectCursorFollower(page);
  await updateHud(
    page,
    '6 / 8',
    'Evidence-First Scene Studio & Visual Prompts',
    'Generating visual storyboard prompts, camera motions, b-roll descriptions, and scene timing.',
    'Allows creators to produce high-retention video assets aligned with the script beats.'
  );
  await sleep(3500);
  await smoothScroll(page, 400, 1500);

  // Step 7: Brand Quality Gate
  console.log('[9/10] Navigating to Brand Quality Gate (Gate 2)...');
  await page.goto('http://localhost:3000/quality-gate', { waitUntil: 'networkidle' });
  await injectCursorFollower(page);
  await updateHud(
    page,
    '7 / 8',
    'Brand Quality Gate — Human Quality Gate 2',
    'Verifying Originality Score, Repetition Penalty, Tone adherence, and Final Sign-off.',
    'Protects creator reputation by verifying novelty, vocabulary, and safety before publishing.'
  );
  await sleep(3500);
  await smoothScroll(page, 350, 1200);

  // Step 8: Manual Publishing Assistant
  console.log('[10/10] Navigating to Publishing Assistant...');
  await page.goto('http://localhost:3000/publishing', { waitUntil: 'networkidle' });
  await injectCursorFollower(page);
  await updateHud(
    page,
    '8 / 8',
    'Manual Publishing Assistant (Safe 1-Click Launch)',
    '1-click clipboard copy for Title, Description & Tags + direct platform launcher buttons.',
    'V1 uses safe manual publishing to avoid API bans and shadowbans from automated posting.'
  );
  await sleep(4000);
  await smoothScroll(page, 350, 1500);

  console.log('Finalizing recording...');
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
  await updateHud(
    page,
    'COMPLETE',
    'Content Studio Lifecycle Complete!',
    'From signal ingestion to verified research, script generation, brand QA, and export.',
    'Local-first, single-niche, single-brand studio powered by Gemini and SQLite WAL.'
  );
  await sleep(3000);

  await page.close();
  await context.close();
  await browser.close();

  console.log('Browser closed. Locating video recording file...');
  const files = fs.readdirSync(RECORDINGS_TEMP);
  const videoFile = files.find(f => f.endsWith('.webm'));
  if (!videoFile) {
    throw new Error('No video recording found in ' + RECORDINGS_TEMP);
  }

  const rawWebmPath = path.join(RECORDINGS_TEMP, videoFile);
  const outMp4Path = path.join(ARTIFACT_DIR, 'content_lifecycle_demo.mp4');
  const outWebmPath = path.join(ARTIFACT_DIR, 'content_lifecycle_demo.webm');

  console.log('Copying WebM recording to artifact directory...');
  fs.copyFileSync(rawWebmPath, outWebmPath);

  console.log('Transcoding to MP4 for maximum compatibility with FFmpeg...');
  try {
    execSync(`ffmpeg -y -i "${rawWebmPath}" -c:v libx264 -pix_fmt yuv420p -preset fast -crf 22 "${outMp4Path}"`, { stdio: 'inherit' });
    console.log('MP4 conversion successful:', outMp4Path);
  } catch (err) {
    console.warn('FFmpeg transcode error, WebM is preserved:', err.message);
  }

  console.log('Demo recording process completed successfully!');
})().catch(err => {
  console.error('Recording script failed:', err);
  process.exit(1);
});

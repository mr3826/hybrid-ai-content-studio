const path = require('path');
const fs = require('fs');
const { chromium } = require('../apps/web/node_modules/playwright');
const { execSync } = require('child_process');

const ARTIFACT_DIR = path.resolve('C:/Users/ahmee/.gemini/antigravity-ide/brain/e5b8600b-81d2-4266-b7a5-c2ff32d7be75');
const RECORDINGS_TEMP = path.join(__dirname, 'temp_reel_recording');

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
      hud.style.border = '1px solid rgba(236, 72, 153, 0.6)'; // Pink border for Reels
      hud.style.backdropFilter = 'blur(12px)';
      hud.style.color = '#f8fafc';
      hud.style.padding = '10px 20px';
      hud.style.borderRadius = '12px';
      hud.style.boxShadow = '0 10px 25px -5px rgba(0, 0, 0, 0.6), 0 0 15px rgba(236, 72, 153, 0.3)';
      hud.style.fontFamily = 'system-ui, -apple-system, sans-serif';
      hud.style.width = '780px';
      hud.style.maxWidth = '92vw';
      hud.style.pointerEvents = 'none';
      hud.style.transition = 'all 0.3s ease-in-out';
      document.body.appendChild(hud);
    }

    hud.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 6px; margin-bottom: 6px;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="background: linear-gradient(135deg, #ec4899, #8b5cf6); color: white; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.5px;">REEL CREATOR: STEP ${stepNum}</span>
          <span style="font-weight: 700; font-size: 14px; color: #fbcfe8;">${title}</span>
        </div>
        <span style="font-size: 11px; color: #f472b6; font-weight: 600; display: flex; align-items: center; gap: 4px;">
          <span style="width: 6px; height: 6px; background: #ec4899; border-radius: 50%; display: inline-block;"></span>
          VERTICAL 9:16 REEL PIPELINE
        </span>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 11px; line-height: 1.4;">
        <div><strong style="color: #f472b6;">WHAT:</strong> <span style="color: #cbd5e1;">${what}</span></div>
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
      cursor.style.background = 'rgba(236, 72, 153, 0.7)';
      cursor.style.border = '2px solid white';
      cursor.style.boxShadow = '0 0 10px rgba(236, 72, 153, 0.8)';
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
        cursor.style.background = 'rgba(236, 72, 153, 0.7)';
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
  console.log('[1/7] Launching browser to record Reel creation...');
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
  const itemId = '165ae90a-f2dc-4efb-9192-56ba89bab42d';

  // Step 1: Script Studio for the Reel
  console.log('[2/7] Opening Script Studio for the Reel item...');
  await page.goto(`http://localhost:3000/script-studio/${itemId}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await injectCursorFollower(page);
  await updateHud(
    page,
    '1 / 5',
    'Script Studio: Retention-Optimized Reel Script',
    'Reviewing the 5 vertical beats: Hook (0-5s), Problem Context, Evidence, Verdict, and CTA.',
    'Reels require an immediate 3-second pattern interrupt and evidence data to maximize retention.'
  );
  await sleep(3500);

  // Scroll through script sections
  await smoothScroll(page, 450, 1500);
  await sleep(2000);
  await smoothScroll(page, 450, 1500);
  await sleep(2000);
  await smoothScroll(page, -900, 1200);

  // Step 2: Scene Studio
  console.log('[3/7] Navigating to Scene Studio...');
  await page.goto('http://localhost:3000/scene-studio', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await injectCursorFollower(page);
  await updateHud(
    page,
    '2 / 5',
    'Scene Studio: 9-Scene Storyboard & Visual Priorities',
    'Decomposing the script into 9 visual scenes with screen recording, terminal, and chart cues.',
    'Aligns visual pacing with narration beats so the Reel never feels static or boring.'
  );
  await sleep(3500);
  await smoothScroll(page, 400, 1500);
  await sleep(2000);
  await smoothScroll(page, -400, 1200);

  // Step 3: Media Studio
  console.log('[4/7] Navigating to Media Studio...');
  await page.goto('http://localhost:3000/media-studio', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await injectCursorFollower(page);
  await updateHud(
    page,
    '3 / 5',
    'Media Studio: Voice Synthesis & 9:16 Vertical Render',
    'Master voice narration synthesized (42.5s), 26 timed subtitle cues generated, and 1080x1920 MP4 rendered.',
    'Local FFmpeg compiles the audio waveforms, timed captions, and vertical video offline.'
  );
  await sleep(3500);

  // Select item in dropdown and preview video
  try {
    const select = await page.$('select');
    if (select) {
      await select.selectOption(itemId);
      await sleep(2500);
    }
    await smoothScroll(page, 550, 1500);
    await page.evaluate(() => {
      const v = document.querySelector('video');
      if (v) v.play().catch(() => {});
    });
    await sleep(4000);
  } catch (e) {
    console.log('Video note:', e.message);
  }

  // Step 4: Quality Gate
  console.log('[5/7] Navigating to Quality Gate...');
  await page.goto('http://localhost:3000/quality-gate', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await injectCursorFollower(page);
  await updateHud(
    page,
    '4 / 5',
    'Brand Quality Gate: Reel Safety & Originality Sign-off',
    'Audit checks: Originality score verified, repetition penalty zero, and brand tone verified.',
    'Human Quality Gate guarantees you never post repetitive cliches or off-brand content.'
  );
  await sleep(3500);
  await smoothScroll(page, 350, 1200);

  // Step 5: Publishing Assistant
  console.log('[6/7] Navigating to Publishing Assistant...');
  await page.goto(`http://localhost:3000/publishing/${itemId}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await injectCursorFollower(page);
  await updateHud(
    page,
    '5 / 5',
    'Publishing Assistant: Instagram & Facebook Reel Package',
    '1-click copy for Reel Caption, Hashtags, and direct launch buttons for Instagram & Facebook.',
    'Manual 1-click clipboard publishing keeps your account safe from automated API shadowbans.'
  );
  await sleep(3500);

  // Click Copy Caption if present
  try {
    const copyBtns = await page.$$('button');
    for (const btn of copyBtns) {
      const text = await btn.innerText();
      if (text.includes('Copy') || text.includes('কপি')) {
        await btn.click();
        await sleep(1500);
        break;
      }
    }
  } catch (e) {
    console.log('Copy button note:', e.message);
  }

  await smoothScroll(page, 400, 1500);
  await sleep(2500);

  // Final summary
  await updateHud(
    page,
    'READY',
    'Reel Created Successfully!',
    'Export package generated: 1080x1920 MP4 video, 42.5s voice narration, SRT subtitles & captions.',
    'Ready for immediate upload to Instagram Reels, YouTube Shorts, and TikTok.'
  );
  await sleep(3000);

  console.log('[7/7] Closing browser and saving video recording...');
  await page.close();
  await context.close();
  await browser.close();

  const files = fs.readdirSync(RECORDINGS_TEMP);
  const videoFile = files.find(f => f.endsWith('.webm'));
  if (!videoFile) {
    throw new Error('No video recording found in ' + RECORDINGS_TEMP);
  }

  const rawWebmPath = path.join(RECORDINGS_TEMP, videoFile);
  const outMp4Path = path.join(ARTIFACT_DIR, 'reels_creation_screen_record.mp4');
  const outWebmPath = path.join(ARTIFACT_DIR, 'reels_creation_screen_record.webm');

  console.log('Copying WebM recording to artifact directory...');
  fs.copyFileSync(rawWebmPath, outWebmPath);

  console.log('Transcoding to MP4 with FFmpeg...');
  try {
    execSync(`ffmpeg -y -i "${rawWebmPath}" -c:v libx264 -pix_fmt yuv420p -preset fast -crf 22 "${outMp4Path}"`, { stdio: 'inherit' });
    console.log('MP4 Reel screen record saved successfully:', outMp4Path);
  } catch (err) {
    console.warn('FFmpeg transcode error, WebM preserved:', err.message);
  }

  console.log('Reel creation screen recording complete!');
})().catch(err => {
  console.error('Reel recording script failed:', err);
  process.exit(1);
});

    // ============================================================
    // STATE
    // ============================================================
    let cameraOn = false;
    let stream = null;

    // ============================================================
    // ACCENT COLOR HELPERS — theme-aware accent color application
    // ============================================================
    const DEFAULT_DARK  = { accent: '#4ade80', dim: 'rgba(74,222,128,0.12)', glow: 'rgba(74,222,128,0.35)' };
    const DEFAULT_LIGHT = { accent: '#4a7a64', dim: 'rgba(74,122,100,0.1)', glow: 'rgba(74,122,100,0.2)' };

    function applyAccent(colors) {
      const root = document.documentElement;
      root.style.setProperty('--accent', colors.accent);
      root.style.setProperty('--accent-dim', colors.dim);
      root.style.setProperty('--accent-glow', colors.glow);
      const app = document.getElementById('app');
      app.classList.add('color-shifting');
      setTimeout(() => app.classList.remove('color-shifting'), 700);
    }

    function reapplyCurrentVibe() {
      const theme = document.documentElement.getAttribute('data-theme');
      applyAccent(theme === 'dark' ? DEFAULT_DARK : DEFAULT_LIGHT);
    }

    // ============================================================
    // THEME
    // ============================================================
    function updateThemeToggleA11y() {
      const toggle = document.querySelector('.theme-toggle');
      if (!toggle) return;
      const isLight = document.documentElement.getAttribute('data-theme') === 'light';
      toggle.setAttribute('aria-checked', isLight ? 'true' : 'false');
    }

    function toggleTheme() {
      const html = document.documentElement;
      const newTheme = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      html.setAttribute('data-theme', newTheme);
      try { localStorage.setItem('signcraft-theme', newTheme); } catch (e) {}
      reapplyCurrentVibe();
      updateThemeToggleA11y();
    }

    (function() {
      let saved = null;
      try { saved = localStorage.getItem('signcraft-theme'); } catch (e) {}
      if (saved) document.documentElement.setAttribute('data-theme', saved);
      updateThemeToggleA11y();
    })();

    // ============================================================
    // CAMERA
    // ============================================================
    async function toggleCamera() {
      const video = document.getElementById('webcamVideo');
      const placeholder = document.getElementById('webcamPlaceholder');
      const startBtn = document.getElementById('camBtn');
      const stopBtn = document.getElementById('camStopBtn');
      const overlay = document.getElementById('webcamOverlay');
      const corners = document.querySelectorAll('.corner-deco');

      if (!cameraOn) {
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } }
          });
          video.srcObject = stream;
          video.style.display = 'block';
          placeholder.style.display = 'none';
          stopBtn.style.display = 'block';
          overlay.style.display = 'flex';
          corners.forEach(c => c.style.display = 'block');
          cameraOn = true;
          startFpsCounter();
          startASLDetection();
        } catch (err) {
          alert('Could not access camera. Please allow camera permissions.');
          console.error(err);
        }
      } else {
        if (challengeActive) quitChallenge();
        stopASLDetection();
        stream.getTracks().forEach(t => t.stop());
        video.srcObject = null;
        video.style.display = 'none';
        placeholder.style.display = 'flex';
        stopBtn.style.display = 'none';
        overlay.style.display = 'none';
        corners.forEach(c => c.style.display = 'none');
        cameraOn = false;
      }
    }

    let aslFramesReceived = 0;
    let aslFpsLastTime = performance.now();

    function updateAslFps() {
      aslFramesReceived++;
      const now = performance.now();
      if (now - aslFpsLastTime >= 1000) {
        document.getElementById('fpsTag').textContent = aslFramesReceived + ' fps';
        aslFramesReceived = 0;
        aslFpsLastTime = now;
      }
    }

    function startFpsCounter() {
      document.getElementById('fpsTag').textContent = '-- fps';
    }

    // ============================================================
    // ASL DETECTION — in-browser engine + display
    // ============================================================
    let aslEngine = null;
    let aslStartToken = 0;
    let isDetecting = false;

    async function startASLDetection() {
      if (aslEngine) return;
      const video = document.getElementById('webcamVideo');
      if (!video.srcObject) return;

      const myToken = ++aslStartToken;
      const engine = await window.__createEngine({
        video,
        onMessage: (msg) => handleASLMessage(msg),
      });

      if (myToken !== aslStartToken || !video.srcObject) {
        // Superseded by a stop/newer start while the engine was loading.
        engine.dispose();
        return;
      }

      aslEngine = engine;
      isDetecting = true;
      // Set mode for current tab
      if (activeTab === 'tutorial') {
        updateTutorialMode();
      }
      aslEngine.start();
    }

    function stopASLDetection() {
      aslStartToken++;
      isDetecting = false;
      if (aslEngine) {
        aslEngine.dispose();
        aslEngine = null;
      }
    }

    const HAND_CONNECTIONS = [
      [0,1],[1,2],[2,3],[3,4],
      [0,5],[5,6],[6,7],[7,8],
      [0,9],[9,10],[10,11],[11,12],
      [0,13],[13,14],[14,15],[15,16],
      [0,17],[17,18],[18,19],[19,20],
      [5,9],[9,13],[13,17],
    ];

    function drawHandLandmarks(landmarks) {
      const canvas = document.getElementById('handCanvas');
      const container = document.getElementById('webcamContainer');
      const video = document.getElementById('webcamVideo');
      const w = container.clientWidth;
      const h = container.clientHeight;
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, w, h);

      if (!landmarks || landmarks.length === 0) return;

      // Account for object-fit: cover — the video is scaled to fill the
      // container and cropped, so landmark coords (0-1) map to the full
      // rendered size, not the visible container size.
      const videoW = video.videoWidth || w;
      const videoH = video.videoHeight || h;
      const scale = Math.max(w / videoW, h / videoH);
      const renderedW = videoW * scale;
      const renderedH = videoH * scale;
      const offX = (renderedW - w) / 2;
      const offY = (renderedH - h) / 2;

      function mapX(x) { return x * renderedW - offX; }
      function mapY(y) { return y * renderedH - offY; }

      // Draw connections
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
      ctx.lineWidth = 2;
      for (const [i, j] of HAND_CONNECTIONS) {
        const [x1, y1] = landmarks[i];
        const [x2, y2] = landmarks[j];
        ctx.beginPath();
        ctx.moveTo(mapX(x1), mapY(y1));
        ctx.lineTo(mapX(x2), mapY(y2));
        ctx.stroke();
      }

      // Draw joints
      const accentColor = getComputedStyle(document.documentElement).getPropertyValue('--accent');
      for (const [x, y] of landmarks) {
        ctx.beginPath();
        ctx.arc(mapX(x), mapY(y), 5, 0, Math.PI * 2);
        ctx.fillStyle = accentColor;
        ctx.fill();
        ctx.strokeStyle = 'rgba(0, 0, 0, 0.5)';
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    }

    function handleASLMessage(msg) {
      if (msg.type === 'status') {
        updateAslFps();
        if (msg.landmarks) {
          drawHandLandmarks(msg.landmarks);
        } else {
          drawHandLandmarks(null);
        }
      }

      if (msg.type === 'detection') {
        // Check tutorial match
        checkTutorialDetection(msg);
        // Check challenge match
        checkChallengeDetection(msg);
      }
    }

    // ============================================================
    // TAB NAVIGATION
    // ============================================================
    let activeTab = 'tutorial';

    function switchTab(tab) {
      activeTab = tab;
      document.querySelectorAll('.tab-btn').forEach((btn, i) => {
        const tabs = ['tutorial', 'challenge', 'stats'];
        btn.classList.toggle('active', tabs[i] === tab);
      });
      document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
      document.getElementById('tab' + tab.charAt(0).toUpperCase() + tab.slice(1)).classList.add('active');

      // Set ASL mode based on active tab
      if (tab === 'tutorial') {
        updateTutorialMode();
      }
      // Hide challenge bar when not on challenge tab
      if (tab !== 'challenge' && challengeActive) {
        stopChallenge();
      }
      // Update stats display when switching to stats tab
      if (tab === 'stats') {
        renderStats();
        renderLeaderboard();
      }
    }

    // ============================================================
    // TUTORIAL
    // ============================================================
    const TUTORIAL_SIGNS = [
      // Letters A-Z
      { name: 'A', mode: 'letters', match: 'A', desc: 'Make a fist with your thumb resting on the side', img: 'signs/A.jpg' },
      { name: 'B', mode: 'letters', match: 'B', desc: 'Flat hand, fingers together pointing up, thumb tucked across palm', img: 'signs/B.jpg' },
      { name: 'C', mode: 'letters', match: 'C', desc: 'Curve your hand into a C shape', img: 'signs/C.jpg' },
      { name: 'D', mode: 'letters', match: 'D', desc: 'Index finger up, other fingers curl down to touch thumb', img: 'signs/D.jpg' },
      { name: 'E', mode: 'letters', match: 'E', desc: 'Curl all fingers down, thumb tucked under fingers', img: 'signs/E.jpg' },
      { name: 'F', mode: 'letters', match: 'F', desc: 'Index and thumb form a circle, other 3 fingers spread up', img: 'signs/F.jpg' },
      { name: 'G', mode: 'letters', match: 'G', desc: 'Index finger and thumb pointing sideways, parallel', img: 'signs/G.jpg' },
      { name: 'H', mode: 'letters', match: 'H', desc: 'Index and middle fingers extended sideways together', img: 'signs/H.jpg' },
      { name: 'I', mode: 'letters', match: 'I', desc: 'Make a fist with only your pinky raised', img: 'signs/I.jpg' },
      { name: 'J', mode: 'letters', match: 'J', desc: 'Start with pinky up, trace a J shape downward', img: 'signs/J.jpg' },
      { name: 'K', mode: 'letters', match: 'K', desc: 'Index and middle finger up in a V, thumb between them', img: 'signs/K.jpg' },
      { name: 'L', mode: 'letters', match: 'L', desc: 'L shape — index finger up, thumb out to the side', img: 'signs/L.jpg' },
      { name: 'M', mode: 'letters', match: 'M', desc: 'Fist with thumb tucked under three fingers', img: 'signs/M.jpg' },
      { name: 'N', mode: 'letters', match: 'N', desc: 'Fist with thumb tucked under two fingers', img: 'signs/N.jpg' },
      { name: 'O', mode: 'letters', match: 'O', desc: 'All fingertips touch thumb forming an O', img: 'signs/O.jpg' },
      { name: 'P', mode: 'letters', match: 'P', desc: 'Index and middle finger pointing down, thumb sticking out between them', img: 'signs/P.jpg' },
      { name: 'Q', mode: 'letters', match: 'Q', desc: 'Thumb and index finger pointing downward together, other fingers curled in', img: 'signs/Q.jpg' },
      { name: 'R', mode: 'letters', match: 'R', desc: 'Cross your index and middle fingers', img: 'signs/R.jpg' },
      { name: 'S', mode: 'letters', match: 'S', desc: 'Fist with thumb over the front of fingers', img: 'signs/S.jpg' },
      { name: 'T', mode: 'letters', match: 'T', desc: 'Fist with thumb tucked between index and middle finger', img: 'signs/T.jpg' },
      { name: 'U', mode: 'letters', match: 'U', desc: 'Index and middle fingers up together, side by side', img: 'signs/U.jpg' },
      { name: 'V', mode: 'letters', match: 'V', desc: 'Index and middle fingers spread apart — peace sign', img: 'signs/V.jpg' },
      { name: 'W', mode: 'letters', match: 'W', desc: 'Index, middle, and ring fingers spread up', img: 'signs/W.jpg' },
      { name: 'X', mode: 'letters', match: 'X', desc: 'Fist with index finger hooked/bent', img: 'signs/X.jpg' },
      { name: 'Y', mode: 'letters', match: 'Y', desc: 'Extend thumb and pinky, curl other fingers down', img: 'signs/Y.jpg' },
      { name: 'Z', mode: 'letters', match: 'Z', desc: 'Trace a Z in the air with your index finger', img: 'signs/Z.jpg' },
      // Words
      { name: 'HELLO', mode: 'words', match: 'HELLO', desc: 'Flat hand at forehead, move outward like a salute wave', img: 'signs/HELLO.mp4' },
      { name: 'GOODBYE', mode: 'words', match: 'GOODBYE', desc: 'Open hand, wave by folding fingers down repeatedly', img: 'signs/GOODBYE.mp4' },
      { name: 'OK', mode: 'words', match: 'OK', desc: 'Touch index finger and thumb to form a circle', img: 'signs/OK.mp4' },
      { name: 'THANK YOU', mode: 'words', match: 'THANK_YOU', desc: 'Touch chin with fingertips, then move hand outward and down', img: 'signs/THANK_YOU.mp4' },
      { name: 'I LOVE YOU', mode: 'words', match: 'I_LOVE_YOU', desc: 'Extend pinky, index finger, and thumb — like a rock sign with thumb out', img: 'signs/I_LOVE_YOU.mp4' },
      { name: 'SIGMA', mode: 'words', match: 'SIGMA', desc: 'S sign on one hand moving up while the other hand points downwards', img: 'signs/SIGMA.mp4' },
      { name: 'BADDIE', mode: 'words', match: 'BADDIE', desc: 'Quiet coyote to the side of the jaw', img: 'signs/BADDIE.mp4' },
      { name: 'RIZZ', mode: 'words', match: 'RIZZ', desc: 'R sign moving from the side of the jaw towards the front', img: 'signs/RIZZ.mp4' },
      { name: '6-7', mode: 'words', match: '6_7', desc: 'Alternate raising and lowering your right and left hand quickly', img: 'signs/6_7.mp4' },
    ];

    let tutorialIndex = 0;
    let tutorialCorrect = false;
    let tutorialAdvanceTimer = null;

    function initTutorial() {
      // Always start fresh on page load
      tutorialIndex = 0;
      renderTutorial();
    }

    function renderTutorial() {
      const container = document.getElementById('tutorialCardContainer');
      const progressFill = document.getElementById('tutorialProgressFill');
      const progressText = document.getElementById('tutorialProgressText');

      const total = TUTORIAL_SIGNS.length;
      const pct = (tutorialIndex / total) * 100;
      progressFill.style.width = pct + '%';
      progressText.textContent = tutorialIndex + '/' + total;

      // Completed all signs
      if (tutorialIndex >= total) {
        container.innerHTML = `
          <div class="tutorial-complete">
            <img src="happyllama.webp" style="width:120px;height:120px;object-fit:contain;image-rendering:pixelated;" alt="Happy llama">
            <div class="complete-title">Tutorial Complete!</div>
            <div class="complete-sub">You've learned all ${total} signs.<br>Try Challenge mode!</div>
            <button class="cam-btn" style="margin-top:20px;" onclick="resetTutorial()">Restart Tutorial</button>
          </div>
        `;
        return;
      }

      const sign = TUTORIAL_SIGNS[tutorialIndex];
      tutorialCorrect = false;

      container.innerHTML = `
        <div class="tutorial-card" id="tutorialCard">
          <div class="tutorial-sign-name">${sign.name}</div>
          <div class="tutorial-image">
            ${sign.img.endsWith('.mp4')
              ? `<video src="${sign.img}" autoplay loop muted playsinline style="width:100%;height:100%;object-fit:contain;"></video>`
              : `<img src="${sign.img}" onerror="this.style.display='none';this.nextElementSibling.style.display='block'" alt="${sign.name}">
            <div class="placeholder-letter" style="display:none">${sign.name.charAt(0)}</div>`
            }
          </div>
          <div class="tutorial-desc">${sign.desc}</div>
          <div class="tutorial-status waiting" id="tutorialStatus"></div>
          <div class="tutorial-actions">
            <button class="skip-btn" onclick="resetTutorial()">Reset</button>
            <button class="skip-btn" onclick="skipTutorialSign()">Skip</button>
          </div>
        </div>
      `;

      updateTutorialMode();
    }

    function updateTutorialMode() {
      if (tutorialIndex >= TUTORIAL_SIGNS.length) return;
      const sign = TUTORIAL_SIGNS[tutorialIndex];
      if (aslEngine) aslEngine.setMode(sign.mode);
    }

    function checkTutorialDetection(msg) {
      if (activeTab !== 'tutorial') return;
      if (tutorialCorrect) return;
      if (tutorialIndex >= TUTORIAL_SIGNS.length) return;

      const sign = TUTORIAL_SIGNS[tutorialIndex];

      if (msg.type === 'detection') {
        let detected = '';
        if (msg.kind === 'letter') detected = msg.value;
        else if (msg.kind === 'word') detected = msg.word || msg.value;

        if (detected === sign.match) {
          tutorialCorrect = true;
          const card = document.getElementById('tutorialCard');
          const status = document.getElementById('tutorialStatus');
          if (card) card.classList.add('correct');
          if (status) {
            status.className = 'tutorial-status correct';
            status.textContent = 'Correct!';
          }
          // Auto-advance after 1.5s
          tutorialAdvanceTimer = setTimeout(() => advanceTutorial(), 1500);
        }
      }
    }

    function advanceTutorial() {
      if (tutorialAdvanceTimer) { clearTimeout(tutorialAdvanceTimer); tutorialAdvanceTimer = null; }
      tutorialIndex++;
      renderTutorial();
    }

    function skipTutorialSign() {
      if (tutorialAdvanceTimer) { clearTimeout(tutorialAdvanceTimer); tutorialAdvanceTimer = null; }
      tutorialIndex++;
      renderTutorial();
    }

    function resetTutorial() {
      tutorialIndex = 0;
      renderTutorial();
    }

    // Initialize tutorial on page load
    initTutorial();

    // ============================================================
    // CHALLENGE MODE
    // ============================================================
    const CHALLENGE_LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
    const CHALLENGE_WORDS = ['HELLO', 'GOODBYE', 'OK', 'THANK_YOU', 'I_LOVE_YOU', 'SIGMA', 'BADDIE', 'RIZZ', '6_7'];

    let challengeDifficulty = 'easy';
    let challengeActive = false;
    let challengeCorrect = 0;
    let challengeWrong = 0;
    let challengeScore = 0; // For unlimited mode
    let challengeItems = []; // {label, x, width, wrongCount, state}
    let challengeAnimFrame = null;
    let challengeLastTime = 0;

    const CHALLENGE_WIN_EASY = 10;
    const CHALLENGE_WIN_HARD = 15;
    const CHALLENGE_LOSE = 10;
    const POINTS_PER_CORRECT = 10;

    // Session stats tracking
    let sessionStats = {}; // {letter/word: wrongCount}
    // Base speeds per difficulty — slider multiplies these
    const BASE_SPEED_EASY = 45;
    const BASE_SPEED_HARD = 65;
    const SPEED_MULTIPLIERS = [0.5, 0.75, 1.0, 1.3, 1.6]; // slider 1-5
    const SPEED_LABELS = ['Very Slow', 'Slow', 'Normal', 'Fast', 'Very Fast'];
    const BASE_SPACING = 100;
    const WRONG_ATTEMPT_LIMIT = 8;
    let challengeLastLabel = null;
    let challengeSpeedMult = 1.0;

    function updateSpeedLabel() {
      const slider = document.getElementById('challengeSpeedSlider');
      const idx = parseInt(slider.value) - 1;
      document.getElementById('speedLabel').textContent = SPEED_LABELS[idx];
    }

    function setChallengeDifficulty(diff) {
      challengeDifficulty = diff;
      document.getElementById('diffEasy').classList.toggle('active', diff === 'easy');
      document.getElementById('diffHard').classList.toggle('active', diff === 'hard');
      document.getElementById('diffUnlimited').classList.toggle('active', diff === 'unlimited');
      
      if (diff === 'unlimited') {
        document.getElementById('challengeDiffDesc').innerHTML =
          'Infinite mode &mdash; 10 points per correct, game over at 10 wrong';
      } else {
        const winTarget = diff === 'easy' ? CHALLENGE_WIN_EASY : CHALLENGE_WIN_HARD;
        const desc = diff === 'easy' ? 'Letters only (A-Z)' : 'Letters + Words';
        document.getElementById('challengeDiffDesc').innerHTML =
          `${desc} &mdash; Get ${winTarget} correct to win`;
      }
    }

    function getRandomChallengeItem() {
      let label;
      let attempts = 0;
      do {
        if (challengeDifficulty === 'easy') {
          label = CHALLENGE_LETTERS[Math.floor(Math.random() * CHALLENGE_LETTERS.length)];
        } else {
          // For hard and unlimited, mix letters and words
          if (Math.random() < 0.6) {
            label = CHALLENGE_WORDS[Math.floor(Math.random() * CHALLENGE_WORDS.length)];
          } else {
            label = CHALLENGE_LETTERS[Math.floor(Math.random() * CHALLENGE_LETTERS.length)];
          }
        }
        attempts++;
      } while (attempts < 20 && label === challengeLastLabel);
      challengeLastLabel = label;
      return label;
    }

    // Measure text width for dynamic spacing
    function measureLabelWidth(label) {
      const display = label.replace(/_/g, ' ');
      // ~14px per char in Press Start 2P at 22px font-size
      return display.length * 14 + 20;
    }

    // Enable/disable the difficulty buttons + speed slider together
    function setControlsEnabled(enabled) {
      document.getElementById('diffEasy').disabled = !enabled;
      document.getElementById('diffHard').disabled = !enabled;
      document.getElementById('diffUnlimited').disabled = !enabled;
      document.getElementById('challengeSpeedSlider').disabled = !enabled;
    }

    // Shared teardown steps common to ending/quitting a challenge run
    function teardownChallenge() {
      challengeActive = false;
      if (challengeAnimFrame) {
        cancelAnimationFrame(challengeAnimFrame);
        challengeAnimFrame = null;
      }
      challengeLastTime = 0;

      const bar = document.getElementById('challengeScrollBar');
      bar.classList.remove('visible');
      bar.innerHTML = '';
    }

    function startChallenge() {
      if (!cameraOn) {
        alert('Please start the camera first!');
        return;
      }

      challengeActive = true;
      challengeCorrect = 0;
      challengeWrong = 0;
      challengeScore = 0;
      challengeItems = [];
      challengeLastTime = 0;
      challengeLastLabel = null;

      // Read speed from slider
      const sliderVal = parseInt(document.getElementById('challengeSpeedSlider').value) - 1;
      challengeSpeedMult = SPEED_MULTIPLIERS[sliderVal];

      updateChallengeScore();

      // Set ASL mode — "both" for hard/unlimited, "letters" for easy
      const mode = (challengeDifficulty === 'hard' || challengeDifficulty === 'unlimited') ? 'both' : 'letters';
      if (aslEngine) aslEngine.setMode(mode);

      // UI: compact spacing, hide start, show quit, show score
      document.getElementById('challengeSetup').classList.add('compact');
      document.getElementById('challengeStartBtn').style.display = 'none';
      document.getElementById('challengeQuitBtn').style.display = 'inline-block';
      document.getElementById('challengeScoreSection').style.display = 'flex';
      setControlsEnabled(false);

      // Update score label and goal text for unlimited mode
      if (challengeDifficulty === 'unlimited') {
        document.getElementById('scoreLabelCorrect').textContent = 'Score';
        document.getElementById('challengeGoalText').textContent = '10 wrong = game over';
      } else {
        document.getElementById('scoreLabelCorrect').textContent = 'Correct';
        document.getElementById('challengeGoalText').textContent = '';
      }

      // Show scroll bar
      const bar = document.getElementById('challengeScrollBar');
      bar.classList.add('visible');
      bar.innerHTML = '';

      // Spawn initial items across the bar
      const barWidth = bar.offsetWidth || 600;
      let nextX = barWidth;
      for (let i = 0; i < 3; i++) {
        const label = getRandomChallengeItem();
        const w = measureLabelWidth(label);
        spawnChallengeItem(nextX, label);
        nextX += w + BASE_SPACING;
      }

      challengeAnimFrame = requestAnimationFrame(challengeLoop);
    }

    function spawnChallengeItem(x, label) {
      if (!label) label = getRandomChallengeItem();
      const w = measureLabelWidth(label);
      const item = { label, x, width: w, wrongCount: 0, state: 'active' };
      challengeItems.push(item);

      const el = document.createElement('div');
      el.className = 'scroll-letter';
      el.textContent = label.replace(/_/g, ' ');
      el.style.left = x + 'px';
      document.getElementById('challengeScrollBar').appendChild(el);
    }

    function challengeLoop(timestamp) {
      if (!challengeActive) return;

      if (!challengeLastTime) challengeLastTime = timestamp;
      const dt = (timestamp - challengeLastTime) / 1000;
      challengeLastTime = timestamp;

      const bar = document.getElementById('challengeScrollBar');
      const barWidth = bar.offsetWidth || 600;
      const els = bar.querySelectorAll('.scroll-letter');
      const leftIdx = getLeftmostActiveIndex();

      const baseSpeed = challengeDifficulty === 'hard' ? BASE_SPEED_HARD : BASE_SPEED_EASY;
      const speed = baseSpeed * challengeSpeedMult;
      // Move active items left
      challengeItems.forEach((item) => {
        if (item.state === 'active') {
          item.x -= speed * dt;
        }
      });

      // Update DOM positions
      els.forEach((el, i) => {
        const item = challengeItems[i];
        if (!item) return;

        // Remove finished items from DOM
        if (item.state === 'done') {
          el.style.display = 'none';
          return;
        }

        el.style.left = item.x + 'px';
        el.className = 'scroll-letter';
        if (item.state === 'correct') el.classList.add('correct');
        else if (item.state === 'wrong') el.classList.add('wrong');
        else if (i === leftIdx) el.classList.add('active');
      });

      // Check if leftmost has fully left the screen
      if (leftIdx >= 0) {
        const leftItem = challengeItems[leftIdx];
        if (leftItem.x < -leftItem.width) {
          // All modes: count items going off screen as wrong
          markChallengeWrong(leftIdx);
        }
      }

      // Spawn new items with longer delay
      let rightmostX = 0;
      let rightmostWidth = 0;
      challengeItems.forEach((item) => {
        if (item.state === 'active' && item.x > rightmostX) {
          rightmostX = item.x;
          rightmostWidth = item.width;
        }
      });
      const nextStart = rightmostX + rightmostWidth + BASE_SPACING;
      if (nextStart < barWidth + 100) {
        spawnChallengeItem(nextStart);
      }

      challengeAnimFrame = requestAnimationFrame(challengeLoop);
    }

    function getLeftmostActiveIndex() {
      let minX = Infinity;
      let minIdx = -1;
      challengeItems.forEach((item, i) => {
        if (item.state === 'active' && item.x < minX) {
          minX = item.x;
          minIdx = i;
        }
      });
      return minIdx;
    }

    function checkChallengeDetection(msg) {
      if (!challengeActive) return;
      if (msg.type !== 'detection') return;

      const leftIdx = getLeftmostActiveIndex();
      if (leftIdx < 0) return;

      const item = challengeItems[leftIdx];
      let detected = '';

      if (msg.kind === 'letter') detected = msg.value;
      else if (msg.kind === 'word') detected = msg.word || msg.value;
      if (!detected) return;

      const isLetter = item.label.length === 1;

      if (isLetter) {
        if (msg.kind === 'letter' && detected === item.label) {
          markChallengeCorrect(leftIdx);
        } else if (msg.kind === 'letter') {
          item.wrongCount++;
          if (item.wrongCount >= WRONG_ATTEMPT_LIMIT) markChallengeWrong(leftIdx);
        }
      } else {
        if (msg.kind === 'word' && detected === item.label) {
          markChallengeCorrect(leftIdx);
        } else if (msg.kind === 'word') {
          item.wrongCount++;
          if (item.wrongCount >= WRONG_ATTEMPT_LIMIT) markChallengeWrong(leftIdx);
        }
      }
    }

    function markChallengeCorrect(idx) {
      // Mark as 'correct' immediately — getLeftmostActiveIndex skips non-active,
      // so next detection instantly targets the next item
      challengeItems[idx].state = 'correct';
      challengeCorrect++;
      
      // For unlimited mode, add points
      if (challengeDifficulty === 'unlimited') {
        challengeScore += POINTS_PER_CORRECT;
      }
      
      updateChallengeScore();
      setTimeout(() => {
        if (challengeItems[idx]) challengeItems[idx].state = 'done';
      }, 350);
      
      // Only check win condition for non-unlimited modes
      if (challengeDifficulty !== 'unlimited') {
        const winTarget = challengeDifficulty === 'hard' ? CHALLENGE_WIN_HARD : CHALLENGE_WIN_EASY;
        if (challengeCorrect >= winTarget) endChallenge(true);
      }
    }

    function markChallengeWrong(idx) {
      const item = challengeItems[idx];
      item.state = 'wrong';
      challengeWrong++;
      
      // Track wrong answer in session stats
      const label = item.label;
      if (!sessionStats[label]) {
        sessionStats[label] = 0;
      }
      sessionStats[label]++;
      saveSessionStats();
      
      updateChallengeScore();
      setTimeout(() => {
        if (challengeItems[idx]) challengeItems[idx].state = 'done';
      }, 500);
      
      // Check lose condition - all modes end at 10 wrong
      if (challengeWrong >= CHALLENGE_LOSE) {
        if (challengeDifficulty === 'unlimited') {
          endUnlimitedChallenge();
        } else {
          endChallenge(false);
        }
      }
    }

    function updateChallengeScore() {
      const correctEl = document.getElementById('challengeCorrect');
      const wrongEl = document.getElementById('challengeWrong');
      if (challengeDifficulty === 'unlimited') {
        correctEl.textContent = challengeScore;
      } else {
        correctEl.textContent = challengeCorrect;
      }
      wrongEl.textContent = challengeWrong;

      // Trigger pop animation on score change
      correctEl.classList.remove('score-pop');
      wrongEl.classList.remove('score-pop');
      void correctEl.offsetWidth; // force reflow
      if (challengeCorrect > 0 || challengeScore > 0) correctEl.classList.add('score-pop');
      if (challengeWrong > 0) wrongEl.classList.add('score-pop');
    }

    function endChallenge(won) {
      teardownChallenge();

      document.getElementById('challengeSetup').style.display = 'none';
      document.getElementById('challengeQuitBtn').style.display = 'none';
      const result = document.getElementById('challengeResult');
      result.style.display = 'flex';

      const title = document.getElementById('challengeResultTitle');
      const sub = document.getElementById('challengeResultSub');
      const imgWin = document.getElementById('challengeResultImgWin');
      const imgLose = document.getElementById('challengeResultImgLose');

      if (won) {
        imgWin.style.display = 'block';
        imgLose.style.display = 'none';
        title.textContent = 'Great Job!';
        title.style.color = 'var(--accent)';
        title.style.fontSize = '24px';
        const winTarget = challengeDifficulty === 'hard' ? CHALLENGE_WIN_HARD : CHALLENGE_WIN_EASY;
        sub.textContent = `You nailed ${winTarget} signs!`;
      } else {
        imgWin.style.display = 'none';
        imgLose.style.display = 'block';
        title.textContent = 'Game Over';
        title.style.color = 'var(--danger)';
        title.style.fontSize = '24px';
        sub.textContent = 'Too many misses. Keep practicing!';
      }

      document.getElementById('challengeResultCorrect').textContent = challengeCorrect;
      document.getElementById('challengeResultWrong').textContent = challengeWrong;
    }

    function endUnlimitedChallenge() {
      teardownChallenge();

      document.getElementById('challengeSetup').style.display = 'none';
      document.getElementById('challengeQuitBtn').style.display = 'none';
      const result = document.getElementById('challengeResult');
      result.style.display = 'flex';

      const title = document.getElementById('challengeResultTitle');
      const sub = document.getElementById('challengeResultSub');
      const imgWin = document.getElementById('challengeResultImgWin');
      const imgLose = document.getElementById('challengeResultImgLose');

      imgWin.style.display = 'block';
      imgLose.style.display = 'none';
      title.textContent = 'Game Over!';
      title.style.color = 'var(--accent)';
      title.style.fontSize = '24px';
      sub.textContent = `Final Score: ${challengeScore} points`;

      document.getElementById('challengeResultCorrect').textContent = challengeScore;
      document.getElementById('challengeResultWrong').textContent = challengeWrong;

      // Save to leaderboard
      saveToLeaderboard(challengeScore);
      // Update leaderboard display if on stats tab
      if (activeTab === 'stats') {
        renderLeaderboard();
      }
    }

    function quitChallenge() {
      teardownChallenge();

      // Reset UI
      document.getElementById('challengeSetup').classList.remove('compact');
      document.getElementById('challengeStartBtn').style.display = 'inline-block';
      document.getElementById('challengeQuitBtn').style.display = 'none';
      document.getElementById('challengeScoreSection').style.display = 'none';
      setControlsEnabled(true);
    }

    function stopChallenge() {
      quitChallenge();
    }

    function resetChallenge() {
      challengeCorrect = 0;
      challengeWrong = 0;
      challengeScore = 0;
      challengeItems = [];
      challengeLastTime = 0;

      document.getElementById('challengeSetup').style.display = 'flex';
      document.getElementById('challengeResult').style.display = 'none';
      document.getElementById('challengeStartBtn').style.display = 'inline-block';
      document.getElementById('challengeQuitBtn').style.display = 'none';
      document.getElementById('challengeScoreSection').style.display = 'none';
      setControlsEnabled(true);

      // Reset score label
      document.getElementById('scoreLabelCorrect').textContent = 'Correct';

      updateChallengeScore();
    }

    // ============================================================
    // STATS TRACKING
    // ============================================================
    function loadSessionStats() {
      let saved = null;
      try { saved = localStorage.getItem('asl-session-stats'); } catch (e) {}
      if (saved) {
        try {
          sessionStats = JSON.parse(saved);
        } catch (e) {
          sessionStats = {};
        }
      } else {
        sessionStats = {};
      }
    }

    function saveSessionStats() {
      try { localStorage.setItem('asl-session-stats', JSON.stringify(sessionStats)); } catch (e) {}
    }

    function clearStats() {
      if (confirm('Clear all session statistics?')) {
        sessionStats = {};
        saveSessionStats();
        renderStats();
      }
    }

    function renderStats() {
      const grid = document.getElementById('statsGrid');
      if (!grid) return;

      // Separate letters and words - letters first, then words
      const letterItems = CHALLENGE_LETTERS.map(item => ({
        label: item,
        count: sessionStats[item] || 0,
        isLetter: true
      }));

      const wordItems = CHALLENGE_WORDS.map(item => ({
        label: item,
        count: sessionStats[item] || 0,
        isLetter: false
      }));

      // Sort letters by wrong count (descending), then alphabetically
      letterItems.sort((a, b) => {
        if (b.count !== a.count) return b.count - a.count;
        return a.label.localeCompare(b.label);
      });

      // Sort words by wrong count (descending), then alphabetically
      wordItems.sort((a, b) => {
        if (b.count !== a.count) return b.count - a.count;
        return a.label.localeCompare(b.label);
      });

      const allItems = [...letterItems, ...wordItems];

      grid.innerHTML = allItems.map(item => {
        const displayLabel = item.label.replace(/_/g, ' ');
        // Determine font size based on label length
        let fontSizeClass = '';
        if (displayLabel.length > 8) {
          fontSizeClass = 'tiny';
        } else if (displayLabel.length > 5) {
          fontSizeClass = 'small';
        }
        
        return `
          <div class="stat-item ${item.count > 0 ? 'has-errors' : ''}">
            <div class="stat-label ${fontSizeClass}">${displayLabel}</div>
            <div class="stat-value">${item.count}</div>
          </div>
        `;
      }).join('');
    }

    // ============================================================
    // LEADERBOARD
    // ============================================================
    function loadLeaderboard() {
      let saved = null;
      try { saved = localStorage.getItem('asl-leaderboard'); } catch (e) {}
      if (saved) {
        try {
          return JSON.parse(saved);
        } catch (e) {
          return [];
        }
      }
      return [];
    }

    function saveLeaderboard(leaderboard) {
      try { localStorage.setItem('asl-leaderboard', JSON.stringify(leaderboard)); } catch (e) {}
    }

    function saveToLeaderboard(score) {
      const leaderboard = loadLeaderboard();
      const entry = {
        score: score,
        date: new Date().toISOString()
      };
      leaderboard.push(entry);
      // Sort by score descending, keep top 10
      leaderboard.sort((a, b) => b.score - a.score);
      if (leaderboard.length > 10) {
        leaderboard.splice(10);
      }
      saveLeaderboard(leaderboard);
    }

    function renderLeaderboard() {
      const list = document.getElementById('leaderboardList');
      if (!list) return;

      const leaderboard = loadLeaderboard();
      
      if (leaderboard.length === 0) {
        list.innerHTML = '<div class="no-leaderboard">No scores yet. Play Unlimited mode to set a high score!</div>';
        return;
      }

      list.innerHTML = leaderboard.map((entry, index) => {
        const date = new Date(entry.date);
        const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        const isTop = index === 0;
        return `
          <div class="leaderboard-item ${isTop ? 'top' : ''}">
            <div class="leaderboard-rank">#${index + 1}</div>
            <div class="leaderboard-score">${entry.score} pts</div>
            <div class="leaderboard-date">${dateStr}</div>
          </div>
        `;
      }).join('');
    }

    // Initialize stats on page load
    loadSessionStats();

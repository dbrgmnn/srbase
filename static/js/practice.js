/**
 * ==========================================
 * PRACTICE SESSION MANAGEMENT
 * ==========================================
 */

// --- GLOBAL SESSION STATE ---
let sessionWords = [];
let answerHistory = [];
let currentWordIndex = 0;
let isAnimating = false;
let swipeData = { startX: 0, startY: 0, currentX: 0, currentY: 0, active: false, dragStarted: false };
let sessionStats = { review: 0, new: 0 };

// --- SESSION LIFECYCLE ---
async function startPractice() {
    const res = await API.request(`/api/practice/session?lang=${currentLanguage}`);
    if (res.status !== 'ok' || !res.data || res.data.length === 0) return alert(res.message || "Nothing to practice right now!");
    sessionWords = res.data;
    
    sessionStats.new = sessionWords.filter(w => !w.started_at).length;
    sessionStats.review = sessionWords.length - sessionStats.new;
    
    currentWordIndex = 0;
    answerHistory = [];
    document.getElementById('app').innerHTML = appRender.practice();
    
    await new Promise(resolve => setTimeout(resolve, 10));
    
    initSwipe();
    renderSessionCard();
}

function closePractice() {
    cleanupPractice();
    renderHub();
    updateStats();
}

function cleanupPractice() {
    if (swipeData._handlers) {
        const h = swipeData._handlers;
        const card = document.getElementById('flashCard');
        if (card) {
            card.removeEventListener('mousedown', h.handleStart);
            card.removeEventListener('touchstart', h.handleStart);
        }
        window.removeEventListener('mousemove', h.handleMove);
        window.removeEventListener('mouseup', h.handleEnd);
        window.removeEventListener('touchmove', h.handleMove);
        window.removeEventListener('touchend', h.handleEnd);
    }
    window.speechSynthesis.cancel();
    isAnimating = false;
}

// --- CARD RENDERING & FLIP ---
function renderSessionCard() {
    updateUndoButtonState();

    const progressBar = document.getElementById('practiceProgressBar');
    if (progressBar) {
        const progress = (currentWordIndex / sessionWords.length) * 100;
        progressBar.style.width = `${progress}%`;
    }

    const counter = document.getElementById('practiceCounter');
    if (counter) {
        counter.textContent = `${currentWordIndex + 1} / ${sessionWords.length}`;
    }

    const card = document.getElementById('flashCard');
    if (!card) return;

    const word = sessionWords[currentWordIndex];
    
    card.classList.remove('is-revealed');
    card.style.transition = 'none';
    card.style.transform = 'translate(0,0) scale(1)';
    card.style.opacity = '1';

    card.offsetHeight;
    card.style.transition = '';

    const isNew = !word.started_at;
    const statusTag = isNew
        ? `<div class="status-tag new">New</div>`
        : `<div class="status-tag review">Review</div>`;
    const levelTag = word.level ? `<div class="level-tag">${word.level}</div>` : '';

    document.getElementById('cardTags').innerHTML = levelTag + statusTag;

    document.getElementById('cardFront').innerHTML = `
        <div style="font-size: 1.2rem; color:#fff; font-weight:700; letter-spacing:-0.5px;">${word.word}</div>
    `;

    document.getElementById('cardBack').innerHTML = `
        <div style="font-size: 1.2rem; color:#fff; font-weight:700; letter-spacing:-0.5px;">${word.translation}</div>
        ${word.example ? `<div style="position:absolute; top:75%; transform:translateY(-50%); left:20px; right:20px; text-align:center; font-style:italic; color:var(--text-low); font-size:0.8rem; line-height:1.4;">${word.example}</div>` : ''}
    `;
}

function flipCard() {
    if (isAnimating) return;
    document.getElementById('flashCard').classList.toggle('is-revealed');
}

function updateUndoButtonState() {
    const undoBtn = document.querySelector('.bottom-nav .nav-segment:nth-child(2)');
    if (undoBtn) {
        if (answerHistory.length === 0) undoBtn.classList.add('disabled');
        else undoBtn.classList.remove('disabled');
    }
}

// --- USER ACTIONS & SWIPE LOGIC ---
function initSwipe() {
    const card = document.getElementById('flashCard');
    if (!card) return;

    cleanupPractice();

    const reset = () => {
        swipeData.active = false;
        swipeData.dragStarted = false;
        card.style.transition = 'transform 0.5s cubic-bezier(0.23, 1, 0.32, 1)';
        card.style.transform = 'translate(0,0) scale(1)';
        const glow = document.getElementById('practiceGlow');
        if (glow) {
            glow.style.opacity = '0';
            glow.style.transform = 'scale(0.8)';
        }
    };

    const handleStart = (e) => {
        if (isAnimating) return;
        swipeData.active = true;
        swipeData.dragStarted = false;
        const isTouch = e.type.includes('touch');
        const touch = isTouch ? e.touches[0] : e;
        swipeData.startX = touch.clientX;
        swipeData.startY = touch.clientY;
        
        if (isTouch && e.cancelable) e.preventDefault();
    };

    const handleMove = (e) => {
        if (!swipeData.active || isAnimating) return;
        const isTouch = e.type.includes('touch');
        const touch = isTouch ? e.touches[0] : e;

        const dx = touch.clientX - swipeData.startX;
        const dy = touch.clientY - swipeData.startY;

        if (!swipeData.dragStarted) {
            if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
                swipeData.dragStarted = true;
                card.style.transition = 'none';
            } else return;
        }

        if (e.cancelable) e.preventDefault();
        swipeData.currentX = touch.clientX;
        swipeData.currentY = touch.clientY;

        card.style.transform = `translate(${dx}px, ${dy}px) rotate(${dx / 20}deg)`;

        const glow = document.getElementById('practiceGlow');
        const feedback = document.getElementById('swipeFeedback');
        const icon = document.getElementById('swipeIcon');
        const label = document.getElementById('swipeLabel');

        if (glow && feedback) {
            let active = true;
            feedback.className = 'swipe-feedback-content';

            if (dy < -50 && Math.abs(dx) < Math.abs(dy)) {
                icon.innerText = '⚡';
                label.innerText = 'Hard';
                feedback.classList.add('feedback-hard');
                glow.style.opacity = Math.min(Math.abs(dy) / 150, 1);
            } else if (dx > 50) {
                icon.innerText = '✅';
                label.innerText = 'Easy';
                feedback.classList.add('feedback-easy');
                glow.style.opacity = Math.min(Math.abs(dx) / 150, 1);
            } else if (dx < -50) {
                icon.innerText = '❌';
                label.innerText = 'Again';
                feedback.classList.add('feedback-again');
                glow.style.opacity = Math.min(Math.abs(dx) / 150, 1);
            } else {
                active = false;
                glow.style.opacity = '0';
            }
            
            if (active) glow.style.transform = 'scale(1)';
            else glow.style.transform = 'scale(0.8)';
        }
    };

    const handleEnd = (e) => {
        if (!swipeData.active || isAnimating) return;
        const isTouch = e.type.includes('touch');
        if (isTouch && e.cancelable) e.preventDefault();

        const glow = document.getElementById('practiceGlow');
        if (glow && swipeData.dragStarted) glow.style.opacity = '0';

        if (!swipeData.dragStarted) {
            swipeData.active = false;
            flipCard();
            return;
        }

        const touch = isTouch ? e.changedTouches[0] : e;
        const dx = touch.clientX - swipeData.startX;
        const dy = touch.clientY - swipeData.startY;

        if (dy < -100 && Math.abs(dx) < Math.abs(dy)) submitAnswer(3);
        else if (dx > 100) submitAnswer(5);
        else if (dx < -100) submitAnswer(0);
        else reset();

        swipeData.active = false;
    };

    card.addEventListener('mousedown', handleStart);
    window.addEventListener('mousemove', handleMove, { passive: false });
    window.addEventListener('mouseup', handleEnd);
    card.addEventListener('touchstart', handleStart, { passive: false });
    window.addEventListener('touchmove', handleMove, { passive: false });
    window.addEventListener('touchend', handleEnd, { passive: false });

    swipeData._handlers = { handleStart, handleMove, handleEnd };
}

async function submitAnswer(quality) {
    if (isAnimating) return;
    const word = sessionWords[currentWordIndex];
    isAnimating = true;

    answerHistory.push({ index: currentWordIndex, data: { ...word } });

    const card = document.getElementById('flashCard');
    card.style.transition = 'all 0.4s ease-in';
    card.style.opacity = '0';
    if (quality === 5) card.style.transform += ' translateX(600px) rotate(20deg)';
    else if (quality === 0) card.style.transform += ' translateX(-600px) rotate(-20deg)';
    else if (quality === 3) card.style.transform += ' translateY(-600px)';

    await API.request('/api/practice/answer', 'POST', { word_id: word.id, quality });

    setTimeout(() => {
        isAnimating = false;
        currentWordIndex++;
        if (currentWordIndex < sessionWords.length) renderSessionCard();
        else { alert("Bravo! Session Finished!"); closePractice(); }
    }, 250);
}

async function undoReview() {
    if (isAnimating || answerHistory.length === 0) return;
    const lastAction = answerHistory.pop();
    const wordToRestore = lastAction.data;

    showTemporaryFeedback('⏪', 'Undo', 'feedback-hard');

    await API.request('/api/practice/undo', 'POST', {
        word_id: wordToRestore.id,
        repetitions: wordToRestore.repetitions,
        easiness: wordToRestore.easiness,
        interval: wordToRestore.interval,
        next_review: wordToRestore.next_review,
        last_reviewed_at: wordToRestore.last_reviewed_at,
        started_at: wordToRestore.started_at
    });

    currentWordIndex = lastAction.index;
    renderSessionCard();
}

function showTemporaryFeedback(iconText, labelText, className) {
    const glow = document.getElementById('practiceGlow');
    const feedback = document.getElementById('swipeFeedback');
    const icon = document.getElementById('swipeIcon');
    const label = document.getElementById('swipeLabel');

    if (!glow || !feedback) return;

    icon.innerText = iconText;
    label.innerText = labelText;
    feedback.className = 'swipe-feedback-content ' + className;

    glow.style.transition = 'opacity 0.15s, transform 0.15s';
    glow.style.opacity = '1';
    glow.style.transform = 'scale(1)';

    setTimeout(() => {
        glow.style.opacity = '0';
        glow.style.transform = 'scale(0.8)';
        setTimeout(() => {
            glow.style.transition = '';
        }, 150);
    }, 300);
}

// --- AUDIO & SHORTCUTS ---
function speakCurrentWord() {
    const word = sessionWords[currentWordIndex];
    if (!word) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(word.word);
    utterance.lang = currentLanguage === 'de' ? 'de-DE' : 'en-US';
    window.speechSynthesis.speak(utterance);
}

window.addEventListener('keydown', (e) => {
    const isPractice = !!document.getElementById('practiceView');
    if (!isPractice) return;

    if (e.code === 'Space') {
        e.preventDefault();
        flipCard();
    } else if (e.code === 'Digit1') submitAnswer(0);
    else if (e.code === 'Digit2') submitAnswer(3);
    else if (e.code === 'Digit3') submitAnswer(4);
    else if (e.code === 'Digit4') submitAnswer(5);
    else if (e.key === 'z' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        undoReview();
    }
});

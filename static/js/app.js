/**
 * Main Application Logic & Auth
 */
let currentUser = null;
let currentLanguage = 'de';
let searchTimeout = null;
let userSettings = { daily_limit: 20 };

async function init() {
    const userId = localStorage.getItem('user_id');
    if (userId) {
        const data = await API.request('/api/me');
        if (data.status === 'ok') { 
            currentUser = data.user; 
            const sData = await API.request(`/api/me/settings?lang=${currentLanguage}`);
            if (sData.status === 'ok') userSettings = sData.settings;
            renderHub(); 
            updateStats();
        }
        else logout();
    } else renderLogin();
}

function renderLogin() {
    document.getElementById('app').innerHTML = appRender.login();
    loadProfiles();
}

function renderHub() {
    document.getElementById('app').innerHTML = appRender.hub();
    // Safely populate user data that cannot go through innerHTML
    const nameEl = document.getElementById('settingsUserName');
    if (nameEl) nameEl.textContent = currentUser.name;
    const emailEl = document.getElementById('settingsUserEmail');
    if (emailEl) emailEl.textContent = currentUser.email;
    const telegramEl = document.getElementById('settingsUserTelegram');
    if (telegramEl) {
        telegramEl.textContent = currentUser.telegram_chat_id ? `TG ID: ${currentUser.telegram_chat_id}` : 'TG ID: Not set';
    }
}

async function loadProfiles() {
    const res = await API.request('/api/users/list');
    const grid = document.getElementById('profilesGrid');
    if (res.status !== 'ok' || !res.data || res.data.length === 0) {
        grid.innerHTML = '<p style="text-align:center; color:var(--text-low); padding:20px;">No profiles found</p>';
    } else {
        res.data.forEach(u => {
            const item = document.createElement('div');
            item.className = 'card';
            item.style.cssText = 'display:flex; align-items:center; gap:14px; padding:14px 18px; cursor:pointer;';
            item.onclick = () => selectProfile(u.id);
            const initial = u.name ? u.name.charAt(0).toUpperCase() : '?';
            item.innerHTML = `
                <div style="width:38px; height:38px; border-radius:50%; background:rgba(0,122,255,0.15); display:flex; align-items:center; justify-content:center; flex-shrink:0; font-size:1rem; font-weight:700; color:var(--primary);"></div>
                <div style="font-size:1rem; font-weight:600; color:#fff;"></div>
            `;
            item.querySelectorAll('div')[0].textContent = initial;
            item.querySelectorAll('div')[1].textContent = u.name;
            grid.appendChild(item);
        });
    }
}

async function updateStats() {
    const res = await API.request(`/api/words/stats?lang=${currentLanguage}`);
    if (res.status === 'ok' && res.data) {
        lastStats = res.data;
        const stats = res.data;
        const fields = {
            'statDue': stats.due || 0,
            'statQueue': stats.total || 0,
            'statLearning': stats.difficult || 0,
            'statKnown': stats.learning || 0,
            'statMastered': stats.mastered || 0,
            'statLearnedToday': stats.today_reviewed || 0,
            'statAddedToday': stats.today_added || 0
        };
        for (const [id, val] of Object.entries(fields)) {
            const el = document.getElementById(id);
            if (el) el.innerText = val;
        }
        
        const nextTimeEl = document.getElementById('statNextTime');
        if (nextTimeEl) {
            const limit = userSettings.daily_limit || 20;
            const remainingInLimit = Math.max(0, limit - (stats.today_new || 0));
            const availableNew = Math.min(stats.st_new || 0, remainingInLimit);
            nextTimeEl.innerText = availableNew > 0 ? availableNew : "0";
        }

        const pBtn = document.querySelector('.btn-primary.btn-lg');
        if (pBtn) {
            pBtn.disabled = !(stats.session_total > 0);
            pBtn.innerText = 'Practice';
        }
    }
}

// --- SEARCH & FILTER ---

function handleSearch(query) {
    clearTimeout(searchTimeout);
    const container = document.getElementById('searchResults');
    if (query.trim().length < 2) { 
        container.innerHTML = ''; 
        return; 
    }
    
    lastSearchQuery = query;
    lastFilterType = null;
    
    searchTimeout = setTimeout(async () => {
        const res = await API.request(`/api/words/search?q=${encodeURIComponent(query)}&lang=${currentLanguage}`);
        renderSearchResults(res.data || [], query);
    }, 300);
}

function renderSearchResults(words, query = '') {
    const container = document.getElementById('searchResults');
    if (words && words.length > 0) {
        container.innerHTML = '';
        words.forEach(w => {
            const el = document.createElement('div');
            el.className = 'swipe-container';
            el.id = `word-${w.id}`;
            
            el.innerHTML = `
                <div class="swipe-action" onclick="handleDeleteWord(${w.id})">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"></path><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path></svg>
                </div>
                <div class="swipe-content card"
                     style="padding:16px 18px; text-align:left; display:flex; align-items:flex-start; justify-content:space-between; gap:12px;"
                     ontouchstart="handleSwipeStart(event)"
                     ontouchmove="handleSwipeMove(event)"
                     ontouchend="handleSwipeEnd(event)"
                     onmousedown="handleSwipeStart(event)">
                    
                    <div style="flex:1; min-width:0;">
                        <!-- VIEW MODE -->
                        <div id="view-mode-${w.id}"></div>
                        
                        <!-- EDIT MODE (Hidden by default) -->
                        <div id="edit-mode-${w.id}" style="display:none; flex-direction:column; gap:8px;" onmousedown="event.stopPropagation()" ontouchstart="event.stopPropagation()">
                            <input type="text" id="edit-word-${w.id}" class="input" style="margin:0; padding:8px;" placeholder="Word">
                            <input type="text" id="edit-translation-${w.id}" class="input" style="margin:0; padding:8px;" placeholder="Translation">
                            <textarea id="edit-example-${w.id}" class="input" style="margin:0; padding:8px; resize:none; font-size:0.9rem;" rows="2" placeholder="Example"></textarea>
                            <select id="edit-level-${w.id}" class="input" style="margin:0; padding:8px; color:var(--text-med);">
                                <option value="">Level (Optional)</option>
                                <option value="A1">A1</option>
                                <option value="A2">A2</option>
                                <option value="B1">B1</option>
                                <option value="B2">B2</option>
                                <option value="C1">C1</option>
                                <option value="C2">C2</option>
                            </select>
                            <div style="display:flex; gap:8px; margin-top:4px;">
                                <button class="btn btn-secondary" style="flex:1; padding:8px;" onclick="toggleInlineEdit(${w.id}, false)">Cancel</button>
                                <button class="btn btn-primary" style="flex:1; padding:8px;" id="save-btn-${w.id}" onclick="saveInlineEdit(${w.id})">Save</button>
                            </div>
                        </div>
                    </div>
                    <div class="word-edit-btn" id="edit-btn-${w.id}"
                         style="flex-shrink:0; cursor:pointer; color:var(--text-low); padding:6px; transition:color 0.2s;"
                         onmouseenter="this.style.color='var(--primary)'" onmouseleave="this.style.color='var(--text-low)'"
                         onclick="toggleInlineEdit(${w.id}, true)">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                    </div>
                </div>
            `;
            
            // Populate edit fields securely via DOM properties
            el.querySelector(`#edit-word-${w.id}`).value = w.word || '';
            el.querySelector(`#edit-translation-${w.id}`).value = w.translation || '';
            el.querySelector(`#edit-example-${w.id}`).value = w.example || '';
            el.querySelector(`#edit-level-${w.id}`).value = w.level || '';
            
            container.appendChild(el);
            
            // Build the initial view mode
            updateViewMode(w.id, w);
        });
    } else {
        const safeQuery = query ? query.replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"}[m])) : '';
        const noResultsMsg = query ? `No matches for "${safeQuery}".` : "No words found in this category.";
        container.innerHTML = `
            <div class="card" style="text-align:center; border:1px dashed #333; padding:50px 20px; background:transparent;">
                <p style="color:var(--text-low); margin-bottom:20px; font-size:1.1rem;">${noResultsMsg}</p>
            </div>
        `;
    }
}

// --- SWIPE LOGIC ---
let swipeItemData = { startX: 0, currentX: 0, activeEl: null, isMouse: false };

function handleSwipeStart(e) {
    const isTouch = e.type.includes('touch');
    const coord = isTouch ? e.touches[0] : e;
    
    swipeItemData.startX = coord.clientX;
    swipeItemData.activeEl = e.currentTarget;
    swipeItemData.activeEl.style.transition = 'none';
    swipeItemData.isMouse = !isTouch;

    if (!isTouch) {
        window.addEventListener('mousemove', handleSwipeMove);
        window.addEventListener('mouseup', handleSwipeEnd);
    }
}

function handleSwipeMove(e) {
    if (!swipeItemData.activeEl) return;
    
    const coord = e.type.includes('touch') ? e.touches[0] : e;
    const dx = coord.clientX - swipeItemData.startX;
    
    if (dx > 0) return;
    
    const moveX = Math.max(dx, -100);
    swipeItemData.activeEl.style.transform = `translateX(${moveX}px)`;
    
    if (Math.abs(dx) > 10 && e.cancelable) e.preventDefault();
}

function handleSwipeEnd(e) {
    if (!swipeItemData.activeEl) return;
    
    const coord = e.type.includes('touch') ? e.changedTouches[0] : e;
    const dx = coord.clientX - swipeItemData.startX;
    
    swipeItemData.activeEl.style.transition = 'transform 0.3s cubic-bezier(0.25, 1, 0.5, 1)';
    
    if (dx < -60) {
        swipeItemData.activeEl.style.transform = 'translateX(-80px)';
    } else {
        swipeItemData.activeEl.style.transform = 'translateX(0)';
    }
    
    if (swipeItemData.isMouse) {
        window.removeEventListener('mousemove', handleSwipeMove);
        window.removeEventListener('mouseup', handleSwipeEnd);
    }
    
    swipeItemData.activeEl = null;
}

async function handleDeleteWord(id) {
    if (!confirm("Delete this word?")) {
        const el = document.querySelector(`#word-${id} .swipe-content`);
        if (el) el.style.transform = 'translateX(0)';
        return;
    }
    
    const res = await API.request(`/api/words/${id}`, 'DELETE');
    if (res.status === 'ok') {
        const container = document.getElementById(`word-${id}`);
        if (container) {
            container.style.transition = 'all 0.3s ease';
            container.style.opacity = '0';
            container.style.maxHeight = '0';
            container.style.margin = '0';
            setTimeout(() => {
                container.remove();
                updateStats();
            }, 300);
        }
    } else {
        alert(res.message || "Failed to delete");
    }
}

async function handleFilterClick(filterType) {
    lastFilterType = filterType;
    lastSearchQuery = '';
    toggleView('search');
    
    const inputEl = document.getElementById('searchInput');
    if (inputEl) inputEl.value = '';
    
    const container = document.getElementById('searchResults');
    container.innerHTML = '<div style="text-align:center; padding:100px; color:var(--text-low); font-size:1.1rem;">Searching...</div>';
    
    const res = await API.request(`/api/words/search?filter=${filterType}&lang=${currentLanguage}`);
    renderSearchResults(res.data || []); 
}

let lastSearchQuery = '';
let lastFilterType = null;

function updateViewMode(id, w) {
    const viewMode = document.getElementById(`view-mode-${id}`);
    if (!viewMode) return;
    
    const levelHtml = w.level 
        ? `<div class="word-level" style="font-size:0.7rem; background:rgba(255,255,255,0.15); padding:2px 6px; border-radius:4px; color:#ddd; font-weight:600; flex-shrink:0;"></div>` 
        : '';
    const exampleHtml = w.example 
        ? `<div class="word-example" style="color:var(--text-low); font-size:0.85rem; font-style:italic; margin-top:6px; line-height:1.3; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;"></div>` 
        : '';

    viewMode.innerHTML = `
        <div style="display:flex; align-items:center; gap:8px;">
            <div class="word-text" style="color:#fff; font-weight:700; font-size:1.1rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;"></div>
            ${levelHtml}
        </div>
        <div class="word-translation" style="color:var(--primary); font-size:1rem; margin-top:3px; font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;"></div>
        ${exampleHtml}
    `;

    viewMode.querySelector('.word-text').textContent = w.word || '?';
    viewMode.querySelector('.word-translation').textContent = w.translation || '?';
    if (w.level) viewMode.querySelector('.word-level').textContent = w.level;
    if (w.example) viewMode.querySelector('.word-example').textContent = `"${w.example}"`;
}

function toggleInlineEdit(id, show) {
    const viewMode = document.getElementById(`view-mode-${id}`);
    const editMode = document.getElementById(`edit-mode-${id}`);
    const editBtn = document.getElementById(`edit-btn-${id}`);
    
    if (!viewMode || !editMode || !editBtn) return;
    
    if (show) {
        viewMode.style.display = 'none';
        editMode.style.display = 'flex';
        editBtn.style.display = 'none';
    } else {
        viewMode.style.display = 'block';
        editMode.style.display = 'none';
        editBtn.style.display = 'block';
    }
}

async function saveInlineEdit(id) {
    const word = document.getElementById(`edit-word-${id}`).value.trim();
    const translation = document.getElementById(`edit-translation-${id}`).value.trim();
    const example = document.getElementById(`edit-example-${id}`).value.trim() || '';
    const level = document.getElementById(`edit-level-${id}`).value.trim() || '';

    if (!word || !translation) return alert('Word and translation are required.');

    const saveBtn = document.getElementById(`save-btn-${id}`);
    saveBtn.innerText = 'Saving...';
    saveBtn.disabled = true;

    const res = await API.request(`/api/words/${id}`, 'PATCH', { word, translation, example, level });
    
    saveBtn.innerText = 'Save';
    saveBtn.disabled = false;

    if (res.status === 'ok') {
        updateViewMode(id, { word, translation, example, level });
        toggleInlineEdit(id, false);
    } else {
        alert(res.message || "Failed to update");
    }
}

async function handleAddWordSubmit() {
    const word = document.getElementById('addWordText').value.trim();
    const translation = document.getElementById('addTranslationText').value.trim();
    const example = document.getElementById('addExampleText').value.trim() || undefined;
    const level = document.getElementById('addLevelText').value.trim() || undefined;

    if (!word || !translation) return alert('Word and translation are required.');

    const res = await API.request('/api/words', 'POST', { word, translation, example, level, lang: currentLanguage });
    if (res.status === 'ok') {
        document.getElementById('addWordText').value = '';
        document.getElementById('addTranslationText').value = '';
        document.getElementById('addExampleText').value = '';
        document.getElementById('addLevelText').value = '';
        updateStats();
        toggleView('home');
    } else {
        alert(res.message || "Failed to add word");
    }
}

// --- SETTINGS & PROFILE ---

function toggleView(type) {
    const searchPanel = document.getElementById('searchPanel');
    const settingsPanel = document.getElementById('settingsPanel');
    const addWordPanel = document.getElementById('addWordPanel');
    const homePanel = document.getElementById('homePanel');

    // Hide all
    if (searchPanel) searchPanel.classList.remove('active');
    if (settingsPanel) settingsPanel.classList.remove('active');
    if (addWordPanel) addWordPanel.classList.remove('active');
    if (homePanel) homePanel.style.display = 'none';

    // Show selected
    if (type === 'search') {
        if (searchPanel) searchPanel.classList.add('active');
        const inputEl = document.getElementById('searchInput');
        if (inputEl && !inputEl.value) {
            setTimeout(() => inputEl.focus(), 50); 
        }
    } else if (type === 'settings') {
        if (settingsPanel) settingsPanel.classList.add('active');
    } else if (type === 'addWord') {
        // Always re-render to reset the form
        if (addWordPanel) {
            addWordPanel.innerHTML = appRender.addWord();
            addWordPanel.classList.add('active');
            const inputEl = document.getElementById('addWordText');
            if (inputEl) setTimeout(() => inputEl.focus(), 50);
        }
    } else {
        if (homePanel) homePanel.style.display = 'flex';
    }

    // Update navbar state
    const nav = document.getElementById('bottomNav');
    if (nav) {
        nav.setAttribute('data-active', type);
        document.querySelectorAll('.nav-segment').forEach(el => el.classList.remove('active'));
        const activeSeg = document.querySelector(`.nav-segment[onclick="toggleView('${type}')"]`);
        if (activeSeg) activeSeg.classList.add('active');
    }

    window.scrollTo(0, 0);
}

async function saveLimit(val) { 
    const res = await API.request('/api/me/settings', 'PUT', { lang: currentLanguage, daily_limit: parseInt(val) });
    if (res.status === 'ok') {
        userSettings.daily_limit = parseInt(val);
        updateStats();
    }
}

async function saveNotificationTime(val) { 
    const res = await API.request('/api/me/settings', 'PUT', { lang: currentLanguage, notification_time: parseInt(val) });
    if (res.status === 'ok') {
        userSettings.notification_time = parseInt(val);
    }
}

async function saveNotificationThreshold(val) {
    const res = await API.request('/api/me/settings', 'PUT', { lang: currentLanguage, notification_threshold: parseInt(val) });
    if (res.status === 'ok') {
        userSettings.notification_threshold = parseInt(val);
    }
}

async function changeLanguage(lang) {
    currentLanguage = lang;
    const res = await API.request(`/api/me/settings?lang=${currentLanguage}`);
    if (res.status === 'ok') userSettings = res.settings;
    updateStats();
    renderSettingsPanel(false);
}

function renderSettingsPanel(edit) { 
    document.getElementById('settingsPanel').innerHTML = appRender.settings(edit);
    
    if (edit) {
        const nameInput = document.getElementById('editName');
        if (nameInput) nameInput.value = currentUser.name;
        const emailInput = document.getElementById('editEmail');
        if (emailInput) emailInput.value = currentUser.email;
        const telegramInput = document.getElementById('editTelegramChatId');
        if (telegramInput) telegramInput.value = currentUser.telegram_chat_id || '';
    } else {
        const nameEl = document.getElementById('settingsUserName');
        if (nameEl) nameEl.textContent = currentUser.name;
        const emailEl = document.getElementById('settingsUserEmail');
        if (emailEl) emailEl.textContent = currentUser.email;
        const telegramEl = document.getElementById('settingsUserTelegram');
        if (telegramEl) {
            telegramEl.textContent = currentUser.telegram_chat_id ? `TG ID: ${currentUser.telegram_chat_id}` : 'TG ID: Not set';
        }
    }
}

async function handleCreateProfile() { 
    const n = document.getElementById('newName').value.trim(); 
    const e = document.getElementById('newEmail').value.trim(); 
    if (!n || !e) return; 
    const res = await API.request('/api/users', 'POST', { name: n, email: e }); 
    if (res.status === 'ok' && res.user) selectProfile(res.user.id); 
    else alert(res.message || "Failed to create profile");
}

async function saveProfile() { 
    const name = document.getElementById('editName').value.trim(); 
    const email = document.getElementById('editEmail').value.trim().toLowerCase();
    const telegram_chat_id = document.getElementById('editTelegramChatId').value.trim();
    
    if (!name || !email) return alert("Name and email are required"); 
    
    const res = await API.request('/api/me', 'PUT', { name, email, telegram_chat_id }); 
    if (res.status === 'ok') { 
        currentUser.name = name; 
        currentUser.email = email;
        currentUser.telegram_chat_id = telegram_chat_id || null;
        renderSettingsPanel(false); 
    } else {
        alert(res.message || "Failed to update profile");
    }
}

function selectProfile(id) { 
    localStorage.setItem('user_id', id); 
    location.reload(); 
}

function logout() { 
    localStorage.removeItem('user_id'); 
    location.reload(); 
}

async function deleteProfile() { 
    if(confirm("Permanently delete this profile? All data for this profile will be lost.")) { 
        const res = await API.request('/api/me', 'DELETE'); 
        if (res.status === 'ok') logout(); 
    } 
}

init();

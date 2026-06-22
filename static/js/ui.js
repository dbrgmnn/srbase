/**
 * UI Templates (Pure HTML renderers)
 */
const appRender = {
    login: () => `
        <div class="view-container" style="justify-content:center; min-height:80vh; gap:16px;">
            <div id="profilesGrid" style="display:flex; flex-direction:column; gap:10px; width:100%;"></div>
            
            <div style="margin-top:8px; border-top:1px solid #222; padding-top:20px; display:flex; flex-direction:column; gap:12px;">
                <input type="text" id="newName" class="input" style="margin-bottom:0;" placeholder="Name">
                <input type="email" id="newEmail" class="input" style="margin-bottom:0;" placeholder="Email">
                <button onclick="handleCreateProfile()" class="btn btn-ghost btn-block" style="margin-top:8px;">Create Profile</button>
            </div>
        </div>
    `,
    navbar: (active = 'home') => `
        <div class="bottom-nav" id="bottomNav" data-active="${active}">
            <div class="nav-segment ${active === 'search' ? 'active' : ''}" onclick="toggleView('search')">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
            </div>
            <div class="nav-segment ${active === 'home' ? 'active' : ''}" onclick="toggleView('home')">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>
            </div>
            <div class="nav-segment ${active === 'settings' ? 'active' : ''}" onclick="toggleView('settings')">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
            </div>
        </div>
    `,
    hub: () => `
        ${appRender.navbar('home')}
        <div id="searchPanel" class="panel">${appRender.search()}</div>
        <div id="settingsPanel" class="panel">${appRender.settings()}</div>
        <div id="addWordPanel" class="panel">${appRender.addWord()}</div>
        
        <div class="view-container" id="homePanel">
            <div class="panel-section" style="margin-top:0;">
                <div class="panel-label" style="text-align:center;">Home</div>
            </div>
            <div class="dashboard-grid">
                <div class="dashboard-row row-main">
                    <div class="stat-card large">
                        <div class="stat-num" id="statDue">0</div>
                        <div class="stat-label">Review</div>
                    </div>
                    <div class="stat-card large">
                        <div class="stat-num" id="statNextTime">0</div>
                        <div class="stat-label">New</div>
                    </div>
                </div>

                <div class="dashboard-row row-stats">
                    <div class="stat-card small" onclick="handleFilterClick('total')">
                        <div class="stat-num" id="statQueue">0</div>
                        <div class="stat-label">Total</div>
                    </div>
                    <div class="stat-card small" onclick="handleFilterClick('difficult')">
                        <div class="stat-num" id="statLearning" style="color:#ff9f0a;">0</div>
                        <div class="stat-label" style="color:#ff9f0a; opacity:0.8;">Difficult</div>
                    </div>
                    <div class="stat-card small" onclick="handleFilterClick('learning')">
                        <div class="stat-num" id="statKnown" style="color:#30d158;">0</div>
                        <div class="stat-label" style="color:#30d158; opacity:0.8;">Learning</div>
                    </div>
                    <div class="stat-card small" onclick="handleFilterClick('mastered')">
                        <div class="stat-num" id="statMastered" style="color:#bf5af2;">0</div>
                        <div class="stat-label" style="color:#bf5af2; opacity:0.8;">Mastered</div>
                    </div>
                </div>

                <div class="dashboard-row row-daily">
                    <div class="stat-card" onclick="handleFilterClick('today_new')">
                        <div class="stat-num" id="statLearnedToday">0</div>
                        <div class="stat-label">Learned Today</div>
                    </div>
                    <div class="stat-card" onclick="handleFilterClick('today_added')">
                        <div class="stat-num" id="statAddedToday">0</div>
                        <div class="stat-label">Added Today</div>
                    </div>
                </div>
            </div>

            <button class="btn btn-primary btn-lg btn-block" style="margin-top:25px;" onclick="startPractice()" disabled>Practice</button>
            <div style="margin-top:12px; display:flex; justify-content:center;">
                <button onclick="toggleView('addWord')" class="btn btn-ghost">+ Add Word</button>
            </div>
        </div>
    `,
    addWord: () => `
        <div class="panel-section" style="margin-top:0;">
            <div class="panel-label" style="text-align:center;">Add Word</div>
        </div>
        <div class="card" style="padding:20px; margin-top:20px;">
            <input type="text" id="addWordText" class="input" placeholder="Word (Required)" required>
            <input type="text" id="addTranslationText" class="input" placeholder="Translation (Required)" required>
            <input type="text" id="addExampleText" class="input" placeholder="Example Sentence (Optional)">
            <select id="addLevelText" class="input" style="color:var(--text-med);">
                <option value="">Level (Optional)</option>
                <option value="A1">A1</option>
                <option value="A2">A2</option>
                <option value="B1">B1</option>
                <option value="B2">B2</option>
                <option value="C1">C1</option>
                <option value="C2">C2</option>
            </select>
            <div style="margin-top:24px; display:flex; justify-content:center; gap:16px;">
                <button onclick="cancelWordEdit()" class="btn btn-ghost-muted">Cancel</button>
                <button id="addWordSubmitBtn" onclick="handleAddWordSubmit()" class="btn btn-primary" style="min-width:100px;">Add</button>
            </div>
        </div>
    `,
    search: () => `
        <div class="panel-section" style="margin-top:0;">
            <div class="panel-label" style="text-align:center;">Dictionary</div>
        </div>
        <div style="margin-top:20px; margin-bottom:10px;">
            <input type="text" id="searchInput" class="input" placeholder="Search dictionary..." oninput="handleSearch(this.value)" style="margin-bottom:0;">
        </div>
        <div id="searchResults"></div>
    `,
    settings: (isEdit = false) => {
        const pencilIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>`;
        
        const profileDisplay = isEdit 
            ? `<div style="display:flex; flex-direction:column; gap:10px; width:100%;">
                    <input id="editName" class="input" style="margin:0;" placeholder="Name">
                    <input id="editEmail" class="input" style="margin:0;" placeholder="Email">
                    <input id="editTelegramChatId" class="input" style="margin:0;" placeholder="TG ID (Optional)">
               </div>`
            : `<div style="display:flex; justify-content:space-between; align-items:flex-start; width:100%;">
                    <div>
                        <div id="settingsUserName" style="color:#fff; font-size:1.15rem; font-weight:700;"></div>
                        <div id="settingsUserEmail" style="color:var(--text-low); font-size:0.9rem; margin-top:4px;"></div>
                        <div id="settingsUserTelegram" style="color:var(--text-low); font-size:0.9rem; margin-top:4px;"></div>
                    </div>
                    <span onclick="renderSettingsPanel(true)" style="cursor:pointer; color:var(--text-low); padding:4px; transition:color 0.2s;" onmouseenter="this.style.color='var(--primary)'" onmouseleave="this.style.color='var(--text-low)'">${pencilIcon}</span>
                </div>`;

        const actionButtons = isEdit
            ? `<div style="margin-top:20px; display:flex; gap:12px; width:100%;">
                    <button class="btn btn-secondary btn-block" onclick="renderSettingsPanel(false)">Cancel</button>
                    <button class="btn btn-primary btn-block" onclick="saveProfile()">Save</button>
               </div>`
            : `<div style="margin-top:20px; display:flex; gap:12px; width:100%;">
                    <button class="btn btn-secondary btn-block" onclick="logout()">Logout</button>
                    <button class="btn btn-danger btn-block" onclick="deleteProfile()">Delete</button>
               </div>`;

        return `
            <div class="panel-section" style="margin-top:0;">
                <div class="panel-label" style="text-align:center;">Profile</div>
                <div class="card" style="padding:18px;">
                    ${profileDisplay}
                    ${actionButtons}
                </div>
            </div>
            
            <div class="panel-section" style="margin-top:20px;">
                <div class="panel-label" style="text-align:center;">Learning</div>
                <div class="setting-item">
                    <span style="color:var(--text-high); font-weight:500;">Dictionary</span>
                    <select class="input" style="width: auto; height: 38px; padding: 0 12px; margin: 0; text-align: right; border:none; background:transparent;" onchange="changeLanguage(this.value)">
                        <option value="de" ${currentLanguage === 'de' ? 'selected' : ''}>German</option>
                        <option value="en" ${currentLanguage === 'en' ? 'selected' : ''}>English</option>
                    </select>
                </div>
                <div class="setting-item">
                    <span style="color:var(--text-high); font-weight:500;">Daily Limit</span>
                    <select class="input" style="width: auto; height: 38px; padding: 0 12px; margin: 0; text-align: right; border:none; background:transparent;" onchange="saveLimit(this.value)">
                        ${[5, 10, 20, 30, 40].map(v => `<option value="${v}" ${userSettings.daily_limit === v ? 'selected' : ''}>${v} words</option>`).join('')}
                    </select>
                </div>
                <div class="setting-item">
                    <span style="color:var(--text-high); font-weight:500;">Notification Time</span>
                    <select class="input" style="width: auto; height: 38px; padding: 0 12px; margin: 0; text-align: right; border:none; background:transparent;" onchange="saveNotificationTime(this.value)">
                        <option value="-1" ${userSettings.notification_time === -1 ? 'selected' : ''}>Off</option>
                        ${Array.from({length: 18}, (_, i) => i + 6).map(v => `<option value="${v * 60}" ${userSettings.notification_time === v * 60 ? 'selected' : ''}>${v}:00</option>`).join('')}
                    </select>
                </div>
            </div>
        `;
    },
    practice: () => `
        <div class="practice-view" id="practiceView">
            <div class="practice-progress"><div class="practice-progress-inner" id="practiceProgressBar"></div></div>
            <div id="practiceCounter" class="practice-counter"></div>
            <div id="practiceGlow" class="practice-glow">
                <div class="swipe-feedback-content" id="swipeFeedback">
                    <div class="swipe-feedback-icon" id="swipeIcon"></div>
                    <div class="swipe-feedback-label" id="swipeLabel"></div>
                </div>
            </div>
            
            <div class="practice-container" id="practiceContainer">

                <div class="flash-card" id="flashCard">
                    <div id="cardTags"></div>
                    <div class="card-content question-layer" id="cardFront"></div>
                    <div class="card-content answer-layer" id="cardBack"></div>
                </div>
            </div>
            
            <div style="flex: 1; min-height: 20px;"></div>
            
            <div class="bottom-nav">
                <div class="nav-segment" onclick="closePractice()">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                </div>
                <div class="nav-segment" onclick="undoReview()">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10h10a5 5 0 0 1 5 5 5 5 0 0 1-5 5H5"></path><polyline points="8 5 3 10 8 15"></polyline></svg>
                </div>
                <div class="nav-segment" onclick="speakCurrentWord()">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path></svg>
                </div>
            </div>
        </div>
    `
};

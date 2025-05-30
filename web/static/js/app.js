/**
 * Newsletter Generator Web App
 * Frontend JavaScript for handling user interactions and API calls
 */

class NewsletterApp {
    constructor() {
        this.currentJobId = null;
        this.pollInterval = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadHistory();
        this.loadSchedules();
    }

    bindEvents() {
        // Tab switching
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => this.switchTab(e.target.id));
        });

        // Input method switching
        document.querySelectorAll('input[name="inputMethod"]').forEach(radio => {
            radio.addEventListener('change', () => this.toggleInputMethod());
        });

        // Schedule checkbox
        document.getElementById('enableSchedule').addEventListener('change', (e) => {
            this.toggleScheduleSettings(e.target.checked);
        });

        // Frequency change
        document.getElementById('frequency').addEventListener('change', () => {
            this.updateScheduleOptions();
        });

        // Action buttons
        document.getElementById('generateBtn').addEventListener('click', () => this.generateNewsletter());
        document.getElementById('previewBtn').addEventListener('click', () => this.previewNewsletter());
        document.getElementById('downloadBtn').addEventListener('click', () => this.downloadNewsletter());
        document.getElementById('sendEmailBtn').addEventListener('click', () => this.sendEmail());

        // Navigation buttons
        document.getElementById('historyBtn').addEventListener('click', () => this.switchTab('historyTab'));
        document.getElementById('scheduleBtn').addEventListener('click', () => this.switchTab('scheduleManageTab'));
    }

    switchTab(tabId) {
        // Remove active class from all tabs
        document.querySelectorAll('.tab-button').forEach(button => {
            button.classList.remove('active', 'bg-blue-100', 'text-blue-700');
            button.classList.add('text-gray-500', 'hover:text-gray-700');
        });

        // Hide all panels
        document.querySelectorAll('.tab-panel').forEach(panel => {
            panel.classList.add('hidden');
        });

        // Activate selected tab
        const selectedTab = document.getElementById(tabId);
        selectedTab.classList.add('active', 'bg-blue-100', 'text-blue-700');
        selectedTab.classList.remove('text-gray-500', 'hover:text-gray-700');

        // Show corresponding panel
        const panelMap = {
            'generateTab': 'generatePanel',
            'historyTab': 'historyPanel',
            'scheduleManageTab': 'scheduleManagePanel'
        };

        const panelId = panelMap[tabId];
        if (panelId) {
            document.getElementById(panelId).classList.remove('hidden');
            
            // Load data for specific tabs
            if (tabId === 'historyTab') {
                this.loadHistory();
            } else if (tabId === 'scheduleManageTab') {
                this.loadSchedules();
            }
        }
    }

    toggleInputMethod() {
        const method = document.querySelector('input[name="inputMethod"]:checked').value;
        const keywordsInput = document.getElementById('keywordsInput');
        const domainInput = document.getElementById('domainInput');

        if (method === 'keywords') {
            keywordsInput.classList.remove('hidden');
            domainInput.classList.add('hidden');
        } else {
            keywordsInput.classList.add('hidden');
            domainInput.classList.remove('hidden');
        }
    }

    toggleScheduleSettings(enabled) {
        const scheduleSettings = document.getElementById('scheduleSettings');
        if (enabled) {
            scheduleSettings.classList.remove('hidden');
        } else {
            scheduleSettings.classList.add('hidden');
        }
    }

    updateScheduleOptions() {
        const frequency = document.getElementById('frequency').value;
        const weeklyOptions = document.getElementById('weeklyOptions');

        if (frequency === 'WEEKLY') {
            weeklyOptions.classList.remove('hidden');
        } else {
            weeklyOptions.classList.add('hidden');
        }
    }

    async generateNewsletter() {
        const data = this.collectFormData();
        if (!data) return;

        this.showProgress();
        
        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            
            if (response.ok) {
                this.currentJobId = result.job_id;
                if (result.status === 'completed') {
                    this.showResults(result.result);
                } else {
                    this.startPolling(result.job_id);
                }
            } else {
                this.showError(result.error || 'Generation failed');
            }
        } catch (error) {
            this.showError('Network error: ' + error.message);
        }
    }

    async previewNewsletter() {
        // Similar to generate but without email sending
        const data = this.collectFormData();
        if (!data) return;

        // Remove email from preview
        delete data.email;
        data.preview_only = true;

        this.generateNewsletter();
    }

    collectFormData() {
        const method = document.querySelector('input[name="inputMethod"]:checked').value;
        const data = {};

        if (method === 'keywords') {
            const keywords = document.getElementById('keywords').value.trim();
            if (!keywords) {
                this.showError('키워드를 입력해주세요.');
                return null;
            }
            data.keywords = keywords.split(',').map(k => k.trim()).filter(k => k);
        } else {
            const domain = document.getElementById('domain').value.trim();
            if (!domain) {
                this.showError('도메인을 입력해주세요.');
                return null;
            }
            data.domain = domain;
        }

        const email = document.getElementById('email').value.trim();
        if (email) {
            data.email = email;
        }

        // Schedule data
        const enableSchedule = document.getElementById('enableSchedule').checked;
        if (enableSchedule) {
            if (!email) {
                this.showError('예약 발송을 위해서는 이메일 주소가 필요합니다.');
                return null;
            }

            const frequency = document.getElementById('frequency').value;
            const time = document.getElementById('scheduleTime').value;
            
            let rrule = `FREQ=${frequency}`;
            
            if (frequency === 'WEEKLY') {
                const selectedDays = Array.from(document.querySelectorAll('.weekday:checked'))
                    .map(cb => cb.value);
                if (selectedDays.length === 0) {
                    this.showError('주간 발송을 위해 요일을 선택해주세요.');
                    return null;
                }
                rrule += `;BYDAY=${selectedDays.join(',')}`;
            }

            const [hour, minute] = time.split(':');
            rrule += `;BYHOUR=${hour};BYMINUTE=${minute}`;

            data.rrule = rrule;
            data.schedule = true;
        }

        return data;
    }

    showProgress() {
        document.getElementById('progressSection').classList.remove('hidden');
        document.getElementById('resultsSection').classList.add('hidden');
        
        let progress = 0;
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        
        // Simulate progress
        const interval = setInterval(() => {
            progress += Math.random() * 10;
            if (progress > 90) progress = 90;
            
            progressBar.style.width = progress + '%';
            
            if (progress < 30) {
                progressText.textContent = '뉴스 수집 중...';
            } else if (progress < 60) {
                progressText.textContent = '내용 요약 중...';
            } else if (progress < 90) {
                progressText.textContent = '뉴스레터 구성 중...';
            }
        }, 500);

        // Clear interval when polling starts
        setTimeout(() => clearInterval(interval), 5000);
    }

    startPolling(jobId) {
        this.pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/status/${jobId}`);
                const result = await response.json();

                if (result.status === 'completed') {
                    this.stopPolling();
                    this.showResults(result.result);
                } else if (result.status === 'failed') {
                    this.stopPolling();
                    this.showError(result.result?.error || 'Generation failed');
                }
            } catch (error) {
                console.error('Polling error:', error);
            }
        }, 2000);
    }

    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }

    showResults(result) {
        document.getElementById('progressSection').classList.add('hidden');
        document.getElementById('resultsSection').classList.remove('hidden');

        const progressBar = document.getElementById('progressBar');
        progressBar.style.width = '100%';

        const preview = document.getElementById('newsletterPreview');
        preview.innerHTML = result.html_content || '<p>뉴스레터 내용을 불러올 수 없습니다.</p>';

        // Reload history
        this.loadHistory();
    }

    showError(message) {
        document.getElementById('progressSection').classList.add('hidden');
        alert('오류: ' + message);
    }

    async loadHistory() {
        try {
            const response = await fetch('/api/history');
            const history = await response.json();

            const historyList = document.getElementById('historyList');
            if (history.length === 0) {
                historyList.innerHTML = '<p class="text-gray-500">아직 생성된 뉴스레터가 없습니다.</p>';
                return;
            }

            historyList.innerHTML = history.map(item => `
                <div class="border-b border-gray-200 py-4">
                    <div class="flex justify-between items-start">
                        <div>
                            <h4 class="text-sm font-medium text-gray-900">
                                ${item.params?.keywords ? 
                                  `키워드: ${item.params.keywords.join(', ')}` : 
                                  `도메인: ${item.params?.domain || 'Unknown'}`}
                            </h4>
                            <p class="text-sm text-gray-500">${new Date(item.created_at).toLocaleString()}</p>
                            <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                item.status === 'completed' ? 'bg-green-100 text-green-800' :
                                item.status === 'failed' ? 'bg-red-100 text-red-800' :
                                'bg-yellow-100 text-yellow-800'
                            }">${item.status}</span>
                        </div>
                        <div class="space-x-2">
                            ${item.status === 'completed' ? `
                                <button onclick="app.viewHistoryItem('${item.id}')" 
                                        class="text-blue-600 hover:text-blue-900 text-sm">보기</button>
                                <button onclick="app.rerunHistoryItem('${item.id}')" 
                                        class="text-green-600 hover:text-green-900 text-sm">다시 실행</button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            console.error('Failed to load history:', error);
        }
    }

    async loadSchedules() {
        try {
            const response = await fetch('/api/schedules');
            const schedules = await response.json();

            const schedulesList = document.getElementById('schedulesList');
            if (schedules.length === 0) {
                schedulesList.innerHTML = '<p class="text-gray-500">예약된 발송이 없습니다.</p>';
                return;
            }

            schedulesList.innerHTML = schedules.map(schedule => `
                <div class="border-b border-gray-200 py-4">
                    <div class="flex justify-between items-start">
                        <div>
                            <h4 class="text-sm font-medium text-gray-900">
                                ${schedule.params?.keywords ? 
                                  `키워드: ${schedule.params.keywords.join(', ')}` : 
                                  `도메인: ${schedule.params?.domain || 'Unknown'}`}
                            </h4>
                            <p class="text-sm text-gray-500">
                                이메일: ${schedule.params?.email || 'Unknown'}
                            </p>
                            <p class="text-sm text-gray-500">
                                다음 실행: ${new Date(schedule.next_run).toLocaleString()}
                            </p>
                            <p class="text-sm text-gray-500">
                                규칙: ${schedule.rrule}
                            </p>
                        </div>
                        <div class="space-x-2">
                            <button onclick="app.runScheduleNow('${schedule.id}')" 
                                    class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm">
                                즉시 실행
                            </button>
                            <button onclick="app.cancelSchedule('${schedule.id}')" 
                                    class="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm">
                                취소
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            console.error('Failed to load schedules:', error);
        }
    }

    async cancelSchedule(scheduleId) {
        if (!confirm('이 예약을 취소하시겠습니까?')) return;

        try {
            const response = await fetch(`/api/schedule/${scheduleId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.loadSchedules(); // Reload schedules
            } else {
                const result = await response.json();
                alert('취소 실패: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            alert('Network error: ' + error.message);
        }
    }

    async runScheduleNow(scheduleId) {
        // This would trigger immediate execution of a scheduled newsletter
        alert('즉시 실행 기능은 추후 구현됩니다.');
    }

    async viewHistoryItem(itemId) {
        try {
            const response = await fetch(`/api/status/${itemId}`);
            const result = await response.json();

            if (result.result?.html_content) {
                // Switch to generate tab and show the result
                this.switchTab('generateTab');
                this.showResults(result.result);
            }
        } catch (error) {
            alert('Failed to load item: ' + error.message);
        }
    }

    async rerunHistoryItem(itemId) {
        try {
            const response = await fetch(`/api/status/${itemId}`);
            const result = await response.json();

            if (result.params) {
                // Populate form with historical parameters
                if (result.params.keywords) {
                    document.getElementById('keywordsMethod').checked = true;
                    document.getElementById('keywords').value = result.params.keywords.join(', ');
                } else if (result.params.domain) {
                    document.getElementById('domainMethod').checked = true;
                    document.getElementById('domain').value = result.params.domain;
                }

                if (result.params.email) {
                    document.getElementById('email').value = result.params.email;
                }

                this.toggleInputMethod();
                this.switchTab('generateTab');
            }
        } catch (error) {
            alert('Failed to load parameters: ' + error.message);
        }
    }

    downloadNewsletter() {
        // This would download the generated newsletter as HTML file
        alert('다운로드 기능은 추후 구현됩니다.');
    }

    sendEmail() {
        // This would send the newsletter via email
        alert('이메일 발송 기능은 추후 구현됩니다.');
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new NewsletterApp();
});

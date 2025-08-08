/**
 * Newsletter Generator Web App
 * Frontend JavaScript for handling user interactions and API calls
 */

class NewsletterApp {
    constructor() {
        this.currentJobId = null;
        this.pollInterval = null;
        // 상태 플래그 초기화
        this.isPolling = false;
        this.isGenerating = false;
        this.lastLoadedJobId = null;
        this.pollCount = 0;
        this.debug = window.location.hostname === 'localhost'; // 로컬에서만 디버깅
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
        document.getElementById('emailConfigBtn').addEventListener('click', () => this.checkEmailConfiguration());

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
        console.log('🔴 CRITICAL DEBUG: generateNewsletter() called');
        
        // 🔴 CRITICAL FIX: 중복 실행 방지
        if (this.isGenerating) {
            console.log('🔴 WARNING: 이미 뉴스레터 생성 중입니다. 요청을 무시합니다.');
            return;
        }
        
        // 기존 폴링 중단
        if (this.isPolling) {
            console.log('🔴 WARNING: 기존 폴링을 중단하고 새 작업을 시작합니다.');
            this.stopPolling();
        }
        
        this.isGenerating = true; // 생성 중 플래그 설정
        
        const data = this.collectFormData();
        if (!data) {
            console.log('🔴 CRITICAL DEBUG: collectFormData failed in generateNewsletter');
            this.isGenerating = false; // 플래그 리셋
            return;
        }

        console.log('🔴 CRITICAL DEBUG: Data to send:', data);
        this.showProgress();
        
        try {
            console.log('🔴 CRITICAL DEBUG: Making POST request to /api/generate');
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            console.log('🔴 CRITICAL DEBUG: Response status:', response.status);
            const result = await response.json();
            console.log('🔴 CRITICAL DEBUG: Response data:', result);
            
            if (response.ok) {
                this.currentJobId = result.job_id;
                if (result.status === 'completed') {
                    console.log('🔴 CRITICAL DEBUG: Job completed immediately, showing results');
                    console.log('🔴 CRITICAL DEBUG: Passing entire result object to showResults');
                    this.showResults(result);
                } else {
                    console.log('🔴 CRITICAL DEBUG: Job pending, starting polling for job_id:', result.job_id);
                    this.startPolling(result.job_id);
                }
            } else {
                console.log('🔴 CRITICAL DEBUG: API error:', result.error);
                this.isGenerating = false; // 에러 시 플래그 리셋
                this.showError(result.error || 'Generation failed');
            }
        } catch (error) {
            console.log('🔴 CRITICAL DEBUG: Network error:', error);
            this.isGenerating = false; // 에러 시 플래그 리셋
            this.showError('Network error: ' + error.message);
        }
    }

    async previewNewsletter() {
        console.log('🔴 CRITICAL DEBUG: previewNewsletter() called');
        
        // Similar to generate but without email sending
        const data = this.collectFormData();
        if (!data) {
            console.log('🔴 CRITICAL DEBUG: collectFormData failed');
            return;
        }

        console.log('🔴 CRITICAL DEBUG: Form data collected:', data);

        // Remove email from preview
        delete data.email;
        data.preview_only = true;

        console.log('🔴 CRITICAL DEBUG: Calling generateNewsletter with preview_only');
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

        // Template style selection
        const templateStyle = document.querySelector('input[name="templateStyle"]:checked');
        data.template_style = templateStyle ? templateStyle.value : 'compact';

        // Period selection
        const period = document.querySelector('input[name="period"]:checked');
        data.period = period ? parseInt(period.value) : 14;

        // Email compatibility option
        const emailCompatible = document.getElementById('emailCompatible');
        if (emailCompatible && emailCompatible.checked) {
            data.email_compatible = true;
        }
        // Note: If not explicitly checked, server will auto-enable if email is provided

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
        // 🔴 CRITICAL FIX: 중복 폴링 방지
        if (this.pollInterval) {
            console.log('🔴 WARNING: 이미 폴링 중입니다. 기존 폴링을 중단합니다.');
            this.stopPolling();
        }
        
        this.currentJobId = jobId; // Store current job ID
        this.pollCount = 0; // 폴링 횟수 카운터 추가
        this.maxPollCount = 900; // 최대 15분 (900초)
        this.isPolling = true; // 폴링 상태 플래그 추가
        
        console.log('🔴 STARTING POLLING for job:', jobId);
        
        this.pollInterval = setInterval(async () => {
            try {
                this.pollCount++;
                
                // 최대 폴링 횟수 초과 시 중단
                if (this.pollCount > this.maxPollCount) {
                    this.stopPolling();
                    this.showError('처리 시간이 너무 오래 걸립니다. 페이지를 새로고침하고 다시 시도해주세요.');
                    return;
                }

                const response = await fetch(`/api/status/${jobId}`);
                const result = await response.json();

                // Update progress text with email status
                const progressText = document.getElementById('progressText');
                if (result.sent) {
                    progressText.textContent = '뉴스레터 생성 완료 및 이메일 발송 완료...';
                } else {
                    progressText.textContent = `뉴스레터를 생성하고 있습니다... (${this.pollCount}초 경과)`;
                }

                if (result.status === 'completed') {
                    this.stopPolling();
                    console.log(`✅ 폴링 완료: ${this.pollCount}초 후 작업 완료`);
                    // Add job_id to result for iframe src
                    result.job_id = jobId;
                    console.log('🔴 CRITICAL DEBUG: Polling completed, passing entire result object to showResults');
                    this.showResults(result);
                    
                    // Show email success message
                    if (result.sent) {
                        this.showEmailSuccess(result.email_to || result.email);
                    }
                } else if (result.status === 'failed') {
                    this.stopPolling();
                    console.log(`❌ 폴링 중단: ${this.pollCount}초 후 작업 실패`);
                    this.showError(result.error || 'Generation failed');
                }
            } catch (error) {
                console.error('Polling error:', error);
                // 연속 오류 발생 시 폴링 중단
                if (this.pollCount > 10) {
                    this.stopPolling();
                    this.showError('서버와의 연결에 문제가 발생했습니다.');
                }
            }
        }, 1000); // 1초 간격으로 폴링
    }

    stopPolling() {
        console.log('🔴 STOPPING POLLING - Current state:', {
            hasInterval: !!this.pollInterval,
            isPolling: this.isPolling,
            pollCount: this.pollCount
        });
        
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        
        this.isPolling = false; // 폴링 상태 플래그 리셋
        this.pollCount = 0; // 카운터 리셋
        
        console.log('🔴 ✅ POLLING STOPPED');
    }

    showResults(result) {
        console.log('🔴 CRITICAL DEBUG: showResults called with:', result);
        console.log('🔴 CRITICAL DEBUG: result keys:', Object.keys(result || {}));
        console.log('🔴 CRITICAL DEBUG: generation_stats:', result.generation_stats);
        
        // 🔴 CRITICAL FIX: 작업 완료 시 플래그 리셋
        this.isGenerating = false;
        
        document.getElementById('progressSection').classList.add('hidden');
        document.getElementById('resultsSection').classList.remove('hidden');

        const progressBar = document.getElementById('progressBar');
        progressBar.style.width = '100%';

        const preview = document.getElementById('newsletterPreview');
        
        // Create detailed results display
        let detailsHtml = '';
        
        // Generation Statistics (handle both possible locations)
        const stats = result.generation_stats || result.result?.generation_stats || {};
        console.log('🔴 CRITICAL DEBUG: Using stats:', stats);
        
        if (stats && Object.keys(stats).length > 0) {
            detailsHtml += `
                <div class="mb-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <h4 class="text-lg font-semibold text-blue-800 mb-3">
                        <i class="fas fa-chart-bar mr-2"></i>Generation Statistics
                    </h4>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                        ${stats.total_time ? `
                            <div class="bg-white p-3 rounded shadow-sm">
                                <div class="font-medium text-gray-700">Total Time</div>
                                <div class="text-xl font-bold text-blue-600">${stats.total_time.toFixed(2)}s</div>
                            </div>
                        ` : ''}
                        ${stats.articles_count ? `
                            <div class="bg-white p-3 rounded shadow-sm">
                                <div class="font-medium text-gray-700">Articles Found</div>
                                <div class="text-xl font-bold text-green-600">${stats.articles_count}</div>
                            </div>
                        ` : ''}
                        ${result.html_size ? `
                            <div class="bg-white p-3 rounded shadow-sm">
                                <div class="font-medium text-gray-700">Newsletter Size</div>
                                <div class="text-xl font-bold text-purple-600">${(result.html_size / 1024).toFixed(1)}KB</div>
                            </div>
                        ` : ''}
                    </div>
                    ${stats.step_times ? this.renderStepTimes(stats.step_times) : ''}
                    ${stats.generated_keywords ? `
                        <div class="mt-3 p-3 bg-white rounded shadow-sm">
                            <div class="font-medium text-gray-700 mb-2">Generated Keywords</div>
                            <div class="text-sm text-gray-600">${stats.generated_keywords}</div>
                        </div>
                    ` : ''}
                </div>
            `;
        }
        
        // Processing Information
        if (result.processing_info) {
            const info = result.processing_info;
            detailsHtml += `
                <div class="mb-4 p-4 bg-green-50 rounded-lg border border-green-200">
                    <h4 class="text-lg font-semibold text-green-800 mb-3">
                        <i class="fas fa-cogs mr-2"></i>Processing Information
                    </h4>
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                        <div class="bg-white p-2 rounded shadow-sm">
                            <div class="font-medium text-gray-700">CLI Mode</div>
                            <div class="font-bold ${info.using_real_cli ? 'text-green-600' : 'text-orange-600'}">
                                ${info.using_real_cli ? 'Real CLI' : 'Mock CLI'}
                            </div>
                        </div>
                        <div class="bg-white p-2 rounded shadow-sm">
                            <div class="font-medium text-gray-700">Template</div>
                            <div class="font-bold text-gray-600">${info.template_style}</div>
                        </div>
                        <div class="bg-white p-2 rounded shadow-sm">
                            <div class="font-medium text-gray-700">Email Mode</div>
                            <div class="font-bold text-gray-600">${info.email_compatible ? 'Yes' : 'No'}</div>
                        </div>
                        <div class="bg-white p-2 rounded shadow-sm">
                            <div class="font-medium text-gray-700">Period</div>
                            <div class="font-bold text-gray-600">${info.period_days} days</div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Input Parameters
        if (result.input_params) {
            const params = result.input_params;
            detailsHtml += `
                <div class="mb-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                    <h4 class="text-lg font-semibold text-gray-800 mb-3">
                        <i class="fas fa-info-circle mr-2"></i>Input Parameters
                    </h4>
                    <div class="text-sm">
                        ${params.keywords ? `
                            <div class="mb-2">
                                <span class="font-medium text-gray-700">Keywords:</span>
                                <span class="ml-2 px-2 py-1 bg-blue-100 text-blue-800 rounded">${params.keywords}</span>
                            </div>
                        ` : ''}
                        ${params.domain ? `
                            <div class="mb-2">
                                <span class="font-medium text-gray-700">Domain:</span>
                                <span class="ml-2 px-2 py-1 bg-purple-100 text-purple-800 rounded">${params.domain}</span>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }
        
        // Newsletter Content
        detailsHtml += `
            <div class="p-4 bg-white rounded-lg border border-gray-200">
                <h4 class="text-lg font-semibold text-gray-800 mb-3">
                    <i class="fas fa-newspaper mr-2"></i>Newsletter Content
                </h4>
                <div class="border rounded bg-gray-50">
                    ${result.html_content || result.content ? 
                        `<iframe id="newsletterFrame" 
                                 style="width: 100%; height: 600px; border: none;" 
                                 sandbox="allow-same-origin allow-scripts">
                                 <p>Loading newsletter...</p>
                         </iframe>` :
                        '<p class="text-gray-500 p-4">Newsletter content could not be loaded.</p>'
                    }
                </div>
            </div>
        `;

        preview.innerHTML = detailsHtml;

        // Load HTML content - handle both possible field names
        const htmlContent = result.html_content || result.content;
        console.log('🔴 CRITICAL DEBUG: HTML Content available:', {
            hasHtmlContent: !!result.html_content,
            hasContent: !!result.content,
            usingContent: !!htmlContent,
            contentLength: htmlContent?.length || 0
        });
        
        if (htmlContent) {
            console.log('🔴 CRITICAL FRONTEND DEBUG:', {
                hasJobId: !!result.job_id,
                contentLength: htmlContent.length,
                jobId: result.job_id,
                contentPreview: htmlContent.substring(0, 200)
            });
            
            // 🔴 CRITICAL FIX: 중복 iframe 로딩 방지
            if (this.lastLoadedJobId === result.job_id) {
                console.log('🔴 WARNING: 동일한 job_id의 iframe이 이미 로딩되었습니다:', result.job_id);
                return;
            }
            
            const self = this; // Capture this for use in setTimeout
            setTimeout(() => {
                const iframe = document.getElementById('newsletterFrame');
                if (iframe) {
                    console.log('🔴 IFRAME FOUND, proceeding with content load');
                    
                    // 로딩된 job_id 기록
                    self.lastLoadedJobId = result.job_id;
                    
                    // Try API endpoint first if job_id is available
                    if (result.job_id) {
                        const apiUrl = `/api/newsletter-html/${result.job_id}`;
                        console.log(`🔴 TRYING API ENDPOINT: ${apiUrl}`);
                        
                        // Test API endpoint directly first
                        fetch(apiUrl)
                            .then(response => {
                                console.log('🔴 API RESPONSE STATUS:', response.status);
                                console.log('🔴 API RESPONSE HEADERS:', response.headers);
                                return response.text();
                            })
                            .then(html => {
                                console.log('🔴 API RESPONSE HTML LENGTH:', html.length);
                                console.log('🔴 API RESPONSE PREVIEW:', html.substring(0, 300));
                                
                                // Now set iframe src
                                iframe.src = apiUrl;
                                
                                iframe.onload = () => {
                                    console.log('🔴 ✅ IFRAME LOADED SUCCESSFULLY via API');
                                };
                                
                                iframe.onerror = () => {
                                    console.log('🔴 ❌ IFRAME FAILED TO LOAD, trying blob URL');
                                    self.loadContentWithBlobUrl(iframe, htmlContent);
                                };
                            })
                            .catch(error => {
                                console.log('🔴 ❌ API ENDPOINT FAILED:', error);
                                console.log('🔴 Falling back to blob URL');
                                self.loadContentWithBlobUrl(iframe, htmlContent);
                            });
                    } else {
                        // Use blob URL directly
                        console.log('🔴 NO JOB_ID, using blob URL directly');
                        self.loadContentWithBlobUrl(iframe, htmlContent);
                    }
                } else {
                    console.log('🔴 ❌ IFRAME NOT FOUND!');
                }
            }, 100);
        } else {
            console.log('🔴 ❌ NO HTML CONTENT IN RESULT');
        }

        // Update button states
        this.updateResultButtons(result);

        // Reload history
        this.loadHistory();
    }
    
    renderStepTimes(stepTimes) {
        if (!stepTimes || Object.keys(stepTimes).length === 0) return '';
        
        const maxTime = Math.max(...Object.values(stepTimes));
        
        return `
            <div class="mt-3 p-3 bg-white rounded shadow-sm">
                <div class="font-medium text-gray-700 mb-3">Processing Steps</div>
                <div class="space-y-2">
                    ${Object.entries(stepTimes).map(([step, time]) => `
                        <div class="flex items-center justify-between">
                            <span class="text-sm text-gray-600 capitalize">${step.replace(/_/g, ' ')}</span>
                            <div class="flex items-center space-x-2">
                                <div class="w-24 bg-gray-200 rounded-full h-2">
                                    <div class="bg-blue-500 h-2 rounded-full" style="width: ${(time / maxTime) * 100}%"></div>
                                </div>
                                <span class="text-sm font-medium text-gray-700">${time.toFixed(2)}s</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    loadContentWithBlobUrl(iframe, htmlContent) {
        console.log('🔴 LOADING WITH BLOB URL, content length:', htmlContent.length);
        console.log('🔴 HTML CONTENT PREVIEW:', htmlContent.substring(0, 200));
        
        try {
            const blob = new Blob([htmlContent], { type: 'text/html; charset=utf-8' });
            const blobUrl = URL.createObjectURL(blob);
            console.log('🔴 BLOB URL CREATED:', blobUrl);
            
            iframe.src = blobUrl;
            
            // Clean up blob URL after iframe loads
            iframe.onload = () => {
                console.log('🔴 ✅ BLOB URL LOADED SUCCESSFULLY');
                URL.revokeObjectURL(blobUrl);
            };
            
            // Handle blob load errors
            iframe.onerror = () => {
                console.error('🔴 ❌ BLOB URL FAILED, trying srcdoc');
                iframe.srcdoc = htmlContent; // Final fallback using srcdoc
                
                // Test if srcdoc works
                setTimeout(() => {
                    if (iframe.contentDocument && iframe.contentDocument.body) {
                        console.log('🔴 ✅ SRCDOC LOADED SUCCESSFULLY');
                    } else {
                        console.log('🔴 ❌ SRCDOC ALSO FAILED - COMPLETE FAILURE');
                    }
                }, 1000);
            };
        } catch (error) {
            console.error('🔴 ❌ ERROR CREATING BLOB URL:', error);
            console.log('🔴 TRYING SRCDOC AS FALLBACK');
            // Ultimate fallback - use srcdoc
            iframe.srcdoc = htmlContent;
            
            // Test if srcdoc works
            setTimeout(() => {
                if (iframe.contentDocument && iframe.contentDocument.body) {
                    console.log('🔴 ✅ FALLBACK SRCDOC LOADED SUCCESSFULLY');
                } else {
                    console.log('🔴 ❌ EVEN FALLBACK SRCDOC FAILED - SOMETHING IS VERY WRONG');
                }
            }, 1000);
        }
    }

    updateResultButtons(result) {
        const downloadBtn = document.getElementById('downloadBtn');
        const sendEmailBtn = document.getElementById('sendEmailBtn');
        
        // Enable/disable buttons based on result status
        if (result.status === 'success' && (result.html_content || result.content)) {
            downloadBtn.disabled = false;
            downloadBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            sendEmailBtn.disabled = false;
            sendEmailBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        } else {
            downloadBtn.disabled = true;
            downloadBtn.classList.add('opacity-50', 'cursor-not-allowed');
            sendEmailBtn.disabled = true;
            sendEmailBtn.classList.add('opacity-50', 'cursor-not-allowed');
        }
    }

    showError(message) {
        document.getElementById('progressSection').classList.add('hidden');
        alert('오류: ' + message);
    }

    showEmailSuccess(email) {
        // Create and show success notification
        const notification = document.createElement('div');
        notification.className = 'fixed top-4 right-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded shadow-lg z-50';
        notification.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-check-circle mr-2"></i>
                <span>✅ 메일 발송 완료: ${email}</span>
                <button class="ml-4 text-green-700 hover:text-green-900" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
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
                                  `키워드: ${Array.isArray(item.params.keywords) ? item.params.keywords.join(', ') : item.params.keywords}` : 
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
                                  `키워드: ${Array.isArray(schedule.params.keywords) ? schedule.params.keywords.join(', ') : schedule.params.keywords}` : 
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
            console.log('viewHistoryItem called with itemId:', itemId);
            const response = await fetch(`/api/status/${itemId}`);
            const result = await response.json();
            console.log('API response:', result);

            if (result.result?.html_content) {
                console.log('HTML content found, switching to generate tab');
                // Add job_id to result for iframe src
                result.result.job_id = itemId;
                this.currentJobId = itemId;
                // Switch to generate tab and show the result
                this.switchTab('generateTab');
                this.showResults(result.result);
                console.log('Results displayed successfully');
            } else {
                console.log('No HTML content found in result');
                alert('뉴스레터 콘텐츠를 찾을 수 없습니다.');
            }
        } catch (error) {
            console.error('Error in viewHistoryItem:', error);
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
                    document.getElementById('keywords').value = Array.isArray(result.params.keywords) ? result.params.keywords.join(', ') : result.params.keywords;
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
        if (!this.currentJobId) {
            // Try to get HTML content from current result
            const iframe = document.getElementById('newsletterFrame');
            if (iframe && iframe.src && iframe.src.startsWith('blob:')) {
                alert('다운로드 기능을 위해 페이지를 새로고침하거나 뉴스레터를 다시 생성해주세요.');
                return;
            }
            
            alert('다운로드할 뉴스레터가 없습니다.');
            return;
        }

        // Create a link to download from the API endpoint
        const downloadUrl = `/api/newsletter-html/${this.currentJobId}`;
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = `newsletter_${this.currentJobId}.html`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    async sendEmail() {
        if (!this.currentJobId) {
            alert('발송할 뉴스레터가 없습니다.');
            return;
        }

        const email = document.getElementById('email').value.trim();
        if (!email) {
            alert('이메일 주소를 입력해주세요.');
            return;
        }

        // 이메일 설정 확인
        try {
            const configResponse = await fetch('/api/email-config');
            const configResult = await configResponse.json();
            
            if (!configResult.ready) {
                if (confirm('이메일 설정이 완료되지 않았습니다. 테스트 이메일을 발송해보시겠습니까?')) {
                    await this.sendTestEmail(email);
                    return;
                } else {
                    alert('이메일 발송을 위해 환경변수 설정이 필요합니다:\n- POSTMARK_SERVER_TOKEN\n- POSTMARK_FROM_EMAIL');
                    return;
                }
            }
        } catch (error) {
            console.error('Email config check failed:', error);
        }

        try {
            const response = await fetch('/api/send-email', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    job_id: this.currentJobId,
                    email: email
                })
            });

            const result = await response.json();
            
            if (response.ok) {
                alert('이메일이 성공적으로 발송되었습니다!');
            } else {
                alert('이메일 발송 실패: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            alert('Network error: ' + error.message);
        }
    }

    async sendTestEmail(email) {
        if (!email) {
            email = prompt('테스트 이메일을 받을 주소를 입력하세요:');
            if (!email) return;
        }

        try {
            const response = await fetch('/api/test-email', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email: email })
            });

            const result = await response.json();
            
            if (response.ok) {
                alert(`테스트 이메일이 ${email}로 발송되었습니다!\n메시지 ID: ${result.message_id || 'N/A'}`);
            } else {
                alert('테스트 이메일 발송 실패: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            alert('Network error: ' + error.message);
        }
    }

    async checkEmailConfiguration() {
        try {
            const response = await fetch('/api/email-config');
            const result = await response.json();
            
            let message = '이메일 설정 상태:\n';
            message += `Postmark 토큰: ${result.postmark_token_configured ? '✓ 설정됨' : '✗ 미설정'}\n`;
            message += `발신자 이메일: ${result.from_email_configured ? '✓ 설정됨' : '✗ 미설정'}\n`;
            message += `전체 상태: ${result.ready ? '✓ 준비 완료' : '✗ 설정 필요'}`;
            
            alert(message);
            
            if (!result.ready) {
                const testEmail = prompt('테스트 이메일을 발송해보시겠습니까? (이메일 주소 입력)');
                if (testEmail) {
                    await this.sendTestEmail(testEmail);
                }
            }
            
        } catch (error) {
            alert('설정 확인 실패: ' + error.message);
        }
    }

    escapeHtmlForSrcdoc(html) {
        return html
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\n/g, '\\n')
            .replace(/\r/g, '\\r');
    }

    async suggestKeywords() {
        const domainInput = document.getElementById('domain');
        const domain = domainInput.value.trim();
        const resultDiv = document.getElementById('keywords-result');
        const button = document.getElementById('btn-suggest');

        if (!domain) {
            resultDiv.innerHTML = '<div class="text-red-600 text-sm">도메인을 입력해주세요.</div>';
            return;
        }

        // Show loading state
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>추천 중...';
        resultDiv.innerHTML = '<div class="text-blue-600 text-sm">키워드를 생성하고 있습니다...</div>';

        try {
            const response = await fetch('/api/suggest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ domain: domain })
            });

            const data = await response.json();

            if (response.ok && data.keywords && data.keywords.length > 0) {
                // Display suggested keywords
                const keywordsList = data.keywords.map(keyword => 
                    `<span class="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full mr-2 mb-2 cursor-pointer hover:bg-blue-200" onclick="app.addKeywordToInput('${keyword}')">${keyword}</span>`
                ).join('');
                
                resultDiv.innerHTML = `
                    <div class="text-sm text-gray-700 mb-2">추천 키워드 (클릭하여 추가):</div>
                    <div class="flex flex-wrap">${keywordsList}</div>
                    <button onclick="app.useAllKeywords(${JSON.stringify(data.keywords).replace(/"/g, '&quot;')})" 
                            class="mt-2 text-xs bg-green-100 text-green-800 px-2 py-1 rounded hover:bg-green-200">
                        모든 키워드 사용
                    </button>
                `;
            } else {
                resultDiv.innerHTML = '<div class="text-yellow-600 text-sm">키워드를 생성할 수 없습니다. 다른 도메인을 시도해보세요.</div>';
            }
        } catch (error) {
            resultDiv.innerHTML = '<div class="text-red-600 text-sm">오류가 발생했습니다: ' + error.message + '</div>';
        } finally {
            // Restore button state
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-lightbulb mr-1"></i>추천받기';
        }
    }

    addKeywordToInput(keyword) {
        const keywordsInput = document.getElementById('keywords');
        const currentKeywords = keywordsInput.value.trim();
        
        if (currentKeywords) {
            keywordsInput.value = currentKeywords + ', ' + keyword;
        } else {
            keywordsInput.value = keyword;
        }
        
        // Switch to keywords method
        document.getElementById('keywordsMethod').checked = true;
        this.toggleInputMethod();
    }

    useAllKeywords(keywords) {
        const keywordsInput = document.getElementById('keywords');
        keywordsInput.value = keywords.join(', ');
        
        // Switch to keywords method
        document.getElementById('keywordsMethod').checked = true;
        this.toggleInputMethod();
    }
}

// Global function for onclick handlers
function suggestKeywords() {
    app.suggestKeywords();
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new NewsletterApp();
});

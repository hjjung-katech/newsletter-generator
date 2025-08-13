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
        
        // 시간 동기화 관련
        this.serverTimeOffset = 0; // 서버와 클라이언트 시간 차이 (ms)
        this.timeSyncInterval = null;
        this.lastTimeSyncTime = null;
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadHistory();
        this.loadSchedules();
        this.initTimeSync();
        this.startTimeDisplay();
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
            this.updateSchedulePreview();
        });
        
        // Time change
        document.getElementById('scheduleTime').addEventListener('change', () => {
            this.updateSchedulePreview();
        });
        
        // Weekday changes
        document.querySelectorAll('.weekday').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateSchedulePreview();
            });
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
        const schedulePreview = document.getElementById('schedulePreview');
        
        if (enabled) {
            scheduleSettings.classList.remove('hidden');
            schedulePreview.classList.remove('hidden');
            this.updateSchedulePreview();
        } else {
            scheduleSettings.classList.add('hidden');
            schedulePreview.classList.add('hidden');
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
        
        // 스케줄이 설정된 경우 스케줄 생성 API 호출
        if (data.schedule) {
            this.showProgress('스케줄을 생성하고 있습니다...');
            await this.createSchedule(data);
            return;
        }
        
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
                this.showError('관심 주제를 입력해주세요.');
                return null;
            }
            data.domain = domain;
            
            // Add suggest_count for domain method
            const suggestCountSelect = document.getElementById('suggest-count');
            if (suggestCountSelect) {
                data.suggest_count = parseInt(suggestCountSelect.value) || 10;
            }
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
            const scheduleSettings = this.getScheduleSettings();
            if (scheduleSettings) {
                data.schedule = scheduleSettings;
            } else {
                return null; // 스케줄 설정이 잘못된 경우
            }
        }

        return data;
    }

    showProgress(customMessage = null) {
        document.getElementById('progressSection').classList.remove('hidden');
        document.getElementById('resultsSection').classList.add('hidden');
        
        let progress = 0;
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        
        // 사용자 정의 메시지가 있으면 고정 메시지 사용
        if (customMessage) {
            progressText.textContent = customMessage;
            progressBar.style.width = '50%';
            return;
        }
        
        // Simulate progress for newsletter generation
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
    
    hideProgress() {
        document.getElementById('progressSection').classList.add('hidden');
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
                                ${this.formatHistoryKeywords(item)}
                            </h4>
                            ${item.result?.generation_info?.generated_keywords ? 
                              `<p class="text-xs text-blue-600 mt-1">🔄 생성된 키워드: ${item.result.generation_info.generated_keywords.join(', ')}</p>` : ''}
                            ${item.result?.generation_info?.generation_time ? 
                              `<p class="text-xs text-gray-400 mt-1">⏰ 키워드 생성 시간: ${new Date(item.result.generation_info.generation_time).toLocaleString()}</p>` : ''}
                            <p class="text-sm text-gray-500">${item.created_at_display || new Date(item.created_at).toLocaleString()}</p>
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

    formatHistoryKeywords(item) {
        // 새로운 데이터 구조 우선 처리 (source_type, source_value)
        const sourceType = item.result?.source_type || item.params?.source_type;
        const sourceValue = item.result?.source_value || item.params?.source_value;
        
        // 1. source_type이 정의된 경우 (최신 시스템)
        if (sourceType && sourceValue) {
            if (sourceType === 'domain' || sourceType === 'topic') {
                return `🎯 주제: ${sourceValue}`;
            } else if (sourceType === 'keywords') {
                // source_value가 문자열이면 파싱, 배열이면 그대로 사용
                const keywords = Array.isArray(sourceValue) ? sourceValue : 
                               typeof sourceValue === 'string' ? sourceValue.split(',').map(k => k.trim()) : [sourceValue];
                return `📝 키워드: ${keywords.join(', ')}`;
            }
        }
        
        // 2. 레거시 데이터 구조 fallback (keywords, domain)
        if (item.params?.keywords) {
            const keywords = Array.isArray(item.params.keywords) ? 
                           item.params.keywords : 
                           [item.params.keywords];
            return `📝 키워드: ${keywords.join(', ')}`;
        }
        
        if (item.params?.domain) {
            return `🎯 도메인: ${item.params.domain}`;
        }
        
        if (item.params?.topic) {
            return `🎯 주제: ${item.params.topic}`;
        }
        
        // 3. 최후 fallback
        if (sourceValue) {
            return `📝 정보: ${sourceValue}`;
        }
        
        return `📝 키워드: 정보 없음`;
    }

    async loadSchedules() {
        try {
            const response = await fetch('/api/schedules');
            const data = await response.json();

            const schedulesList = document.getElementById('schedulesList');
            
            // 기존 내용 초기화
            schedulesList.innerHTML = '';
            
            // 현재 서버 시간 표시 (unified format)
            if (data.current_time_display || data.current_time_kst) {
                const currentTimeDisplay = document.createElement('div');
                currentTimeDisplay.className = 'mb-4 p-3 bg-blue-50 rounded-lg';
                currentTimeDisplay.innerHTML = `
                    <div class="flex items-center justify-between">
                        <div>
                            <span class="text-sm font-medium text-blue-900">현재 서버 시간 (KST)</span>
                            <div class="text-lg font-mono text-blue-700" id="currentServerTime">${data.current_time_display || data.current_time_kst}</div>
                        </div>
                        <div class="text-xs text-blue-600">
                            <div>Timezone: ${data.timezone}</div>
                            <div id="timeDiffInfo" class="text-blue-500"></div>
                        </div>
                    </div>
                `;
                
                // 기존 시간 표시 제거 후 새로 추가
                const existingTimeDisplay = schedulesList.querySelector('.bg-blue-50');
                if (existingTimeDisplay) {
                    existingTimeDisplay.remove();
                }
                schedulesList.appendChild(currentTimeDisplay);
                
                this.updateTimeDifference(data.current_time || data.server_time);
            }
            
            const schedules = data.schedules || data;
            
            if (!Array.isArray(schedules) || schedules.length === 0) {
                const noSchedulesDiv = document.createElement('div');
                noSchedulesDiv.innerHTML = '<p class="text-gray-500 mt-4">예약된 발송이 없습니다.</p>';
                schedulesList.appendChild(noSchedulesDiv);
                return;
            }

            const schedulesHtml = schedules.map(schedule => `
                <div class="border-b border-gray-200 py-4">
                    <div class="flex justify-between items-start">
                        <div class="flex-1">
                            <h4 class="text-sm font-medium text-gray-900 mb-2">
                                ${schedule.params?.source_type === 'domain' || schedule.params?.source_type === 'topic' ? 
                                  `🎯 주제: ${schedule.params.source_value || schedule.params?.domain || schedule.params?.topic || 'Unknown'} (매번 새 키워드 생성)` :
                                  schedule.params?.keywords ? 
                                  `📝 키워드: ${Array.isArray(schedule.params.keywords) ? schedule.params.keywords.join(', ') : schedule.params.keywords}` : 
                                  `📝 키워드: ${schedule.params?.source_value || 'Unknown'}`}
                            </h4>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm text-gray-600">
                                <div>
                                    <span class="font-medium">이메일:</span> ${schedule.params?.email || 'Unknown'}
                                </div>
                                <div>
                                    <span class="font-medium">템플릿:</span> ${schedule.params?.template_style || 'compact'}
                                </div>
                                <div class="col-span-full">
                                    <span class="font-medium">다음 실행:</span> 
                                    <span class="font-mono ${schedule.is_overdue ? 'text-red-600' : 'text-blue-600'}">${schedule.next_run_display || schedule.next_run_kst || new Date(schedule.next_run).toLocaleString()}</span>
                                    ${schedule.time_until_next ? `<span class="ml-2 text-xs px-2 py-1 rounded-full ${schedule.is_overdue ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-600'}">${schedule.time_until_next}</span>` : ''}
                                </div>
                                <div class="col-span-full text-xs text-gray-500">
                                    <span class="font-medium">RRULE:</span> ${schedule.rrule}
                                </div>
                            </div>
                        </div>
                        <div class="ml-4 space-x-2">
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
            
            const schedulesContainer = document.createElement('div');
            schedulesContainer.innerHTML = schedulesHtml;
            schedulesList.appendChild(schedulesContainer);
            
        } catch (error) {
            console.error('Failed to load schedules:', error);
            const schedulesList = document.getElementById('schedulesList');
            schedulesList.innerHTML = '<p class="text-red-500">스케줄 로딩 실패: ' + error.message + '</p>';
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
        if (!confirm('이 스케줄을 지금 즉시 실행하시겠습니까?')) return;
        
        try {
            const response = await fetch(`/api/schedule/${scheduleId}/run`, {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (response.ok) {
                if (result.status === 'queued') {
                    alert(`뉴스레터 생성이 시작되었습니다.\nJob ID: ${result.job_id}`);
                } else if (result.status === 'completed') {
                    alert('뉴스레터가 성공적으로 생성되고 발송되었습니다.');
                }
            } else {
                alert('실행 실패: ' + (result.error || 'Unknown error'));
            }
        } catch (error) {
            alert('Network error: ' + error.message);
        }
    }
    
    // ===== 시간 동기화 관련 메소드들 =====
    
    async initTimeSync() {
        try {
            await this.syncServerTime();
            // 5분마다 시간 동기화
            this.timeSyncInterval = setInterval(() => this.syncServerTime(), 5 * 60 * 1000);
        } catch (error) {
            console.error('Failed to initialize time sync:', error);
        }
    }
    
    async syncServerTime() {
        try {
            const startTime = Date.now();
            const response = await fetch('/api/time-sync');
            const data = await response.json();
            const endTime = Date.now();
            
            // 네트워크 지연을 고려한 서버 시간 계산 (unified format)
            const networkDelay = (endTime - startTime) / 2;
            const serverTime = new Date(data.utc_time || data.server_time_iso).getTime();
            const adjustedServerTime = serverTime + networkDelay;
            
            this.serverTimeOffset = adjustedServerTime - endTime;
            this.lastTimeSyncTime = endTime;
            
            console.log(`Time sync completed. Offset: ${this.serverTimeOffset}ms, Delay: ${networkDelay}ms`);
            
            // UI 업데이트 (unified format)
            this.updateTimeDifference(data.utc_time || data.server_time_iso);
            
        } catch (error) {
            console.error('Time sync failed:', error);
        }
    }
    
    updateTimeDifference(serverTimeIso) {
        try {
            const serverTime = new Date(serverTimeIso);
            const clientTime = new Date();
            const diffMs = Math.abs(serverTime.getTime() - clientTime.getTime());
            const diffMinutes = Math.floor(diffMs / (1000 * 60));
            
            const timeDiffInfo = document.getElementById('timeDiffInfo');
            if (timeDiffInfo) {
                if (diffMinutes === 0) {
                    timeDiffInfo.textContent = '시간 동기화 완료';
                    timeDiffInfo.className = 'text-green-600';
                } else if (diffMinutes < 5) {
                    timeDiffInfo.textContent = `클라이언트와 ${diffMinutes}분 차이`;
                    timeDiffInfo.className = 'text-yellow-600';
                } else {
                    timeDiffInfo.textContent = `클라이언트와 ${diffMinutes}분 차이 (주의)`;
                    timeDiffInfo.className = 'text-red-600';
                }
            }
        } catch (error) {
            console.error('Failed to update time difference:', error);
        }
    }
    
    getCurrentServerTime() {
        if (!this.lastTimeSyncTime) return new Date();
        
        const now = Date.now();
        const timeSinceSync = now - this.lastTimeSyncTime;
        return new Date(now + this.serverTimeOffset);
    }
    
    startTimeDisplay() {
        // 현재 시간을 1초마다 업데이트
        setInterval(() => {
            const serverTime = this.getCurrentServerTime();
            const currentServerTimeEl = document.getElementById('currentServerTime');
            if (currentServerTimeEl) {
                currentServerTimeEl.textContent = serverTime.toLocaleString('ko-KR', {
                    year: 'numeric',
                    month: '2-digit', 
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                    timeZone: 'Asia/Seoul'
                }) + ' KST';
            }
        }, 1000);
    }
    
    // ===== 스케줄 설정 관련 메소드들 =====
    
    getScheduleSettings() {
        try {
            const frequency = document.getElementById('frequency').value;
            const time = document.getElementById('scheduleTime').value;
            
            if (!time) {
                this.showError('발송 시간을 설정해주세요.');
                return null;
            }
            
            // RRULE 생성
            let rrule = `FREQ=${frequency}`;
            
            // 요일 설정 (주간 발송인 경우)
            if (frequency === 'WEEKLY') {
                const selectedDays = Array.from(document.querySelectorAll('.weekday:checked'))
                    .map(cb => cb.value);
                if (selectedDays.length === 0) {
                    this.showError('주간 발송을 위해 요일을 선택해주세요.');
                    return null;
                }
                rrule += `;BYDAY=${selectedDays.join(',')}`;
            }
            
            // 시간 설정
            const [hour, minute] = time.split(':');
            rrule += `;BYHOUR=${hour};BYMINUTE=${minute}`;
            
            // 다음 실행 시간 미리보기 계산
            const nextRun = this.calculateNextRun(rrule);
            const nextRunText = nextRun ? nextRun.toLocaleString('ko-KR', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                timeZone: 'Asia/Seoul'
            }) + ' KST' : '계산 실패';
            
            return {
                rrule: rrule,
                frequency: frequency,
                time: time,
                next_run_preview: nextRunText
            };
        } catch (error) {
            console.error('Failed to get schedule settings:', error);
            this.showError('스케줄 설정 처리 중 오류가 발생했습니다.');
            return null;
        }
    }
    
    calculateNextRun(rruleString) {
        try {
            // 간단한 RRULE 파싱 및 다음 실행 시간 계산
            // 실제로는 서버에서 더 정확히 계산되지만, UI 미리보기용
            
            const now = this.getCurrentServerTime();
            const parts = rruleString.split(';');
            const freq = parts.find(p => p.startsWith('FREQ='))?.split('=')[1];
            const hourPart = parts.find(p => p.startsWith('BYHOUR='))?.split('=')[1];
            const minutePart = parts.find(p => p.startsWith('BYMINUTE='))?.split('=')[1];
            const daysPart = parts.find(p => p.startsWith('BYDAY='))?.split('=')[1];
            
            if (!freq || !hourPart || !minutePart) return null;
            
            const hour = parseInt(hourPart);
            const minute = parseInt(minutePart);
            
            let nextRun = new Date(now);
            nextRun.setHours(hour, minute, 0, 0);
            
            // 이미 지난 시간이면 다음으로
            if (nextRun <= now) {
                if (freq === 'DAILY') {
                    nextRun.setDate(nextRun.getDate() + 1);
                } else if (freq === 'WEEKLY') {
                    // 간단한 주간 처리 - 다음 주
                    nextRun.setDate(nextRun.getDate() + 7);
                } else if (freq === 'MONTHLY') {
                    nextRun.setMonth(nextRun.getMonth() + 1);
                }
            }
            
            return nextRun;
        } catch (error) {
            console.error('Failed to calculate next run:', error);
            return null;
        }
    }
    
    async createSchedule(data) {
        try {
            const scheduleData = {
                keywords: data.keywords,
                domain: data.domain,
                suggest_count: data.suggest_count || 10,  // 도메인 기반 키워드 생성 개수
                email: data.email,
                template_style: data.template_style,
                email_compatible: data.email_compatible,
                period: data.period,
                rrule: data.schedule.rrule
            };
            
            console.log('Creating schedule with data:', scheduleData);
            
            const response = await fetch('/api/schedule', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(scheduleData)
            });
            
            let result;
            const contentType = response.headers.get('content-type');
            
            if (contentType && contentType.includes('application/json')) {
                result = await response.json();
            } else {
                // HTML 에러 응답 처리
                const text = await response.text();
                throw new Error(`Server returned non-JSON response (status: ${response.status}): ${text.substring(0, 100)}...`);
            }
            
            if (response.ok) {
                this.isGenerating = false;
                this.hideProgress();
                
                // 성공 메시지 표시
                // 테스트 모드 또는 경고 메시지 구성
                let warningHtml = '';
                if (result.is_test || result.test_mode) {
                    warningHtml = `
                        <div class="mt-3 p-3 bg-orange-100 border border-orange-300 rounded">
                            <div class="flex">
                                <div class="flex-shrink-0">
                                    <i class="fas fa-exclamation-triangle text-orange-500"></i>
                                </div>
                                <div class="ml-2 text-sm text-orange-800">
                                    <strong>테스트 모드:</strong> ${result.warning || `${result.time_until_execution_minutes || '10'}분 후 실행 예정 - 1시간 후 자동 비활성화됩니다.`}
                                </div>
                            </div>
                        </div>
                    `;
                } else if (result.warning) {
                    warningHtml = `
                        <div class="mt-3 p-3 bg-yellow-100 border border-yellow-300 rounded">
                            <div class="flex">
                                <div class="flex-shrink-0">
                                    <i class="fas fa-info-circle text-yellow-500"></i>
                                </div>
                                <div class="ml-2 text-sm text-yellow-800">
                                    ${result.warning}
                                </div>
                            </div>
                        </div>
                    `;
                }

                const successHtml = `
                    <div class="bg-green-50 border border-green-200 rounded-lg p-6">
                        <div class="flex">
                            <div class="flex-shrink-0">
                                <svg class="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                                </svg>
                            </div>
                            <div class="ml-3">
                                <h3 class="text-sm font-medium text-green-800">스케줄이 성공적으로 생성되었습니다!</h3>
                                <div class="mt-2 text-sm text-green-700">
                                    <div class="space-y-1">
                                        <div><strong>스케줄 ID:</strong> <code class="bg-green-100 px-1 rounded">${result.schedule_id}</code></div>
                                        <div><strong>다음 실행 시간:</strong> <span class="font-mono">${result.next_run_display || result.next_run_kst}</span></div>
                                        <div><strong>RRULE:</strong> <code class="bg-green-100 px-1 rounded text-xs">${result.rrule}</code></div>
                                        <div><strong>현재 서버 시간:</strong> <span class="font-mono">${result.current_time_display || result.current_time_kst}</span></div>
                                    </div>
                                </div>
                                ${warningHtml}
                                <div class="mt-3">
                                    <button onclick="app.switchTab('scheduleManageTab')" 
                                            class="bg-green-600 hover:bg-green-700 text-white px-3 py-2 rounded text-sm">
                                        스케줄 관리로 이동
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                document.getElementById('resultsSection').classList.remove('hidden');
                document.getElementById('newsletterPreview').innerHTML = successHtml;
                
                // 스케줄 목록 새로고침
                this.loadSchedules();
                
            } else {
                this.isGenerating = false;
                this.hideProgress();
                this.showError('스케줄 생성 실패: ' + (result.error || 'Unknown error'));
            }
            
        } catch (error) {
            console.error('Failed to create schedule:', error);
            this.isGenerating = false;
            this.hideProgress();
            this.showError('스케줄 생성 중 오류 발생: ' + error.message);
        }
    }
    
    updateSchedulePreview() {
        try {
            const scheduleSettings = this.getScheduleSettings();
            const previewElement = document.getElementById('nextRunPreview');
            const testModeWarning = document.getElementById('testModeWarning');
            
            if (!previewElement) return;
            
            if (scheduleSettings && scheduleSettings.next_run_preview) {
                previewElement.innerHTML = `
                    <div class="font-mono">${scheduleSettings.next_run_preview}</div>
                    <div class="text-xs mt-1">
                        <div>빈도: ${scheduleSettings.frequency === 'DAILY' ? '매일' : 
                                      scheduleSettings.frequency === 'WEEKLY' ? '매주' : 
                                      scheduleSettings.frequency === 'MONTHLY' ? '매월' : scheduleSettings.frequency}</div>
                        <div>시간: ${scheduleSettings.time}</div>
                        <div>RRULE: <code class="text-xs bg-blue-100 px-1 rounded">${scheduleSettings.rrule}</code></div>
                    </div>
                `;
                
                // 테스트 모드 감지 (10분 이내 스케줄)
                if (scheduleSettings.time_until_execution_minutes !== undefined) {
                    const minutesUntil = scheduleSettings.time_until_execution_minutes;
                    if (testModeWarning) {
                        if (minutesUntil <= 10 && minutesUntil >= 1) {
                            testModeWarning.classList.remove('hidden');
                            testModeWarning.innerHTML = `
                                <i class="fas fa-exclamation-triangle mr-1"></i>
                                <strong>테스트 모드:</strong> ${minutesUntil.toFixed(1)}분 후 실행 예정 - 1시간 후 자동 비활성화됩니다.
                            `;
                        } else if (minutesUntil < 1) {
                            testModeWarning.classList.remove('hidden');
                            testModeWarning.innerHTML = `
                                <i class="fas fa-times-circle mr-1"></i>
                                <strong>오류:</strong> 최소 1분 이후 시간을 선택해주세요.
                            `;
                            testModeWarning.className = testModeWarning.className.replace('bg-orange-100 border-orange-300 text-orange-800', 'bg-red-100 border-red-300 text-red-800');
                        } else {
                            testModeWarning.classList.add('hidden');
                        }
                    }
                }
            } else {
                previewElement.innerHTML = `
                    <div class="text-orange-600">설정을 확인해주세요</div>
                    <div class="text-xs mt-1">모든 필드를 올바르게 입력하면 미리보기가 표시됩니다.</div>
                `;
                if (testModeWarning) {
                    testModeWarning.classList.add('hidden');
                }
            }
        } catch (error) {
            console.error('Failed to update schedule preview:', error);
            const previewElement = document.getElementById('nextRunPreview');
            if (previewElement) {
                previewElement.innerHTML = `
                    <div class="text-red-600">미리보기 오류</div>
                    <div class="text-xs mt-1">${error.message}</div>
                `;
            }
        }
    }

    async viewHistoryItem(itemId) {
        try {
            console.log('viewHistoryItem called with itemId:', itemId);
            const response = await fetch(`/api/status/${itemId}`);
            const result = await response.json();
            console.log('API response:', result);

            if (result.html_content) {
                console.log('HTML content found, switching to generate tab');
                // Add job_id to result for iframe src
                result.job_id = itemId;
                this.currentJobId = itemId;
                // Switch to generate tab and show the result
                this.switchTab('generateTab');
                this.showResults(result);
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
        const suggestCountSelect = document.getElementById('suggest-count');
        const suggestCount = parseInt(suggestCountSelect.value) || 10;
        const resultDiv = document.getElementById('keywords-result');
        const button = document.getElementById('btn-suggest');

        if (!domain) {
            resultDiv.innerHTML = '<div class="text-red-600 text-sm">관심 주제를 입력해주세요.</div>';
            return;
        }

        // Show loading state
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>추천 중...';
        resultDiv.innerHTML = `<div class="text-blue-600 text-sm">${suggestCount}개 키워드를 생성하고 있습니다...</div>`;

        try {
            const response = await fetch('/api/suggest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    domain: domain,
                    count: suggestCount 
                })
            });

            const data = await response.json();

            if (response.ok && data.keywords && data.keywords.length > 0) {
                // Store suggested keywords for editing
                this.suggestedKeywords = [...data.keywords];
                this.currentDomain = domain;
                
                // Display editable keywords
                this.renderEditableKeywords(data.keywords, domain);
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

    renderEditableKeywords(keywords, domain) {
        const resultDiv = document.getElementById('keywords-result');
        
        // Create editable keywords HTML
        const editableKeywords = keywords.map((keyword, index) => `
            <div class="inline-flex items-center bg-blue-100 text-blue-800 text-sm px-3 py-2 rounded-full mr-2 mb-2 group">
                <input type="text" 
                       value="${keyword}" 
                       class="bg-transparent border-none outline-none text-sm min-w-0 flex-1"
                       onchange="app.updateKeyword(${index}, this.value)"
                       onkeypress="if(event.key==='Enter') this.blur()">
                <button onclick="app.removeKeyword(${index})" 
                        class="ml-2 text-blue-600 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity">
                    <i class="fas fa-times text-xs"></i>
                </button>
            </div>
        `).join('');
        
        resultDiv.innerHTML = `
            <div class="space-y-4">
                <div>
                    <div class="text-sm text-gray-700 mb-2">생성된 키워드 (클릭하여 편집):</div>
                    <div class="flex flex-wrap" id="editable-keywords">
                        ${editableKeywords}
                        <button onclick="app.addNewKeyword()" 
                                class="inline-flex items-center bg-gray-100 text-gray-600 text-sm px-3 py-2 rounded-full hover:bg-gray-200">
                            <i class="fas fa-plus mr-1"></i>추가
                        </button>
                    </div>
                </div>
                
                <div class="flex flex-wrap gap-2">
                    <button onclick="app.useEditedKeywords()" 
                            class="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-md">
                        <i class="fas fa-edit mr-1"></i>수정된 키워드로 뉴스레터 생성
                    </button>
                    
                    <button onclick="app.generateDirectFromDomain('${domain}')" 
                            class="bg-green-600 hover:bg-green-700 text-white text-sm px-4 py-2 rounded-md">
                        <i class="fas fa-rocket mr-1"></i>도메인에서 직접 생성
                    </button>
                    
                    <button onclick="app.resetKeywords()" 
                            class="bg-gray-500 hover:bg-gray-600 text-white text-sm px-4 py-2 rounded-md">
                        <i class="fas fa-undo mr-1"></i>원래대로
                    </button>
                </div>
            </div>
        `;
    }

    updateKeyword(index, newValue) {
        if (this.suggestedKeywords && index < this.suggestedKeywords.length) {
            this.suggestedKeywords[index] = newValue.trim();
        }
    }

    removeKeyword(index) {
        if (this.suggestedKeywords && index < this.suggestedKeywords.length) {
            this.suggestedKeywords.splice(index, 1);
            this.renderEditableKeywords(this.suggestedKeywords, this.currentDomain);
        }
    }

    addNewKeyword() {
        const newKeyword = prompt('새 키워드를 입력하세요:');
        if (newKeyword && newKeyword.trim()) {
            this.suggestedKeywords.push(newKeyword.trim());
            this.renderEditableKeywords(this.suggestedKeywords, this.currentDomain);
        }
    }

    useEditedKeywords() {
        const validKeywords = this.suggestedKeywords.filter(k => k && k.trim());
        if (validKeywords.length === 0) {
            alert('최소 하나 이상의 키워드가 필요합니다.');
            return;
        }
        
        const keywordsInput = document.getElementById('keywords');
        keywordsInput.value = validKeywords.join(', ');
        
        // Switch to keywords method
        document.getElementById('keywordsMethod').checked = true;
        this.toggleInputMethod();
        
        // Show success message
        const resultDiv = document.getElementById('keywords-result');
        resultDiv.innerHTML = `<div class="text-green-600 text-sm">키워드가 설정되었습니다. 뉴스레터를 생성해보세요.</div>`;
    }

    async generateDirectFromDomain(domain) {
        // Confirm with user
        if (!confirm(`주제 "${domain}"에서 직접 뉴스레터를 생성하시겠습니까? (키워드 수정 없이 진행)`)) {
            return;
        }
        
        // Set domain method and generate directly
        document.getElementById('domainMethod').checked = true;
        document.getElementById('domain').value = domain;
        this.toggleInputMethod();
        
        // Clear results and show generating message
        const resultDiv = document.getElementById('keywords-result');
        resultDiv.innerHTML = `<div class="text-blue-600 text-sm">도메인에서 직접 뉴스레터를 생성하고 있습니다...</div>`;
        
        // Generate newsletter
        this.generateNewsletter();
    }

    resetKeywords() {
        if (this.suggestedKeywords && this.currentDomain) {
            // Reload original keywords from API
            this.suggestKeywords();
        }
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

(function(root, factory) {
    const helpers = factory();
    root.NewsletterAppRequestResponseHelpers = helpers;

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = helpers;
    }
})(typeof window !== 'undefined' ? window : globalThis, function() {
    function normalizeArchiveReference(entry = {}) {
        return {
            job_id: entry.job_id,
            title: entry.title || entry.job_id,
            snippet: entry.snippet || '선택된 참고본 세부 정보를 불러오지 못했습니다.',
            source_value: entry.source_value || '',
            created_at: entry.created_at || null
        };
    }

    function buildGenerationRequest(formState = {}, options = {}) {
        const includeSchedule = options.includeSchedule !== false;
        const includeEmail = options.includeEmail !== false;
        const method = formState.method === 'domain' ? 'domain' : 'keywords';
        const data = {};

        if (method === 'keywords') {
            const keywords = String(formState.keywordsInput || '').trim();
            if (!keywords) {
                return { error: '키워드를 입력해주세요.' };
            }

            data.keywords = keywords.split(',').map((keyword) => keyword.trim()).filter(Boolean);
        } else {
            const domain = String(formState.domainInput || '').trim();
            if (!domain) {
                return { error: '도메인을 입력해주세요.' };
            }

            data.domain = domain;
        }

        const email = String(formState.emailInput || '').trim();
        if (includeEmail && email) {
            data.email = email;
        }

        data.period = Number.parseInt(formState.periodValue, 10);
        data.template_style = formState.templateStyle || 'compact';
        data.email_compatible = Boolean(formState.emailCompatible);

        if (Array.isArray(formState.archiveReferenceIds) && formState.archiveReferenceIds.length) {
            data.archive_reference_ids = formState.archiveReferenceIds.slice();
        }

        if (includeSchedule && formState.enableSchedule) {
            if (!email) {
                return { error: '예약 발송을 위해서는 이메일 주소가 필요합니다.' };
            }

            const frequency = formState.frequency;
            const time = String(formState.scheduleTime || '');
            let rrule = `FREQ=${frequency}`;

            if (frequency === 'WEEKLY') {
                const selectedDays = Array.isArray(formState.selectedWeekdays)
                    ? formState.selectedWeekdays.filter(Boolean)
                    : [];
                if (!selectedDays.length) {
                    return { error: '주간 발송을 위해 요일을 선택해주세요.' };
                }
                rrule += `;BYDAY=${selectedDays.join(',')}`;
            }

            const [hour, minute] = time.split(':');
            rrule += `;BYHOUR=${hour};BYMINUTE=${minute}`;

            data.rrule = rrule;
            data.schedule = true;
        }

        return { data };
    }

    function buildPresetPayload({ params, name, description, isDefault }) {
        const normalizedName = String(name || '').trim();
        if (!normalizedName) {
            return { error: '프리셋 이름을 입력해주세요.' };
        }

        return {
            payload: {
                name: normalizedName,
                description: String(description || '').trim(),
                is_default: Boolean(isDefault),
                params
            }
        };
    }

    function buildSourcePolicyPayload({ pattern, policyType, isActive }) {
        const normalizedPattern = String(pattern || '').trim();
        if (!normalizedPattern) {
            return { error: '소스 패턴을 입력해주세요.' };
        }

        return {
            payload: {
                pattern: normalizedPattern,
                policy_type: policyType,
                is_active: Boolean(isActive)
            }
        };
    }

    function normalizeGenerationResultEnvelope(result = {}, jobId = null) {
        if (!result || !result.result) {
            return null;
        }

        const normalized = { ...result.result };
        if (jobId) {
            normalized.job_id = jobId;
        }

        if (Object.prototype.hasOwnProperty.call(result, 'sent')) {
            normalized.sent = result.sent;
        }

        ['approval_status', 'delivery_status', 'approved_at', 'rejected_at', 'approval_note'].forEach((field) => {
            if (result[field] !== undefined && result[field] !== null) {
                normalized[field] = result[field];
            }
        });

        return normalized;
    }

    function buildStepTimesHtml(stepTimes) {
        if (!stepTimes || Object.keys(stepTimes).length === 0) {
            return '';
        }

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

    function buildResultDetailsHtml(result = {}) {
        let detailsHtml = '';

        if (result.delivery_status || result.approval_status) {
            const approvalLabelMap = {
                pending: ['승인 대기', 'bg-amber-100 text-amber-800'],
                approved: ['승인 완료', 'bg-green-100 text-green-800'],
                rejected: ['반려됨', 'bg-red-100 text-red-800'],
                not_requested: ['승인 불필요', 'bg-slate-100 text-slate-700']
            };
            const deliveryLabelMap = {
                draft: ['Draft', 'bg-slate-100 text-slate-700'],
                pending_approval: ['승인 대기', 'bg-amber-100 text-amber-800'],
                approved: ['승인됨', 'bg-blue-100 text-blue-800'],
                sent: ['발송 완료', 'bg-green-100 text-green-800'],
                send_failed: ['발송 실패', 'bg-red-100 text-red-800']
            };
            const approvalBadge = approvalLabelMap[result.approval_status];
            const deliveryBadge = deliveryLabelMap[result.delivery_status];
            detailsHtml += `
                <div class="mb-4 p-4 bg-amber-50 rounded-lg border border-amber-200">
                    <h4 class="text-lg font-semibold text-amber-900 mb-3">
                        <i class="fas fa-shield-alt mr-2"></i>Delivery Review
                    </h4>
                    <div class="flex flex-wrap gap-2 text-sm">
                        ${approvalBadge ? `<span class="inline-flex px-2.5 py-1 rounded-full font-semibold ${approvalBadge[1]}">Approval: ${approvalBadge[0]}</span>` : ''}
                        ${deliveryBadge ? `<span class="inline-flex px-2.5 py-1 rounded-full font-semibold ${deliveryBadge[1]}">Delivery: ${deliveryBadge[0]}</span>` : ''}
                    </div>
                    ${result.approved_at ? `<p class="mt-2 text-sm text-gray-600">승인 시각: ${new Date(result.approved_at).toLocaleString()}</p>` : ''}
                    ${result.rejected_at ? `<p class="mt-2 text-sm text-gray-600">반려 시각: ${new Date(result.rejected_at).toLocaleString()}</p>` : ''}
                    ${result.approval_note ? `<p class="mt-2 text-sm text-gray-600">메모: ${result.approval_note}</p>` : ''}
                </div>
            `;
        }

        if (result.generation_stats) {
            const stats = result.generation_stats;
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
                    ${stats.step_times ? buildStepTimesHtml(stats.step_times) : ''}
                    ${stats.generated_keywords ? `
                        <div class="mt-3 p-3 bg-white rounded shadow-sm">
                            <div class="font-medium text-gray-700 mb-2">Generated Keywords</div>
                            <div class="text-sm text-gray-600">${stats.generated_keywords}</div>
                        </div>
                    ` : ''}
                </div>
            `;
        }

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

        if (result.input_params) {
            const params = result.input_params;
            const archiveReferences = Array.isArray(result.archive_references)
                ? result.archive_references
                : [];
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
                        ${archiveReferences.length ? `
                            <div class="mt-3 rounded-md border border-blue-100 bg-blue-50 p-3">
                                <div class="font-medium text-gray-700">Archive References</div>
                                <ul class="mt-2 space-y-2">
                                    ${archiveReferences.map((reference) => `
                                        <li class="text-sm text-gray-600">
                                            <span class="font-medium text-gray-800">${reference.title}</span>
                                            <span class="block text-xs text-gray-500">${reference.source_value || reference.job_id}</span>
                                        </li>
                                    `).join('')}
                                </ul>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }

        detailsHtml += `
            <div class="p-4 bg-white rounded-lg border border-gray-200">
                <h4 class="text-lg font-semibold text-gray-800 mb-3">
                    <i class="fas fa-newspaper mr-2"></i>Newsletter Content
                </h4>
                <div class="border rounded bg-gray-50">
                    ${result.html_content
                        ? (
                            result.job_id
                                ? `<iframe id="newsletterFrame"
                                     style="width: 100%; height: 600px; border: none;"
                                     src="/api/newsletter-html/${result.job_id}"
                                     sandbox="allow-same-origin allow-scripts">
                             </iframe>`
                                : `<iframe id="newsletterFrame"
                                     style="width: 100%; height: 600px; border: none;"
                                     sandbox="allow-same-origin allow-scripts">
                             </iframe>`
                        )
                        : '<p class="text-gray-500 p-4">Newsletter content could not be loaded.</p>'
                    }
                </div>
            </div>
        `;

        return detailsHtml;
    }

    return Object.freeze({
        normalizeArchiveReference,
        buildGenerationRequest,
        buildPresetPayload,
        buildSourcePolicyPayload,
        normalizeGenerationResultEnvelope,
        buildStepTimesHtml,
        buildResultDetailsHtml
    });
});

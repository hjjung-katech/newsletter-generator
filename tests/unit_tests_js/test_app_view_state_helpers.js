const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const repoRoot = path.resolve(__dirname, '../..');
const helpers = require(path.join(repoRoot, 'web/static/js/app_view_state_helpers.js'));

test('resolveResultButtonState enables actions only for successful html results', () => {
    assert.deepEqual(
        helpers.resolveResultButtonState({
            status: 'success',
            html_content: '<html>ok</html>'
        }),
        {
            downloadDisabled: false,
            sendEmailDisabled: false
        }
    );

    assert.deepEqual(
        helpers.resolveResultButtonState({
            status: 'processing',
            html_content: ''
        }),
        {
            downloadDisabled: true,
            sendEmailDisabled: true
        }
    );
});

test('buildHistoryListHtml renders derived badges and actions for completed items', () => {
    const html = helpers.buildHistoryListHtml([
        {
            id: 'job-pending',
            created_at: '2026-03-12T00:00:00Z',
            status: 'completed',
            approval_status: 'pending',
            result: {
                html_content: '<html>pending</html>'
            },
            execution_visibility: {
                status_category: 'completed',
                status_label: '완료',
                status_message: '생성은 완료되었고 승인 대기 중입니다.',
                primary_timestamp: '2026-03-12T00:00:00Z',
                approval_label: '승인 대기'
            },
            params: {
                keywords: ['AI', 'Battery']
            }
        },
        {
            id: 'job-approved',
            created_at: '2026-03-12T01:00:00Z',
            status: 'completed',
            approval_status: 'approved',
            personalization_visibility: {
                personalization_state: 'default',
                status_label: '기본 개인화',
                status_message: '현재 개인화 설정은 기본값으로 유지됩니다.',
                effective_template_style: 'compact',
                effective_period: 14,
                email_mode_label: '기본 모드',
                override_count: 0,
                override_labels: []
            },
            execution_visibility: {
                status_category: 'completed',
                status_label: '완료',
                status_message: '최근 실행이 완료되었습니다.',
                primary_timestamp: '2026-03-12T01:00:00Z'
            },
            params: {
                domain: 'Mobility'
            }
        }
    ]);

    assert.match(html, /키워드: AI, Battery/);
    assert.match(html, /도메인: Mobility/);
    assert.match(html, /bg-green-100 text-green-800\">완료/);
    assert.match(html, /bg-amber-100 text-amber-800\">승인 대기/);
    assert.match(html, /생성은 완료되었고 승인 대기 중입니다/);
    assert.match(html, /개인화: 템플릿 compact · 14일 · 기본 모드/);
    assert.match(html, /app\.approveHistoryItem\('job-pending'\)/);
    assert.match(html, /app\.rerunHistoryItem\('job-approved'\)/);
});

test('buildApprovalsListHtml renders delivery view model with note and actions', () => {
    const html = helpers.buildApprovalsListHtml([
        {
            id: 'approval-1',
            created_at: '2026-03-12T02:00:00Z',
            approval_status: 'pending',
            delivery_status: 'pending_approval',
            approval_note: 'review this',
            approval_visibility: {
                approval_state: 'pending',
                approval_label: '승인 대기',
                approval_message: '검토 후 승인 또는 반려할 수 있습니다.',
                primary_timestamp: '2026-03-12T02:00:00Z',
                timestamp_label: '요청 시각',
                can_approve: true,
                can_reject: true
            },
            execution_visibility: {
                status_category: 'completed',
                status_label: '완료',
                status_message: '생성은 완료되었고 승인 대기 중입니다.',
                approval_label: '승인 대기',
                delivery_label: '승인 대기'
            },
            params: {
                domain: 'Semiconductor',
                email: 'ops@example.com'
            }
        },
        {
            id: 'approval-2',
            created_at: '2026-03-12T03:00:00Z',
            approval_status: 'approved',
            delivery_status: 'approved',
            approval_visibility: {
                approval_state: 'approved',
                approval_label: '승인 완료',
                approval_message: '승인이 완료되었습니다. 이제 발송할 수 있습니다.',
                primary_timestamp: '2026-03-12T03:05:00Z',
                timestamp_label: '승인 시각',
                can_approve: false,
                can_reject: false
            },
            execution_visibility: {
                status_category: 'completed',
                status_label: '완료',
                status_message: '생성은 완료되었고 발송 준비가 끝났습니다.',
                approval_label: '승인 완료',
                delivery_label: '승인됨'
            },
            params: {
                keywords: ['Battery'],
                email: 'approved@example.com'
            }
        }
    ]);

    assert.match(html, /도메인: Semiconductor/);
    assert.match(html, /이메일: ops@example.com/);
    assert.match(html, /메모: review this/);
    assert.match(html, /승인 대기/);
    assert.match(html, /검토 후 승인 또는 반려할 수 있습니다/);
    assert.match(html, /요청 시각:/);
    assert.match(html, /app\.rejectHistoryItem\('approval-1'\)/);
    assert.match(html, /승인이 완료되었습니다\. 이제 발송할 수 있습니다/);
    assert.match(html, /승인 시각:/);
    assert.doesNotMatch(html, /app\.approveHistoryItem\('approval-2'\)/);
    assert.doesNotMatch(html, /app\.rejectHistoryItem\('approval-2'\)/);
});

test('resolveApprovalVisibility normalizes fallback states and action availability', () => {
    assert.deepEqual(
        helpers.resolveApprovalVisibility({
            approval_status: 'pending',
            status: 'completed',
            created_at: '2026-03-12T04:00:00Z',
            result: { html_content: '<html>ok</html>' }
        }),
        {
            rawApprovalStatus: 'pending',
            approvalState: 'pending',
            approvalLabel: '승인 대기',
            approvalMessage: '검토 후 승인 또는 반려할 수 있습니다.',
            primaryTimestamp: '2026-03-12T04:00:00Z',
            timestampLabel: '기준 시각',
            canResolve: true,
            canApprove: true,
            canReject: true,
            isResolved: false
        }
    );
});

test('analytics helpers render summary cards and deduplicated event payloads', () => {
    const cardsHtml = helpers.buildAnalyticsSummaryCardsHtml({
        generation: {
            completed: 8,
            failed: 1,
            success_rate: 88.9,
            average_duration_seconds: 12.3,
            total_cost_usd: 1.2345
        },
        email: {
            sent: 5,
            failed: 1,
            deduplicated: 2
        },
        schedule: {
            completed: 4,
            failed: 1,
            created: 6,
            queued: 2
        }
    });
    const eventsHtml = helpers.buildAnalyticsEventsHtml([
        {
            event_type: 'schedule_run',
            status: 'queued',
            deduplicated: true,
            created_at: '2026-03-12T03:00:00Z',
            job_id: 'job-1',
            schedule_id: 'sched-1',
            payload: {
                mode: 'async',
                template_style: 'compact'
            }
        }
    ]);

    assert.match(cardsHtml, /Generation/);
    assert.match(cardsHtml, /Email Delivery/);
    assert.match(cardsHtml, /deduplicated 2/);
    assert.match(eventsHtml, /schedule_run/);
    assert.match(eventsHtml, /deduplicated/);
    assert.match(eventsHtml, /mode<\/span>: async/);
});

test('source policy helpers summarize linkage, recent execution, and render badges', () => {
    const policies = [
        {
            id: 'policy-block',
            pattern: 'zeta.com',
            policy_type: 'block',
            is_active: false,
            updated_at: '2026-03-12T04:00:00Z',
            source_policy_visibility: {
                visibility_state: 'disabled',
                status_label: '비활성',
                status_message: '비활성 상태라 현재 실행에는 적용되지 않습니다.',
                linked_preset_count: 0,
                linked_default_preset_count: 0
            }
        },
        {
            id: 'policy-allow',
            pattern: 'alpha.com',
            policy_type: 'allow',
            is_active: true,
            updated_at: '2026-03-12T05:00:00Z',
            linked_presets: [
                { id: 'preset-1', name: 'Alpha Watch', is_default: true }
            ],
            preset_linkage_visibility: {
                link_state: 'matched',
                message: '연결된 도메인 프리셋 1개, 기본 프리셋 1개',
                linked_preset_count: 1,
                linked_default_preset_count: 1
            },
            latest_related_execution: {
                job_id: 'job-1',
                created_at: '2026-03-12T06:00:00Z',
                execution_visibility: {
                    status_category: 'completed',
                    status_label: '완료',
                    status_message: '최근 실행에서 이 정책이 실제로 반영되었습니다.',
                    primary_timestamp: '2026-03-12T06:00:00Z',
                    result_title: 'Alpha Brief'
                }
            },
            source_policy_visibility: {
                visibility_state: 'applied',
                status_label: '최근 반영',
                status_message: '최근 실행에서 이 정책이 실제로 반영되었습니다.',
                linked_preset_count: 1,
                linked_default_preset_count: 1,
                linked_preset_names: ['Alpha Watch'],
                recent_usage_state: 'recent',
                policy_type_label: 'Allow 정책'
            }
        }
    ];
    const summary = helpers.summarizeSourcePolicies(policies);
    const html = helpers.buildSourcePoliciesHtml(policies);

    assert.equal(summary.message, '활성 정책 1개 (allow 1 / block 0) · 프리셋 연결 1개 · 최근 반영 1개');
    assert.ok(html.indexOf('alpha.com') < html.indexOf('zeta.com'));
    assert.match(html, /최근 반영/);
    assert.match(html, /비활성/);
    assert.match(html, /Alpha Watch/);
    assert.match(html, /최근 실행/);
    assert.match(html, /Alpha Brief/);
    assert.match(html, /app\.toggleSourcePolicyActive\('policy-block', true\)/);
});

test('schedule list helper renders params, next run, and actions', () => {
    const html = helpers.buildSchedulesListHtml([
        {
            id: 'schedule-1',
            next_run: '2026-03-12T06:00:00Z',
            rrule: 'FREQ=WEEKLY;BYDAY=MO',
            latest_execution: {
                status_category: 'completed',
                status_label: '완료',
                status_message: '최근 예약 실행이 완료되었습니다.',
                primary_timestamp: '2026-03-12T05:00:00Z'
            },
            params: {
                keywords: ['AI'],
                email: 'alerts@example.com'
            }
        }
    ]);

    assert.match(html, /키워드: AI/);
    assert.match(html, /alerts@example.com/);
    assert.match(html, /FREQ=WEEKLY;BYDAY=MO/);
    assert.match(html, /최근 예약 실행이 완료되었습니다/);
    assert.match(html, /완료/);
    assert.match(html, /app\.runScheduleNow\('schedule-1'\)/);
});

test('history and schedule helpers fall back to empty execution visibility for missing runs', () => {
    const schedulesHtml = helpers.buildSchedulesListHtml([
        {
            id: 'schedule-2',
            next_run: '2026-03-12T07:00:00Z',
            rrule: 'FREQ=DAILY',
            params: { domain: 'battery.com', email: 'ops@example.com' }
        }
    ]);

    assert.match(schedulesHtml, /실행 이력 없음/);
    assert.match(schedulesHtml, /아직 실행 이력이 없습니다/);
});

test('preset selection helper renders default, recent execution, and source policy visibility', () => {
    const view = helpers.resolvePresetSelectionView({
        selectedPresetId: 'preset-1',
        preset: {
            id: 'preset-1',
            name: 'Domain Watch',
            description: 'Monitor Reuters',
            is_default: true,
            updated_at: '2026-03-13T09:00:00Z',
            preset_visibility: {
                availability_state: 'available',
                preset_type_label: '도메인 프리셋',
                is_scheduled: false
            },
            latest_related_execution: {
                job_id: 'job-1',
                created_at: '2026-03-13T08:00:00Z',
                title: 'Reuters digest',
                execution_visibility: {
                    status_category: 'completed',
                    status_label: '완료',
                    status_message: '최근 실행이 완료되었습니다.'
                }
            },
            source_policy_visibility: {
                link_state: 'matched',
                message: '활성 소스 정책 1개와 연결됩니다. (allow 1 / block 0)'
            },
            personalization_visibility: {
                personalization_state: 'overridden',
                status_label: '오버라이드 적용',
                status_message: '기본값 대비 개인화 오버라이드 2개가 적용됩니다.',
                effective_template_style: 'modern',
                effective_period: 7,
                email_mode_label: '이메일 호환 모드',
                override_count: 2,
                override_labels: ['템플릿 스타일', '기간'],
                source_policy_message: '활성 소스 정책 1개와 연결됩니다. (allow 1 / block 0)'
            }
        }
    });

    assert.equal(view.statusTone, 'green');
    assert.match(view.statusMessage, /Domain Watch: Monitor Reuters/);
    assert.match(view.detailsHtml, /선택됨/);
    assert.match(view.detailsHtml, /기본/);
    assert.match(view.detailsHtml, /도메인 프리셋/);
    assert.match(view.detailsHtml, /오버라이드 적용/);
    assert.match(view.detailsHtml, /개인화: 템플릿 modern · 7일 · 이메일 호환 모드/);
    assert.match(view.detailsHtml, /오버라이드: 템플릿 스타일, 기간/);
    assert.match(view.detailsHtml, /최근 연관 실행/);
    assert.match(view.detailsHtml, /Reuters digest/);
    assert.match(view.detailsHtml, /활성 소스 정책 1개와 연결됩니다/);
});

test('preset selection helper falls back when there is no related execution', () => {
    const view = helpers.resolvePresetSelectionView({
        selectedPresetId: '',
        preset: {
            id: 'preset-2',
            name: 'Weekly AI',
            description: '',
            is_default: false,
            preset_visibility: {
                availability_state: 'available',
                preset_type_label: '키워드 프리셋',
                is_scheduled: true
            },
            source_policy_visibility: {
                link_state: 'unavailable',
                message: '키워드 프리셋이라 직접 연결된 소스 정책을 확인할 수 없습니다.'
            }
        }
    });

    assert.equal(view.statusTone, 'gray');
    assert.match(view.statusMessage, /Weekly AI 프리셋이 준비되었습니다/);
    assert.match(view.detailsHtml, /연관된 최근 실행 이력이 없습니다/);
    assert.match(view.detailsHtml, /예약/);
    assert.match(view.detailsHtml, /키워드 프리셋이라 직접 연결된 소스 정책을 확인할 수 없습니다/);
});

test('personalization helper resolves default and overridden summaries', () => {
    const defaultVisibility = helpers.resolvePersonalizationVisibility({
        personalization_visibility: {
            personalization_state: 'default',
            status_label: '기본 개인화',
            effective_template_style: 'compact',
            effective_period: 14,
            email_mode_label: '기본 모드',
            override_count: 0,
            override_labels: []
        }
    });
    const overriddenHtml = helpers.buildPersonalizationMetaHtml({
        personalization_visibility: {
            personalization_state: 'overridden',
            status_label: '오버라이드 적용',
            status_message: '기본값 대비 개인화 오버라이드 3개가 적용됩니다.',
            effective_template_style: 'modern',
            effective_period: 7,
            email_mode_label: '이메일 호환 모드',
            override_count: 3,
            override_labels: ['템플릿 스타일', '기간', '아카이브 컨텍스트'],
            archive_reference_count: 1,
            source_policy_message: '활성 소스 정책 1개와 연결됩니다.'
        }
    });

    assert.equal(defaultVisibility.personalizationState, 'default');
    assert.equal(defaultVisibility.statusLabel, '기본 개인화');
    assert.match(overriddenHtml, /개인화: 템플릿 modern · 7일 · 이메일 호환 모드 · 아카이브 1개/);
    assert.match(overriddenHtml, /오버라이드: 템플릿 스타일, 기간, 아카이브 컨텍스트/);
    assert.match(overriddenHtml, /활성 소스 정책 1개와 연결됩니다/);
});

test('section state helpers preserve empty, error, and content decisions', () => {
    assert.match(
        helpers.resolveHistorySectionState({ history: [] }).html,
        /아직 생성된 뉴스레터가 없습니다/
    );
    assert.match(
        helpers.resolveApprovalsSectionState({
            approvals: []
        }).html,
        /승인 요청 이력이 없습니다/
    );
    assert.match(
        helpers.resolveApprovalsSectionState({
            errorMessage: '권한이 없습니다.',
            errorTone: 'yellow'
        }).html,
        /text-amber-600/
    );
    assert.match(
        helpers.resolveSchedulesSectionState({
            schedules: [{ id: 'schedule-1', next_run: '2026-03-12T06:00:00Z', rrule: 'FREQ=WEEKLY', params: {} }]
        }).html,
        /schedule-1/
    );
});

test('analytics and source policy section helpers preserve derived section state', () => {
    const analytics = helpers.resolveAnalyticsSectionState({
        result: {
            window_days: 7,
            summary: { generation: { completed: 2 } },
            recent_events: [{ event_type: 'schedule_run' }]
        }
    });
    assert.equal(analytics.statusTone, 'green');
    assert.equal(analytics.summary.generation.completed, 2);
    assert.equal(analytics.events.length, 1);

    const emptyPolicies = helpers.resolveSourcePoliciesSectionState({
        sourcePolicies: [],
        editingSourcePolicyId: ''
    });
    assert.match(emptyPolicies.html, /등록된 소스 정책이 없습니다/);
    assert.equal(emptyPolicies.shouldResetForm, true);

    const errorPolicies = helpers.resolveSourcePoliciesSectionState({
        errorMessage: '소스 정책을 불러올 수 없습니다.',
        errorTone: 'red'
    });
    assert.equal(errorPolicies.statusTone, 'red');
    assert.match(errorPolicies.html, /text-red-600/);

    const detachedPolicies = helpers.resolveSourcePoliciesSectionState({
        sourcePolicies: [
            {
                id: 'policy-detached',
                pattern: 'orphan.example',
                policy_type: 'allow',
                is_active: true,
                source_policy_visibility: {
                    visibility_state: 'detached',
                    status_label: '연결 없음',
                    status_message: '활성 정책이지만 연결된 프리셋이나 최근 적용 이력이 없습니다.'
                }
            }
        ]
    });
    assert.equal(detachedPolicies.statusTone, 'yellow');
    assert.match(detachedPolicies.statusMessage, /연결되지 않았습니다/);
});

test('keyword suggestion view helper preserves loading, success, and error render states', () => {
    const loading = helpers.resolveKeywordSuggestionView({ phase: 'loading' });
    assert.equal(loading.buttonDisabled, true);
    assert.match(loading.buttonHtml, /추천 중/);

    const success = helpers.resolveKeywordSuggestionView({
        phase: 'success',
        keywords: ['AI', 'Robotics']
    });
    assert.match(success.resultHtml, /추천 키워드/);
    assert.match(success.resultHtml, /app\.addKeywordToInput\('AI'\)/);
    assert.match(success.resultHtml, /모든 키워드 사용/);

    const error = helpers.resolveKeywordSuggestionView({
        phase: 'error',
        errorMessage: 'boom'
    });
    assert.match(error.resultHtml, /오류가 발생했습니다: boom/);
});

test('index templates load both helper scripts before app shell', () => {
    ['index.html', 'index_en.html'].forEach((templateName) => {
        const template = fs.readFileSync(path.join(repoRoot, 'web/templates', templateName), 'utf8');
        const requestHelpersIndex = template.indexOf('js/app_request_response_helpers.js');
        const viewHelpersIndex = template.indexOf('js/app_view_state_helpers.js');
        const appIndex = template.indexOf('js/app.js');

        assert.notEqual(requestHelpersIndex, -1, `${templateName} should load request/response helper`);
        assert.notEqual(viewHelpersIndex, -1, `${templateName} should load view-state helper`);
        assert.notEqual(appIndex, -1, `${templateName} should load app shell`);
        assert.ok(requestHelpersIndex < appIndex, `${templateName} should load request/response helper before app.js`);
        assert.ok(viewHelpersIndex < appIndex, `${templateName} should load view-state helper before app.js`);
    });
});
